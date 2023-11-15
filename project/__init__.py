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

import urllib
from google.cloud import storage

from utilities import utils

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", os.urandom(12))
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

Session(app)
oauth = OAuth(app)

@app.errorhandler(413)
def too_large(e):
    return make_response(jsonify(message="File is too large"), 413)

@app.route('/', methods = ('GET', 'POST'))
@app.route('/home', methods = ('GET', 'POST'))
def index():
	if session.get('user_id') and session.get('user_id') != -1: 
		return render_template('index.html', 
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])
	else:
		return redirect(url_for('login'))


#ADD / INSERT or UPDATE DATA 
@app.route('/add_response', methods = ['POST'])
def add_response():
	
	response_text = request.form.get('response_text')
	question_id = request.form.get('question_id')

	if not response_text:
		flash("Please enter response text")
		return redirect(request.referrer)

	response, question_response_counter = utils.add_response(user_id = session['user_id'], question_id = question_id, response_text = response_text)

	if response == -1:
		flash("An error occured")
		return redirect(request.referrer)

	return jsonify({'response' : response, 'question_response_counter' : question_response_counter})

@app.route('/ask_question', methods = ('GET', 'POST'))
def ask_question():
	if session.get('user_id'):
		user_id = session['user_id']

		if request.method == 'POST':
			question_title = request.form['question-title']
			question_details = request.form['question-details']
			question_tags = request.form.get('question-tags', '')

			if not question_title:
				flash("Please enter the Title!")
			elif not question_details:
				flash('question details are required!')
			else:
				question_id = utils.add_question(user_id = session['user_id'], question_title = question_title, question_text = question_details, question_tags = question_tags)

				if question_id == -1:
					flash("An error occured")
					return redirect(request.referrer)

				print(f" question added to database successfully!! {question_id}")
				
				return redirect(url_for('question_detail', question_id = question_id))

		return render_template('ask_question.html',
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])
	else:
		return redirect(url_for('login'))

@app.route('/delete_question/<int:question_id>/', methods = ('GET', 'POST'))
def delete_question(question_id):
	if session.get('user_id'):
		#GET user_id and question_id
		
		response_status = utils.delete_question(user_id = session['user_id'], question_id = question_id)

		if response_status == "OK":
			flash("Question deleted successfully!")

		return redirect(url_for('index'))
	else:
		return redirect(url_for('login'))

@app.route('/delete_response/<int:response_id>/', methods = ('GET', 'POST'))
def delete_response(response_id):
	if session.get('user_id'):
		#GET user_id and response_id
		
		response_status = utils.delete_response(user_id = session['user_id'], response_id = response_id)

		if response_status == "OK":
			flash("Response deleted successfully!")

		print(response_status)

		return redirect(request.referrer)
	else:
		return redirect(url_for('login'))

@app.route('/follow_unfollow', methods = ['POST'])
def follow_unfollow():
	followed_user_id = request.form.get('followed_user_id')

	status = utils.follow_unfollow(follower_user_id = session['user_id'], followed_user_id = followed_user_id)

	return jsonify({'status' : status})

@app.route('/generate_quiz', methods = ['POST'])
def generate_quiz():
	user_id = request.form.get('user_id', 1)
	topic_level_pairs = request.form.get('topic_level_pairs')
	
	quiz_id = utils.generate_quiz_questions(user_id = user_id, topic_level_pairs = topic_level_pairs)

	return jsonify({'quiz_id' : quiz_id})

@app.route('/record_user_quiz_response', methods = ['POST'])
def record_user_quiz_response():

	quiz_id = request.form.get('quiz_id');
	quiz_question_ids = request.form.keys() - ['quiz_id'];

	for quiz_question_id in quiz_question_ids:
		utils.record_user_quiz_response(user_id = session['user_id'], quiz_question_id = quiz_question_id, user_response = int(request.form.get(quiz_question_id)))

	utils.score_user_quiz(user_id = session['user_id'], quiz_id = quiz_id)

	return redirect(url_for('quiz'))
	#user_id = int(request.form.get('user_id'))
	#quiz_question_id = int(request.form.get('quiz_question_id'))
	#user_response = int(request.form.get('user_response'))

	#response = utils.record_user_quiz_response(user_id = user_id, quiz_question_id = quiz_question_id, user_response = user_response)

	return jsonify({'response' : response})

@app.route('/score_user_quiz', methods = ['POST'])
def score_user_quiz():
	user_id = int(request.form.get('user_id'))
	quiz_id = int(request.form.get('quiz_id'))

	score = utils.score_user_quiz(user_id = user_id, quiz_id = quiz_id)

	return jsonify({"score" : score})

@app.route('/upload_image', methods = ['POST'])
def upload_image():
	
	"""
	I need to be able to extract 
	file name 
	image file itself
	content type
	"""
	#print('request recived to upload image!!')

	if 'image' not in request.files:
		return jsonify({'error': 'No image uploaded!!'})

	image = request.files['image']

	if image.filename == '':
		return jsonify({'error': 'No File Name!!'})

	if image:
		bucket_name = os.environ.get('STORAGE_BUCKET_NAME')
		content_type = image.content_type
		filename = image.filename

		#print(f"uploading {filename} to {bucket_name}")

		gcs_client = storage.Client()
		storage_bucket = gcs_client.get_bucket(bucket_name)
		blob = storage_bucket.blob(filename)

		#print("starting image upload...")

		blob.upload_from_string(image.read(), content_type = content_type)

		image_url = blob.public_url;

		# Return the URL of the saved image
		return jsonify({'url': image_url})

@app.route('/vote_unvote', methods = ['POST'])
def vote_unvote():
	question_id = int(request.form.get('question_id', -1))
	response_id = int(request.form.get('response_id', -1))
	post_type = request.form.get('post_type', 'question')
	up_or_down_vote = request.form.get('up_or_down_vote', 'up')

	print(question_id, response_id, post_type, up_or_down_vote)

	vote_count, my_vote = utils.vote_unvote(user_id = session['user_id'], 
											question_id = question_id, 
											response_id = response_id, 
											post_type = post_type,
											up_or_down_vote = up_or_down_vote)

	return jsonify({'vote_count' : vote_count, 'my_vote' : my_vote})


#GET DATA
@app.route('/attempt_quiz/<int:quiz_id>/')
def attempt_quiz(quiz_id):
	if session.get('user_id'):
		return render_template('attempt_quiz.html', quiz_id = quiz_id,
			start_quiz = "true",
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url']
		)
	else:
		return redirect(url_for('login'))

@app.route('/create_custom_quiz', methods = ('GET', 'POST'))
def create_custom_quiz():
	if session.get('user_id'):
		if request.method == 'GET':
			return render_template('create_custom_quiz.html',
				user_id = session['user_id'], 
				user_name = session['user_name'], 
				user_picture_url = session['user_picture_url']
			)
		else:
			number_of_topics = len(request.form) // 2
			topic_level_pairs = dict()

			for i in range(1, number_of_topics + 1):
				topic_name = request.form.get(f"topic_name_{i}")
				difficulty_level = request.form.get(f"difficulty_level_{i}")

				topic_level_pairs[topic_name] = difficulty_level

			quiz_id = utils.generate_quiz_questions(user_id = session['user_id'], topic_level_pairs = topic_level_pairs)

			return redirect(url_for('attempt_quiz', quiz_id = quiz_id))
	else:
		return redirect(url_for('login'))

@app.route('/get_quiz_questions', methods = ['POST'])
def get_quiz_questions():
	quiz_id = int(request.form.get('quiz_id'))
	limit = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	quiz_details, quiz_questions = utils.get_quiz_questions(quiz_id = quiz_id, limit = limit, offset = offset)

	return jsonify({'quiz_details' : quiz_details, 'quiz_questions' : quiz_questions})

@app.route('/get_quiz_results', methods = ['POST'])
def get_quiz_results():
	user_id = int(request.form.get('user_id'))
	quiz_id = int(request.form.get('quiz_id'))

	quiz_details, quiz_questions_results = utils.get_quiz_results(user_id = user_id, quiz_id = quiz_id)
	
	return jsonify({'quiz_details' : quiz_details, 'quiz_results' : quiz_questions_results})

@app.route('/load_more_questions', methods = ['POST'])
def load_more_questions():
	# Get the number of transactions to load and offset from the request
	num_to_load = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	questions = utils.load_more_questions(
					user_id = session['user_id'], 
					num_to_load = num_to_load, offset = offset
				)

	return jsonify({'questions': questions})

@app.route('/load_more_quizzes', methods = ['POST'])
def load_more_quizzes():
		user_id = int(request.form.get('user_id'))
		limit = int(request.form.get('num_to_load', 10))
		offset = int(request.form.get('offset', 0))

		quizzes = utils.load_more_quizzes(user_id = user_id, limit = limit, offset = offset)

		return jsonify({'quizzes' : quizzes})

@app.route('/load_more_responses', methods=['POST'])
def load_more_responses():
	question_id = request.form.get('question_id')
	limit = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	responses = utils.load_more_responses(
					user_id = session['user_id'], question_id = question_id, 
					limit = limit, offset = offset
				)

	return jsonify({'responses' : responses})

@app.route('/load_more_web_search_results', methods=['POST'])
def load_more_web_search_results():
	question_id = request.form.get('question_id')
	limit = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	web_search_results = utils.load_more_web_search_results(question_id = question_id, limit = limit, offset = offset)

	return jsonify({'web_search_results' : web_search_results})

@app.route('/load_more_video_results', methods=['POST'])
def load_more_video_results():
	question_id = int(request.form.get('question_id'))
	limit = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	video_results = utils.load_more_video_results(question_id = question_id, limit = limit, offset = offset)

	return jsonify({'video_results' : video_results})

@app.route('/load_more_related_questions', methods=['POST'])
def load_more_related_questions():
	question_id = int(request.form.get('question_id'))
	limit = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	similar_questions = utils.load_more_related_questions(question_id = question_id, limit = limit, offset = offset)

	return jsonify({'similar_questions' : similar_questions})

@app.route('/question_detail/<int:question_id>/', methods = ('GET', 'POST'))
def question_detail(question_id):
	if session.get('user_id'):
		question = utils.get_question(user_id = session['user_id'], question_id = question_id)

		if question == -1:
			flash("An error while fetching the question")
			return redirect(request.referrer)

		return render_template('question_detail.html', question = question,
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url']
		)
	else:
		return redirect(url_for('login'))

@app.route('/quiz')
def quiz():
	if session.get('user_id') and session.get('user_id') != -1: 
		return render_template('quiz.html', 
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])
	else:
		return render_template('quiz.html')

@app.route('/search', methods = ('GET', 'POST'))
def search():
	if session.get('user_id'):

		if request.method == 'POST':
			search_query = request.form.get('search_query', '')
			limit = int(request.form.get('num_to_load', 10))
			offset = int(request.form.get('offset', 0))
		
			search_results = utils.question_search(user_id = session['user_id'], search_query = search_query, limit = limit, offset = offset)

			return jsonify({'search_results' : search_results})
		else:
			search_query = request.args.get('search_query', '')
			
			return render_template('search_results.html', 
				search_query = search_query,
				user_id = session['user_id'], 
				user_name = session['user_name'], 
				user_picture_url = session['user_picture_url']
			)
	else:
		return redirect(url_for('login'))

#AUTH
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
			auth_result = utils.check_database_user_authentication(name = first_name + " " + last_name, email = email, password = password, type = "email_register")
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