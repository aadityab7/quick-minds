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

Session(app)
oauth = OAuth(app)

@app.errorhandler(413)
def too_large(e):
    return make_response(jsonify(message="File is too large"), 413)

@app.route('/', methods = ('GET', 'POST'))
@app.route('/home', methods = ('GET', 'POST'))
def index():
	"""
		when the routes '/' (default) or '/home' are visited
		call the index function
	"""
	if session.get('user_id') and session.get('user_id') != -1: 
		#if user is logged in
		#redirect to the questions page
		return redirect(url_for("questions"))
	else:
		#if user is not logged in
		#set dummy session variables
		#and redirect to the landing page
		session["user_id"] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""

		return render_template('landing_page.html',
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url']
		)

########################################################################################################################################
#PROFILE FUNCTIONALITY

@app.route('/profile/<int:target_user_id>/')
def profile(target_user_id):

	if session.get('user_id') and session.get('user_id') != -1:
		pass
	else:
		session["user_id"] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""

	return render_template('profile.html',
		target_user_id = target_user_id,
		user_id = session['user_id'], 
		user_name = session['user_name'], 
		user_picture_url = session['user_picture_url']
	)

@app.route('/get_profile_info', methods = ['POST'])
def get_profile_info():
	target_user_id = int(request.form.get('target_user_id'))

	profile_info, followers, following = utils.get_profile_info(user_id = session['user_id'], target_user_id = target_user_id) 

	if profile_info == -1:
		flash("some error occured while fetching user's data")
		return redirect(request.referrer)

	return jsonify({'profile_info': profile_info, 'followers': followers, 'following': following})

@app.route('/get_user_questions_activity', methods = ['POST'])
def get_user_questions_activity():
	"""
		API endpoint which can only be accessed using POST method
		1. Extract form data embedded in the POST request 
			- target_user_id: int
			- limit: int
			- offset: int
		2. use utility function to perform required operations
		3. return the resultant data back in the JSON format
	"""
	target_user_id = int(request.form.get('target_user_id'))
	limit = int(request.form.get('num_to_load'))
	offset = int(request.form.get('offset'))

	questions = utils.get_user_questions_activity(
		user_id = session['user_id'], 
		target_user_id = target_user_id, 
		limit = limit, 
		offset = offset
	)

	return jsonify({'questions': questions})

@app.route('/get_user_tag_activity', methods = ['POST'])
def get_user_tag_activity():
	target_user_id = int(request.form.get('target_user_id'))
	limit = int(request.form.get('num_to_load'))
	offset = int(request.form.get('offset'))

	tags = utils.get_user_tag_activity(user_id = session['user_id'], target_user_id = target_user_id, limit = limit, offset = offset)

	return jsonify({'tags': tags})

@app.route('/get_user_response_activity', methods = ['POST'])
def get_user_response_activity():
	target_user_id = int(request.form.get('target_user_id'))
	limit = int(request.form.get('num_to_load'))
	offset = int(request.form.get('offset'))

	responses = utils.get_user_response_activity(user_id = session['user_id'], target_user_id = target_user_id, limit = limit, offset = offset)

	return jsonify({'responses': responses})

@app.route('/get_user_article_activity', methods = ['POST'])
def get_user_article_activity():
	target_user_id = int(request.form.get('target_user_id'))
	limit = int(request.form.get('num_to_load'))
	offset = int(request.form.get('offset'))

	articles = utils.get_user_article_activity(
		user_id = session['user_id'], 
		target_user_id = target_user_id, 
		limit = limit, 
		offset = offset
	)

	return jsonify({'articles': articles})


@app.route('/followers/<int:target_user_id>')
def followers(target_user_id):
	if session.get('user_id') and session.get('user_id') != -1:
		pass
	else:
		session["user_id"] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""

	return render_template('followers.html',
		target_user_id = target_user_id,
		user_id = session['user_id'], 
		user_name = session['user_name'], 
		user_picture_url = session['user_picture_url']
	)

########################################################################################################################################
#TAGS FUNCTIONALITY

@app.route('/tags', methods = ('GET', 'POST'))
def tags():
	if session.get("user_id") and session.get('user_id') != -1:
		pass
	else:
		session["user_id"] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""
		
	if request.method == 'GET':
		return render_template('tags.html',
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])
	else:
		limit = int(request.form.get('num_to_load'))
		offset = int(request.form.get('offset'))

		tags = utils.load_more_tags(limit = limit, offset = offset) 

		return jsonify({'tags' : tags})

@app.route('/tag/<string:tag_name>/')
def tag(tag_name):
	if session.get('user_id') and session.get('user_id') != -1:
		pass		
	else:
		session["user_id"] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""
			
	return render_template('tag.html', 
		tag_name = tag_name,
		user_id = session['user_id'], 
		user_name = session['user_name'], 
		user_picture_url = session['user_picture_url'])

@app.route('/load_more_questions_with_tag', methods = ['POST'])
def load_more_questions_with_tag():
	tag_name = request.form.get('tag_name')
	limit = int(request.form.get('num_to_load'))
	offset = int(request.form.get('offset'))

	questions = utils.load_more_questions_with_tag(
					user_id = session['user_id'], 
					tag_name = tag_name,
					limit = limit,
					offset = offset
				)

	return jsonify({'questions': questions})

########################################################################################################################################
#ARTICLES FUNCTIONALITY

@app.route('/load_more_articles_with_tag', methods = ['POST'])
def load_more_articles_with_tag():
	tag_name = request.form.get('tag_name')
	limit = int(request.form.get('num_to_load'))
	offset = int(request.form.get('offset'))

	articles = utils.load_more_articles_with_tag(
					user_id = session['user_id'], 
					tag_name = tag_name,
					limit = limit,
					offset = offset
				)

	return jsonify({'articles': articles})

@app.route('/articles')
def articles():
	return render_template('articles.html',
		user_id = session['user_id'],
		user_name = session['user_name'], 
		user_picture_url = session['user_picture_url'])

@app.route('/write_article', methods = ('GET', 'POST'))
def write_article():
	if session.get('user_id') and session.get('user_id') != -1:
		if request.method == 'POST':
			title = request.form.get('article-title')
			contents = request.form.get('article-contents')
			tags = request.form.get('article-tags')

			article_id = utils.add_article(user_id = session['user_id'], title = title, 
				contents = contents, tags = tags)

			return redirect(url_for('article', article_id = article_id))
		else:
			return render_template('write_article.html',
				user_id = session['user_id'],
				user_name = session['user_name'], 
				user_picture_url = session['user_picture_url'])
	else:
		return redirect(url_for('login'))

@app.route('/article/<int:article_id>/', methods = ('GET', 'POST'))	
def article(article_id):
	if session.get('user_id') and session.get('user_id') != -1:
		pass
	else:
		session['user_id'] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""

	article = utils.get_article(user_id = session['user_id'], article_id = article_id)	

	if article == -1:
		flash("An error while fetching the article")
		return redirect(request.referrer)

	return render_template('article.html', article = article,
		user_id = session['user_id'], 
		user_name = session['user_name'], 
		user_picture_url = session['user_picture_url']
	)

@app.route('/add_article_response', methods = ['POST'])	
def add_article_response():
	article_id = int(request.form.get('article_id'))
	contents = request.form.get('contents')

	article_response, article_response_counter = utils.add_article_response(user_id = session['user_id'], 
		article_id = article_id, contents = contents)

	return({'article_response' : article_response, 'article_response_counter' : article_response_counter})

@app.route('/load_more_articles', methods = ['POST'])	
def load_more_articles():
	limit = int(request.form.get('num_to_load'))
	offset = int(request.form.get('offset'))

	articles = utils.load_more_articles(user_id = session['user_id'], limit = limit, offset = offset)

	return jsonify({'articles' : articles})

@app.route('/load_more_article_responses', methods = ['POST'])	
def load_more_article_responses():
	article_id = int(request.form.get('article_id'))
	limit = int(request.form.get('num_to_load'))
	offset = int(request.form.get('offset'))

	article_responses = utils.load_more_article_responses(
		user_id = session['user_id'],
		article_id = article_id, 
		limit = limit, 
		offset = offset
	)

	return ({'article_responses' : article_responses})

@app.route('/handle_article_vote', methods = ['POST'])	
def handle_article_vote():
	article_id = int(request.form.get('article_id'))
	up_or_down_vote = request.form.get('up_or_down_vote')

	vote_count, my_vote = utils.handle_article_vote(user_id = session['user_id'], 
		article_id = article_id, up_or_down_vote = up_or_down_vote)

	return jsonify({'vote_count' : vote_count, 'my_vote' : my_vote})

@app.route('/handle_article_response_vote', methods = ['POST'])	
def handle_article_response_vote():
	article_response_id = int(request.form.get('article_response_id'))
	up_or_down_vote = request.form.get('up_or_down_vote')

	vote_count, my_vote = utils.handle_article_response_vote(user_id = session['user_id'], 
		article_response_id = article_response_id, up_or_down_vote = up_or_down_vote)

	return jsonify({'vote_count' : vote_count, 'my_vote' : my_vote})

@app.route('/add_article_response_comment', methods = ['POST'])
def add_article_response_comment():
	article_id = int(request.form.get('article_id'))
	contents = request.form.get('contents')

	response = utils.add_article_response_comment(user_id = session['user_id'], article_id = article_id, 
		contents = contents)

	return jsonify({'response': response})

@app.route('/load_more_article_response_comments', methods = ['POST'])	
def load_more_article_response_comments():
	user_id = int(request.form.get('user_id'))
	article_response_id = int(request.form.get('article_response_id'))
	limit = int(request.form.get('limit'))
	offset = int(request.form.get('offset'))

	article_response_comments = utils.load_more_article_response_comments(user_id = user_id, 
		article_response_id = article_response_id, limit = limit, offset = offset)

	return jsonify({'article_response_comments' : article_response_comments})

@app.route('/delete_article/<int:article_id>/', methods = ('GET', 'POST'))	
def delete_article(article_id):
	if session.get('user_id') and session.get('user_id') != -1:
		#GET user_id and question_id
		
		response_status = utils.delete_article(user_id = session['user_id'], article_id = article_id)

		if response_status == "OK":
			flash("Article deleted successfully!")
		else:
			flash("response_status")

		return redirect(url_for('articles'))
	else:
		return redirect(url_for('login'))

@app.route('/delete_article_response/<int:article_response_id>/', methods = ('GET', 'POST'))	
def delete_article_response(article_response_id):
	if session.get('user_id') and session.get('user_id') != -1:
		#GET user_id and response_id
		response_status = utils.delete_article_response(user_id = session['user_id'], 
			article_response_id = article_response_id)

		if response_status == "OK":
			flash("Article Response deleted successfully!")
		else:
			flash(response_status)

		return redirect(request.referrer)
	else:
		return redirect(url_for('login'))

@app.route('/get_article_count')
def get_article_count():
	total_article_count = utils.get_article_count()
	return jsonify({"total_article_count" : total_article_count})

########################################################################################################################################
#QUESTIONS FUNCTIONALITY

@app.route('/questions')
def questions():
	return render_template('questions.html', 
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])

@app.route('/get_question_count')
def get_question_count():
	total_question_count = utils.get_question_count()
	return jsonify({"total_question_count" : total_question_count})

@app.route('/question_progress/<int:question_id>')
def question_progress(question_id):
	if session.get('user_id') and session.get('user_id') != -1:
		return render_template(
			'question_progress.html', 
			question_id = question_id,
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url']
		)
	else:
		return redirect(url_for('login'))

@app.route('/question_step_text_extraction/', methods = ['POST'])
def question_step_text_extraction():
	question_id = int(request.form.get('question_id'))

	response_status = utils.question_step_text_extraction(question_id = question_id)

	return jsonify({'response_status' : response_status})

@app.route('/question_step_web_search', methods = ['POST'])
def question_step_web_search():
	question_id = int(request.form.get('question_id'))
	
	response_status = utils.question_step_web_search(question_id = question_id)

	return jsonify({'response_status' : response_status})

@app.route('/question_step_youtube_search', methods = ['POST'])
def question_step_youtube_search():
	question_id = int(request.form.get('question_id'))
	
	response_status = utils.question_step_youtube_search(question_id = question_id)

	return jsonify({'response_status' : response_status})

@app.route('/question_step_similar_question', methods = ['POST'])
def question_step_similar_question():
	question_id = int(request.form.get('question_id'))
	
	response_status = utils.question_step_similar_question(question_id = question_id)

	return jsonify({'response_status' : response_status})

@app.route('/question_step_ai_response', methods = ['POST'])
def question_step_ai_response():
	question_id = int(request.form.get('question_id'))
	
	response_status = utils.question_step_ai_response(question_id = question_id)

	return jsonify({'response_status' : response_status})

@app.route('/add_response', methods = ['POST'])
def add_response():
	if session.get('user_id') and session.get('user_id') != -1:
		response_text = request.form.get('response_text')
		question_id = request.form.get('question_id')

		if not response_text:
			flash("Please enter response text")
			return redirect(request.referrer)

		response, question_response_counter = utils.add_response(user_id = session['user_id'], 
			question_id = question_id, response_text = response_text)

		if response == -1:
			flash("An error occured")
			return redirect(request.referrer)

		return jsonify({'response' : response, 'question_response_counter' : question_response_counter})
	else:
		return redirect(url_for('login'))

@app.route('/ask_question', methods = ('GET', 'POST'))
def ask_question():
	if session.get('user_id') and session.get('user_id') != -1:
		user_id = session['user_id']

		if request.method == 'POST':
			#question_title = request.form['question-title']
			question_details = request.form['question-details']
			question_tags = request.form.get('question-tags', '')

			#if not question_title:
			#	flash("Please enter the Title!")
			#el
			if not question_details:
				flash('question details are required!')
			else:
				question_id = utils.add_question(user_id = session['user_id'], 
					#question_title = question_title, 
					question_text = question_details, 
					question_tags = question_tags)

				if question_id == -1:
					flash("An error occured")
					return redirect(request.referrer)

				return redirect(url_for('question_progress', question_id = question_id))

		return render_template('ask_question.html',
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])
	else:
		return redirect(url_for('login'))

@app.route('/delete_question/<int:question_id>/', methods = ('GET', 'POST'))
def delete_question(question_id):
	if session.get('user_id') and session.get('user_id') != -1:
		#GET user_id and question_id
		
		response_status = utils.delete_question(user_id = session['user_id'], question_id = question_id)

		if response_status == "OK":
			flash("Question deleted successfully!")
		else:
			flash(response_status)
			
		return redirect(url_for('index'))
	else:
		return redirect(url_for('login'))

@app.route('/delete_response/<int:response_id>/', methods = ('GET', 'POST'))
def delete_response(response_id):
	if session.get('user_id') and session.get('user_id') != -1:
		#GET user_id and response_id
		
		response_status = utils.delete_response(user_id = session['user_id'], response_id = response_id)

		if response_status == "OK":
			flash("Response deleted successfully!")
		else:
			flash(response_status)

		return redirect(request.referrer)
	else:
		return redirect(url_for('login'))

@app.route('/vote_unvote', methods = ['POST'])
def vote_unvote():
	if session.get('user_id') and session.get('user_id') != -1:
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
	else:
		return redirect(url_for("login"))

@app.route('/load_more_questions', methods = ['POST'])
def load_more_questions():
	# Get the number of questions to load and offset from the request
	num_to_load = int(request.form.get('num_to_load', 10))
	offset = int(request.form.get('offset', 0))

	questions = utils.load_more_questions(
					user_id = session['user_id'], 
					num_to_load = num_to_load, 
					offset = offset
				)

	return jsonify({'questions': questions})

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
	if session.get('user_id') and session.get('user_id') != -1:
		pass
	else:
		session['user_id'] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""

	question = utils.get_question(user_id = session['user_id'], question_id = question_id)

	if question == -1:
		flash("An error while fetching the question")
		return redirect(request.referrer)

	return render_template('question_detail.html', question = question,
		user_id = session['user_id'], 
		user_name = session['user_name'], 
		user_picture_url = session['user_picture_url']
	)

########################################################################################################################################
#QUIZ FUNCTIONALITY
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

	return redirect(url_for('quiz_result', quiz_id = quiz_id))

@app.route('/quiz_result/<int:quiz_id>/')
def quiz_result(quiz_id):
	"""
		if user has has attempted this quiz then show the results else 
		show a page with the option to start the quiz
	"""
	if session.get('user_id') and session.get('user_id') != -1:
		return render_template('quiz_result.html',
			quiz_id = quiz_id,
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url']
		)
	else:
		return redirect(url_for('login'))

@app.route('/score_user_quiz', methods = ['POST'])
def score_user_quiz():
	user_id = int(request.form.get('user_id'))
	quiz_id = int(request.form.get('quiz_id'))

	score = utils.score_user_quiz(user_id = user_id, quiz_id = quiz_id)

	return jsonify({"score" : score})

@app.route('/attempt_quiz/<int:quiz_id>/<string:start_quiz>/')
def attempt_quiz(quiz_id, start_quiz):
	if session.get('user_id') and session.get('user_id') != -1:
		
		start_quiz = str(start_quiz)

		return render_template('attempt_quiz.html', quiz_id = quiz_id,
			start_quiz = start_quiz,
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url']
		)
	else:
		return redirect(url_for('login'))

@app.route('/create_custom_quiz', methods = ('GET', 'POST'))
def create_custom_quiz():
	if session.get('user_id') and session.get('user_id') != -1:
		if request.method == 'GET':
			return render_template('create_custom_quiz.html',
				user_id = session['user_id'], 
				user_name = session['user_name'], 
				user_picture_url = session['user_picture_url']
			)
		else:
			number_of_topics = int(request.form.get("max_topic_number"))
			topic_level_pairs = dict()

			for i in range(1, number_of_topics + 1):
				topic_name = request.form.get(f"topicname_{i}")
				if topic_name is not None:
					difficulty_level = request.form.get(f"difficultylevel_{i}")
					topic_level_pairs[topic_name] = difficulty_level

			quiz_id = utils.generate_quiz_questions(user_id = session['user_id'], topic_level_pairs = topic_level_pairs)

			return redirect(url_for('attempt_quiz', quiz_id = quiz_id, start_quiz = "true"))
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

	response_status, quiz_details, quiz_questions_results = utils.get_quiz_results(user_id = user_id, quiz_id = quiz_id)
	
	return jsonify({'response_status': response_status, 'quiz_details' : quiz_details, 'quiz_results' : quiz_questions_results})

@app.route('/load_more_quizzes', methods = ['POST'])
def load_more_quizzes():
		user_id = int(request.form.get('user_id'))
		limit = int(request.form.get('num_to_load', 10))
		offset = int(request.form.get('offset', 0))

		quizzes = utils.load_more_quizzes(user_id = user_id, limit = limit, offset = offset)

		return jsonify({'quizzes' : quizzes})

@app.route('/quiz')
def quiz():
	if session.get('user_id') and session.get('user_id') != -1: 
		return render_template('quiz.html', 
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url'])
	else:
		return redirect(url_for('login'))

########################################################################################################################################
#COMMON FUNCTIONALITIES
@app.route('/follow_unfollow', methods = ['POST'])
def follow_unfollow():
	followed_user_id = request.form.get('followed_user_id')

	status = utils.follow_unfollow(follower_user_id = session['user_id'], followed_user_id = followed_user_id)

	return jsonify({'status' : status})

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

@app.route('/search', methods = ('GET', 'POST'))
def search():
	if session.get('user_id') and session.get('user_id') != -1:
		pass
	else:
		session['user_id'] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""

	if request.method == 'POST':
		search_query = request.form.get('search_query', '')
		limit = int(request.form.get('num_to_load', 10))
		offset = int(request.form.get('offset', 0))
		search_type = request.form.get('search_type', "all")
	
		search_results = utils.search(user_id = session['user_id'], search_query = search_query, limit = limit, offset = offset, search_type = search_type)	

		return jsonify({'search_results' : search_results})
	else:
		search_query = request.args.get('search_query', '')
		
		return render_template('search_results.html', 
			search_query = search_query,
			user_id = session['user_id'], 
			user_name = session['user_name'], 
			user_picture_url = session['user_picture_url']
		)
		
########################################################################################################################################
#AUTHENTICATION FUNCTIONALITY
#MAIN AUTHENTICATION SECTION (login, logout, sign_up)
@app.route('/login')
def login():
	if session.get('user_id') and session.get('user_id') != -1:
		return redirect(url_for('index'))
	else:
		session['user_id'] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""

	return render_template('login.html',
		user_id = session['user_id'], 
		user_name = session['user_name'], 
		user_picture_url = session['user_picture_url']
	)

@app.route("/logout", methods=('GET', 'POST'))
def logout():
    session["user_id"] = -1
    return redirect(url_for("index"))

@app.route('/sign_up')
def sign_up():
	if session.get('user_id') and session.get('user_id') != -1:
		return redirect('index')
	else:
		session['user_id'] = -1
		session['user_name'] = ""
		session['user_picture_url'] = ""

	return render_template('sign_up.html',
		user_id = session['user_id'], 
		user_name = session['user_name'], 
		user_picture_url = session['user_picture_url']
	)

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