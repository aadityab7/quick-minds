from flask import Flask, render_template, request, url_for, flash, redirect, abort, jsonify, session
import plotly.graph_objs as go

from authlib.integrations.flask_client import OAuth
from flask_session import Session

import json
import os
import sqlite3
import requests
from werkzeug.utils import secure_filename

import markdown

import psycopg2

from utilities import utils

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", os.urandom(12))
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
app.config['UPLOAD_FOLDER'] = "G:\\quick-minds\\image_folder"

Session(app)
oauth = OAuth(app)

@app.errorhandler(413)
def too_large(e):
    return make_response(jsonify(message="File is too large"), 413)

@app.route('/', methods = ('GET', 'POST'))
@app.route('/home', methods = ('GET', 'POST'))
def index():
	if session.get('user_id') and session.get('user_id') != -1: 
		print("rendering index page now!!")
		return render_template('index.html', 
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])
	else:
		return redirect(url_for('login'))

@app.route('/ask_question', methods = ('GET', 'POST'))
def ask_question():
	if session.get('user_id'):
		user_id = session['user_id']

		if request.method == 'POST':
			question_title = request.form['question-title']
			question_details = request.form['question-details']

			file_url = ''
			filename = ''
			if 'file-upload' in request.files:
				image_file = request.files['file-upload']
				filename = secure_filename(image_file.filename)
				if filename != '':
					file_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
					image_file.save(file_url)

			if not question_title:
				flash("Please enter the Title!")
			elif not question_details:
				flash('question details are required!')
			else:
				question_id = utils.add_question(user_id = session['user_id'], question_title = question_title, question_text = question_details)

				if question_id == -1:
					flash("An error occured")
					return redirect(request.referrer)
				
				if file_url != '':
					image_id = utils.add_image_to_post(file_url, question_id)
					if image_id == -1:
						flash("An error occured when inserting image")
						return redirect(request.referrer)

				return render_template('index.html', 
					user_id = session['user_id'], 
					user_name = session['user_name'], 
					user_picture_url = session['user_picture_url'])

		return render_template('ask_question.html',
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])
	else:
		return redirect(url_for('login'))

#MAIN AUTHENTICATION SECTION (login, logout, sign_up)
@app.route('/login')
def login():
	return render_template('login.html')

@app.route("/logout", methods=('GET', 'POST'))
def logout():
    session["user_id"] = -1
    return redirect(url_for("index"))

@app.route('/sign_up')
def sign_up():
	return render_template('sign_up.html')

#PERFORM ACTUAL AUTHENTICATION FLOW using OAuth2 SUB-SECTION (facebook, github, google)
#authentication with EMAIL
@app.route('/email_login', methods = ('GET', 'POST'))
def email_login():
	if request.method == 'POST':
		email = request.form['email']
		password = request.form['password']
		
		if not email:
			flash("Please enter the email address!")
			return redirect(request.referrer) 
		elif not password or password == "":
			flash("Please enter the password!")
			return redirect(request.referrer)
		else:
			auth_result = utils.check_database_user_authentication(email = email, password = password, type = "email_login")
			message, session["user_id"], session["user_name"], session["user_picture_url"] = auth_result

			if message != "OK":
				flash(message)
				return redirect(request.referrer)

		return redirect(url_for("index"))

@app.route('/email_register', methods = ('GET', 'POST'))
def email_register():
	if request.method == 'POST':
		first_name = request.form['first_name']
		last_name = request.form['last_name']
		email = request.form['email']
		password = request.form['password']
		password_confirmation = request.form['password_confirmation']

		if not first_name:
			flash("Please enter the First name!")
			#reload the same page with flash message instead of redirecting to index page!!
			return redirect(request.referrer) 
		elif not last_name:
			flash("Please enter the Last name!")
			return redirect(request.referrer) 
		elif not email:
			flash("Please enter the email address!")
			return redirect(request.referrer) 
		elif not password or password == "":
			flash("Please enter the password!")
			return redirect(request.referrer) 
		elif not password_confirmation:
			flash("Please enter the password confirmation!")
			return redirect(request.referrer) 
		elif password != password_confirmation:
			flash("password and password_confirmation are not same!!")
			return redirect(request.referrer) 
		else:
			auth_result = utils.check_database_user_authentication(name = first_name + last_name, email = email, password = password, type = "email_register")
			message, session["user_id"], session["user_name"], session["user_picture_url"] = auth_result

			if message != "OK":
				flash(message)
				return redirect(request.referrer)

		return redirect(url_for("index"))

#authentication with FACEBOOK
@app.route('/facebook/')
def facebook():
	# Facebook Oauth Config
	FACEBOOK_CLIENT_ID = os.environ.get('FACEBOOK_CLIENT_ID')
	FACEBOOK_CLIENT_SECRET = os.environ.get('FACEBOOK_CLIENT_SECRET')
	oauth.register(
		name='facebook',
		client_id=FACEBOOK_CLIENT_ID,
		client_secret=FACEBOOK_CLIENT_SECRET,
		access_token_url='https://graph.facebook.com/oauth/access_token',
		access_token_params=None,
		authorize_url='https://www.facebook.com/dialog/oauth',
		authorize_params=None,
		api_base_url='https://graph.facebook.com/',
	)

	# Redirect to google_auth function
	redirect_uri = url_for('facebook_auth', _external=True)

	if redirect_uri[:5] == "http:":
		redirect_uri = "https:" + redirect_uri[5:]

	return oauth.facebook.authorize_redirect(redirect_uri)
 
@app.route('/facebook/auth/')
def facebook_auth():
	token = oauth.facebook.authorize_access_token()
	resp = oauth.facebook.get(
		'https://graph.facebook.com/me?fields=id,name,picture{url}')
	profile = resp.json()

	user_id = profile["id"]
	user_name = profile["name"]
	picture_url = profile["picture"]["data"]["url"]

	auth_result = utils.check_database_user_authentication(name = user_name, picture_url = picture_url, facebook_id = user_id, type = "facebook")
	message, session["user_id"], session["user_name"], session["user_picture_url"] = auth_result

	if message != "OK":
		flash(message)
		return redirect(request.referrer)

	return redirect(url_for("index"))

#authentication with GITHUB
@app.route('/github/')
def github():
	GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
	GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

	oauth.register(
		name='github',
		client_id=GITHUB_CLIENT_ID,
		client_secret=GITHUB_CLIENT_SECRET,
		access_token_url='https://github.com/login/oauth/access_token',
		access_token_params=None,
		authorize_url='https://github.com/login/oauth/authorize',
		authorize_params=None,
		api_base_url='https://api.github.com/',
		client_kwargs={'scope': 'user:email'},
	)

	# Redirect to google_auth function
	redirect_uri = url_for('github_auth', _external=True)
	if redirect_uri[:5] == "http:":
		redirect_uri = "https:" + redirect_uri[5:]

	return oauth.github.authorize_redirect(redirect_uri)

@app.route('/github/auth/')
def github_auth():
	token = oauth.github.authorize_access_token()

	resp = oauth.github.get('user', token=token) 

	userinfo = resp.json()

	user_id = userinfo["id"]
	user_name = userinfo["name"]
	user_email = userinfo["email"]
	picture_url = userinfo["avatar_url"]

	user_email = "" if user_email is None else user_email

	auth_result = utils.check_database_user_authentication(name = user_name, email = user_email, picture_url = picture_url, github_id = user_id, type = "github")
	message, session["user_id"], session["user_name"], session["user_picture_url"] = auth_result

	if message != "OK":
		flash(message)
		return redirect(request.referrer)

	return redirect(url_for("index"))

#authentication with GOOGLE
@app.route('/google/')
def google():
	# Google Oauth Config
	# Get client_id and client_secret from environment variables
	GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
	GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

	CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'

	oauth.register(
		name='google',
		client_id=GOOGLE_CLIENT_ID,
		client_secret=GOOGLE_CLIENT_SECRET,
		server_metadata_url=CONF_URL,
		client_kwargs={
			'scope': 'openid email profile'
		}
	)
	 
	# Redirect to google_auth function
	redirect_uri = url_for('google_auth', _external=True)
	if redirect_uri[:5] == "http:":
		redirect_uri = "https:" + redirect_uri[5:]

	return oauth.google.authorize_redirect(redirect_uri)

@app.route('/google/auth/')
def google_auth():
	token = oauth.google.authorize_access_token()

	userinfo = token['userinfo']

	if userinfo.get("email_verified"):
		user_id = userinfo["sub"]
		user_name = userinfo["name"]
		user_email = userinfo["email"]
		picture_url = userinfo["picture"]
	else:
		return "User email not available or not verified by Google.", 400

	auth_result = utils.check_database_user_authentication(name = user_name, email = user_email, picture_url = picture_url, google_id = user_id, type = "google")
	message, session["user_id"], session["user_name"], session["user_picture_url"] = auth_result
	
	if message != "OK":
		flash(message)
		return redirect(request.referrer)

	return redirect(url_for("index"))

#MAIN SECTION
@app.route('/load_more_questions', methods = ('GET', 'POST'))
def load_more_questions():
	# Get the number of transactions to load and offset from the request
	num_to_load = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	questions = utils.load_more_questions(user_id = session['user_id'], num_to_load = num_to_load, offset = offset)

	return jsonify({'questions': questions})

@app.route('/question_detail/<int:question_id>/', methods = ('GET', 'POST'))
def question_detail(question_id):
	if session.get('user_id'):
		question = utils.get_question(question_id)

		return render_template('question_detail.html', question = question,
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url']
		)
	else:
		return redirect(url_for('login'))

@app.route('/add_response', methods = ['POST'])
def add_response():
	print("recived request")
	print(request.form)
	
	response_text = request.form.get('response_text')
	question_id = request.form.get('question_id')

	response = utils.add_response(user_id = session['user_id'], question_id = question_id, response_text = response_text)

	if response == -1:
		flash("An error occured")
		return redirect(request.referrer)

	return jsonify({'response' : response})

@app.route('/follow_unfollow', methods = ['POST'])
def follow_unfollow():
	follower_user_id = request.form.get('follower_user_id')
	followed_user_id = request.form.get('followed_user_id')

	status = utils.follow_unfollow(follower_user_id = follower_user_id, followed_user_id = followed_user_id)

	return jsonify({'status' : status})

@app.route('/vote_unvote', methods = ['POST'])
def vote_unvote():
	post_id = request.form.get('post_id')
	vote_type = request.form.get('vote_type')

	val = utils.vote_unvote(post_id = post_id, user_id = session['user_id'], vote_type = vote_type)

	return jsonify({'val' : val})

@app.route('/test_markdown')
def test_markdown():
	return render_template('test_markdown.html')


@app.route('/upload_image', methods = ['POST'])
def upload_image():
	if 'image' not in request.files:
		return jsonify({'error': 'No image part'})

	image = request.files['image']

	if image.filename == '':
		return jsonify({'error': 'No selected image file'})

	if image:
		image_url = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)

		# Save the image to the specified folder
		image.save(image_url)

		# Return the URL of the saved image
		return jsonify({'url': image_url})

@app.route('/load_more_responses', methods = ['POST'])
def load_more_responses():
	question_id = request.form.get('question_id')
	limit = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	responses = utils.load_more_responses(question_id = question_id, limit = limit, offset = offset)

	return jsonify({'responses' : responses})