
#Note : we represent user not logged in as user_id = -1

import os
import psycopg2
import markdown
import requests
import re
import vertexai
from vertexai.language_models import TextGenerationModel
import ast

model = TextGenerationModel.from_pretrained("text-bison@001")

def get_db_connection():
	"""
	function to establish connection to the database
	"""
	conn = psycopg2.connect(
		host=os.environ.get('DB_HOST'),
		database=os.environ.get('DB_NAME'),
		user=os.environ.get('DB_USERNAME'),
		password=os.environ.get('DB_PASSWORD'))

	return conn

def add_image_to_post(
	image_file_url: str,
	question_or_response_id: int,
	post_type: str = 'question'
):
	conn = get_db_connection()
	cur = conn.cursor()

	if post_type == 'question':
		query = "INSERT INTO Image (url, question_id, post_type) VALUES (%s, %s, %s)"
	else:
		query = "INSERT INTO Image (url, response_id, post_type) VALUES (%s, %s, %s)"

	cur.execute(query, (image_file_url, question_or_response_id, post_type))
	conn.commit()

	if post_type == 'question':
		query = "SELECT image_id FROM Image WHERE url = %s AND question_id = %s"
	else:
		query = "SELECT image_id FROM Image WHERE url = %s AND response_id = %s"

	cur.execute(query, (image_file_url, question_or_response_id))
	image_id = cur.fetchone()

	cur.close()
	conn.close()

	if image_id is None:
		return -1
	else:
		image_id = image_id[0]

	return image_id

def add_question(
	user_id: int,
	question_title: str,
	question_text:str,
	question_tags: str
):
	question_tags = [tag.strip() for tag in question_tags.split(',')]
	question_tags = str(set(question_tags))
	question_tags = re.sub(r"[']", "", question_tags)

	question_query = question_title + " " + question_text + " " + question_tags

	#we have to remove images from this query to perform search 
	question_query = re.sub(r'[!][[].*[\]][(].*[)]', "", question_query)
	question_query = re.sub(r"[#!*:{}\n]", "", question_query)

	conn = get_db_connection()
	cur = conn.cursor()

	query = "INSERT INTO Question (user_id, question_title, question_text, tags, document_vectors) VALUES (%s, %s, %s, %s, to_tsvector(%s))"

	cur.execute(query, (user_id, question_title, question_text, question_tags, question_query))
	conn.commit()

	query = "SELECT \
				Question.question_id \
			FROM Question \
			WHERE user_id = %s \
			ORDER BY created_time DESC LIMIT 1"
	
	cur.execute(query, (user_id,))
	question = cur.fetchone()

	cur.close()
	conn.close()

	if question is None:
		question_id = -1
	else:
		question_id = question[0]

	#keep track of all the images seperatly as well
	#images = re.findall(r'[!][[].*[\]][(].*[)]', question_text)
	
	#before returning the question find and add related resources and responses
	generate_and_add_ai_response_question(question_id = question_id, question_query = question_query)
	add_similar_questions_to_this_question(question_id = question_id, question_query = question_query)
	add_related_search_results_to_question(question_id = question_id, question_query = question_query)
	add_related_youtube_videos_to_question(question_id = question_id, question_query = question_query)

	return question_id

def add_quiz_to_db(
	user_id: int,
	quiz_ai_response: dict,
	topic_level_pairs: dict
):
	conn = get_db_connection()
	cur = conn.cursor()

	title = (', ').join(topic_level_pairs.keys()) + " Quiz"

	query = "INSERT INTO Quiz (user_id, title) VALUES (%s, %s)"
	cur.execute(query, (user_id, title))
	conn.commit()

	query = "SELECT quiz_id FROM Quiz WHERE user_id = %s ORDER BY created_time DESC LIMIT 1"
	cur.execute(query, (user_id,))
	quiz_id = cur.fetchone()[0]

	query = "INSERT INTO Quiz_Question (quiz_id, question_text, option_1, option_2, option_3, option_4, correct_answer) VALUES (%s, %s, %s, %s, %s, %s, %s)"

	for question in quiz_ai_response['questions']:
		
		if 'options' in question.keys():
			options = question.get('options')
		else:
			options = question.get('list_of_4_options')

		cur.execute(query, (quiz_id, question['question_text'], options[0], options[1], options[2], options[3], question['correct_option_number']))
		conn.commit()

	#store initially unattempted quiz score
	total_quiz_questions = len(quiz_ai_response['questions'])
	query = "INSERT INTO Quiz_Score_Card (quiz_id, user_id, total_quiz_questions, attempted, correct, wrong) VALUES (%s, %s, %s, %s, %s, %s)"

	cur.execute(query, (quiz_id, user_id, total_quiz_questions, 0, 0, 0))
	conn.commit()

	cur.close()
	conn.close()

	return quiz_id

def add_related_search_results_to_question(
	question_id: int,
	question_query: str
):
	response = make_web_search_request(question_query)

	if response == -1:
		print("An error occured in web search result!")
		return

	conn = get_db_connection()
	cur = conn.cursor()

	for response_item in response.get('items', []):
		title = response_item['htmlTitle']
		link = response_item['link']
		description = response_item['htmlSnippet']

		query = "INSERT INTO Related_web_search_result (question_id, title, description, link) VALUES (%s, %s, %s, %s)"
		cur.execute(query, (question_id, title, description, link))
		conn.commit()

	cur.close()
	conn.close()

def add_related_youtube_videos_to_question(
	question_id: int,
	question_query: str
):
	video_results = make_youtube_video_search_request(question_query)

	if video_results == -1:
		print("An error occured in web search result!")
		return

	conn = get_db_connection()
	cur = conn.cursor()

	for video_id, video_details in video_results.items():
		
		video_url = f'https://www.youtube.com/watch?v={video_id}'

		query = "INSERT INTO Related_video \
					(question_id, title, description, video_url, thumbnail_url, channel_title, player_embed_html) \
				VALUES (%s, %s, %s, %s, %s, %s, %s)"
		
		
		cur.execute(query, 
			(question_id, video_details['title'], video_details['description'], video_url, 
			video_details['thumbnail_url'], video_details['channel_title'], video_details['player_embed_html'])
		)		

		conn.commit()
		

	cur.close()
	conn.close()

def add_response(
	user_id: int,
	question_id: int,
	response_text: str
):

	conn = get_db_connection()
	cur = conn.cursor()

	query = "INSERT INTO Response (type, user_id, question_id, response_text) VALUES (%s, %s, %s, %s)"

	cur.execute(query, ('response', user_id, question_id, response_text))
	conn.commit()

	query = "UPDATE Question SET response_counter = response_counter + 1 WHERE question_id = %s"
	cur.execute(query, (question_id,))
	conn.commit()

	query = "SELECT \
				Response.response_id, Response.response_text, Response.vote_counter, Response.response_counter, Response.created_time, App_user.user_id, App_user.name\
			FROM Response \
			INNER JOIN App_user\
				ON Response.user_id = App_user.user_id\
			WHERE Response.user_id = %s \
			ORDER BY Response.created_time DESC LIMIT 1"
	
	cur.execute(query, (user_id,))
	response = cur.fetchone()

	query = "SELECT response_counter FROM Question WHERE question_id = %s"
	
	cur.execute(query, (question_id,))
	question_response_counter = cur.fetchone()

	cur.close()
	conn.close()

	if response is None:
		return -1

	if question_response_counter is None:
		question_response_counter = 0
	else:
		question_response_counter = question_response_counter[0]

	response_keys = ("response_id", "response_text", "vote_counter", "response_counter", "created_time", "user_id", "user_name")
	response = dict(zip(response_keys, response))

	response['response_text'] = markdown.markdown(response['response_text'])

	return response, question_response_counter

def add_similar_questions_to_this_question(
	question_id: int,
	question_query: str
):
	#do this before adding question to the table
	conn = get_db_connection()
	cur = conn.cursor()
	
	query = """
		SELECT
			question_id, 
			strict_word_similarity(%s, question_title || ' ' || question_text || ' ' || coalesce(array_to_string(tags, ', '), ' ')) as similarity
		FROM Question
		ORDER BY similarity 
		DESC LIMIT 10
	"""

	cur.execute(query, (question_query,))
	similar_questions = cur.fetchall()

	if similar_questions is None:
		similar_questions = []

	query = "INSERT INTO Related_question (question_id, similar_question_id, similarity_score) VALUES (%s, %s, %s)"
	
	#add this to the similarity table
	for similar_question in similar_questions:
		cur.execute(query, (question_id, similar_question[0], similar_question[1]))
		conn.commit()

	cur.close()
	conn.close()

def check_database_user_authentication(
		facebook_id:str = "", 
		github_id:str = "", 
		google_id:str = "", 	
		email:str = "", 
		password:str = "",
		name:str = "",
		picture_url:str = "https://icon-library.com/images/generic-user-icon/generic-user-icon-10.jpg",
		type:str = "Invalid"
):

	"""
	perform database operations for user authentication for login and sign-up
	parameters / arguments: (not in correct order)
		- name: user's first and last name
		- email: user email
		- password: password to use with email login (set to some complex default when not provided)
		- picture_url: url for user's profile photo (use default photo if not provided)
		- facebook_id: unique ID by Facebook for logging in with Facebook
		- github_id: unique ID by GitHub for logging in with GitHub
		- google_id: unique ID by Google for logging in with Google
		- type: which type of auth flow are we using ("email_login", "email_register", "facebook", "github", "google")
			-"email_login" : get email and password - check if user exists or NOT
			-"email_register": get name, email and pwd - create user if not already exists 
			-"facebook": get name, picture_url and facebook_id
			-"github": get name, email, picture_url and github_id
			-"google": get name, email, picture_url and google_id
	returns:
		- user_id: unique identification number of user in our database
		- user_name
		- user_picture_url
		- message: "OK" if everything went as planned else "some error message"
	"""
	
	message = ""
	user_id = -1
	user_name = ""
	user_picture_url = ""

	if(os.environ.get('DB_AVAILABLE') == "yes"):
		conn = get_db_connection()
		cur = conn.cursor()

		if type == "email_login":
			query = "SELECT user_id, name, picture_url, password FROM App_user WHERE email = %s"

			cur.execute(query, (email,))
			res = cur.fetchone()

			if res is None:
				message = "No such user exists!!"
			else:
				if res[3] == password:
					message = "OK"
					user_id = res[0] 
					user_name = res[1]
					user_picture_url = res[2]
				else:
					message = "Incorrect password!"

		elif type == "email_register":
			query = "SELECT user_id FROM App_user WHERE email = %s"

			cur.execute(query, (email,))
			res = cur.fetchone()

			if res is None:
				query = "INSERT INTO App_user (name, email, picture_url, password) VALUES (%s, %s, %s, %s)"

				cur.execute(query, (name, email, picture_url, password))
				conn.commit()

				query = "SELECT user_id, name, picture_url FROM App_user WHERE email = %s"
				cur.execute(query, (email,))
				res = cur.fetchone()

				if res is None:
					message = "Some Error Occured"
				else:
					message = "OK"
					user_id = res[0]
					user_name = res[1]
					user_picture_url = res[2]
			else:
				message = "Email Already used by another ID, try Logging In"

		elif type == "facebook":
			query = "SELECT user_id, name, picture_url FROM App_user WHERE facebook_id = %s"

			cur.execute(query, (facebook_id,))
			res = cur.fetchone()

			if res is None:
				#create user
				query = "INSERT INTO App_user (name, picture_url, facebook_id) VALUES (%s, %s, %s)"
				
				cur.execute(query, (name, picture_url, facebook_id))
				conn.commit()

				query = "SELECT user_id, name, picture_url FROM App_user WHERE facebook_id = %s"
				cur.execute(query, (facebook_id,))
				res = cur.fetchone()

				if res is None:
					message = "Some Error Occured"
				else:
					message = "OK"
					user_id = res[0]
					user_name = res[1]
					user_picture_url = res[2]
			else:
				#return existing user's data
				message = "OK"
				user_id = res[0]
				user_name = res[1]
				user_picture_url = res[2]

		elif type == "github":
			github_id = str(github_id)
			query = "SELECT user_id, name, picture_url FROM App_user WHERE github_id = %s"

			cur.execute(query, (github_id,))
			res = cur.fetchone()

			if res is None:
				#create user
				query = "INSERT INTO App_user (name, email, picture_url, github_id) VALUES (%s, %s, %s, %s)"
				
				cur.execute(query, (name, email, picture_url, github_id))
				conn.commit()

				query = "SELECT user_id, name, picture_url FROM App_user WHERE github_id = %s"
				cur.execute(query, (github_id,))
				res = cur.fetchone()

				if res is None:
					message = "Some Error Occured"
				else:
					message = "OK"
					user_id = res[0]
					user_name = res[1]
					user_picture_url = res[2]
			else:
				#return existing user's data
				message = "OK"
				user_id = res[0]
				user_name = res[1]
				user_picture_url = res[2]

		elif type == "google":
			query = "SELECT user_id, name, picture_url FROM App_user WHERE google_id = %s"

			cur.execute(query, (google_id,))
			res = cur.fetchone()

			if res is None:
				#create user
				query = "INSERT INTO App_user (name, email, picture_url, google_id) VALUES (%s, %s, %s, %s)"
				
				cur.execute(query, (name, email, picture_url, google_id))
				conn.commit()

				query = "SELECT user_id, name, picture_url FROM App_user WHERE google_id = %s"
				cur.execute(query, (google_id,))
				res = cur.fetchone()

				if res is None:
					message = "Some Error Occured"
				else:
					message = "OK"
					user_id = res[0]
					user_name = res[1]
					user_picture_url = res[2]
			else:
				#return existing user's data
				message = "OK"
				user_id = res[0]
				user_name = res[1]
				user_picture_url = res[2]

		else:
			message = "Invalid Method of Authentication!!"

		cur.close()
		conn.close()
	else:
		message = "No DB_AVAILABLE"

	return message, user_id, user_name, user_picture_url

def delete_question(
	user_id: int,
	question_id: int
):
	response_status = "OK"

	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT user_id FROM Question WHERE question_id = %s"
	cur.execute(query, (question_id,))
	author_user_id = cur.fetchone()

	if author_user_id is None:
		response_status = "an error occured when deleting question"
	else:
		author_user_id = author_user_id[0]

		if author_user_id == user_id:
			query = "DELETE FROM Question WHERE question_id = %s"
			cur.execute(query, (question_id,))
			conn.commit()
		else:
			response_status = "not author"

	cur.close()
	conn.close()

	return response_status

def delete_response(
	user_id: int,
	response_id: int
):
	response_status = "OK"

	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT user_id FROM Response WHERE response_id = %s"
	cur.execute(query, (response_id,))
	author_user_id = cur.fetchone()

	if author_user_id is None:
		response_status = "an error occured when deleting response"
	else:
		author_user_id = author_user_id[0]

		if author_user_id == user_id:
			query = "DELETE FROM Response WHERE response_id = %s"
			cur.execute(query, (response_id,))
			conn.commit()
		else:
			response_status = "not author"

	cur.close()
	conn.close()

	return response_status

def follow_unfollow(
	follower_user_id: int,
	followed_user_id: int
):
	"""
	add follow if not already else remove
	return: followed, unfollowed
	"""
	status = 'following'

	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT 1 FROM Follow WHERE follower_user_id = %s AND followed_user_id = %s"
	cur.execute(query, (follower_user_id, followed_user_id))
	result = cur.fetchone()

	if result is None:
		#don't currently follow
		query = "INSERT INTO Follow (follower_user_id, followed_user_id) VALUES (%s, %s)"

		cur.execute(query, (follower_user_id, followed_user_id))
		conn.commit()
	else:
		status = 'follow'
		query = "DELETE FROM Follow WHERE follower_user_id = %s AND followed_user_id = %s"

		cur.execute(query, (follower_user_id, followed_user_id))
		conn.commit()

	cur.close()
	conn.close()

	return status

def generate_ai_response(
	question_query: str,
	temperature: float = 0.2,
	max_output_tokens: int = 256,
	top_p: float = 0.8,
	top_k: int = 40
):	
	parameters = {
					"temperature": temperature, 
					"max_output_tokens": max_output_tokens,
					"top_p": top_p,
					"top_k": top_k
				}

	prompt = f"generate a infomative response for the following question and try to answer it such that no followups are needed : {question_query}"

	response = model.predict(prompt, **parameters,)

	result = markdown.markdown(response.text)

	return result

def generate_and_add_ai_response_question(
	question_id: int,
	question_query: str
):
	response = generate_ai_response(question_query)

	add_response(user_id =  0, question_id = question_id, response_text = response)

def generate_quiz_questions(
	user_id: int,
	topic_level_pairs: dict,
	number_of_questions: int = 3,
	temperature: float = 0.2,
	max_output_tokens: int = 1000,
	top_p: float = 0.8,
	top_k: int = 40
):	
	"""
	topic-level pairs should be in format 
	('topic_name' : difficulty level number from 1 to 5)

	{
		'topic1' : 'topic1_level',
		'topic2' : 'topic2_level',
		'topic3' : 'topic3_level',
		'topic4' : 'topic4_level',
		'topic5' : 'topic5_level'
	}
	"""

	parameters = {
					"temperature": temperature, 
					"max_output_tokens": max_output_tokens,
					"top_p": top_p,
					"top_k": top_k
	}

	quiz_questions_format = "{questions : [question_text, list_of_4_options, correct_option_number]}"

	prompt = f"Generate {number_of_questions} quiz questions for the following topics with associated difficulty level = {topic_level_pairs}. Respond using JSON = {quiz_questions_format}. Return only the JSON and nothing else."

	response = model.predict(prompt, **parameters,)

	response_text = response.text

	print("response of quiz generation request")
	print(response_text)

	response_text = re.sub(r"[`\n]", "", response_text)
	if response_text[:4] == "json":
		response_text = response_text[4:]
	
	quiz_ai_response = ast.literal_eval(response_text)

	#add these questions to a quiz database and then return the quiz_id (which can be used to fetch the quiz questions)
	return add_quiz_to_db(user_id, quiz_ai_response, topic_level_pairs)

def get_question(
	user_id: int,
	question_id: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = """
		WITH QuestionUser AS (
		    SELECT
		        Question.question_id as question_id, Question.question_title, Question.question_text,
				Question.vote_counter, Question.response_counter, Question.created_time, Question.tags,
				App_user.user_id as question_user_id, App_user.name
		    FROM
		        Question
		        INNER JOIN App_user
		        	ON Question.user_id = App_user.user_id
		    WHERE
		        Question.question_id = %s
		)
		SELECT
		    qu.*, 
		    CASE WHEN f.followed_user_id IS NULL THEN false ELSE true END AS following,
		    CASE WHEN pv.val IS NULL THEN 0 WHEN pv.val = 1 THEN 1 ELSE -1 END AS my_vote
		FROM
		    QuestionUser qu
		    LEFT JOIN Follow f
		    	ON qu.question_user_id = f.followed_user_id AND f.follower_user_id = %s
		    LEFT JOIN Post_Vote as pv
		    	ON qu.question_id = pv.question_id AND pv.user_id = %s
	"""

	cur.execute(query, (question_id, user_id, user_id))

	"""
	alternate_query = "SELECT \
				Question.question_id, Question.question_title, Question.question_text, \
				Question.vote_counter, Question.response_counter, Question.created_time, \
				App_user.user_id, App_user.name, \
				CASE WHEN Follow.followed_user_id IS NULL THEN false ELSE true END AS following	\
			FROM Question \
			INNER JOIN App_user\
			ON Question.user_id = App_user.user_id \
			LEFT JOIN Follow \
				on App_user.user_id = Follow.followed_user_id and Follow.follower_user_id = %s \
			WHERE question_id = %s"

	cur.execute(alternate_query, (user_id, question_id,))
	"""

	question = cur.fetchone()

	if question is None:
		return -1
		
	cur.close()
	conn.close()

	question_keys =	("question_id", "question_title", "question_text", "vote_counter", "response_counter", "created_time", "tags", "user_id", "user_name", "following", "my_vote")
	question = dict(zip(question_keys, question))

	question["question_text"] = markdown.markdown(question["question_text"])

	return question

def get_quiz_questions(
	quiz_id: int,
	limit: int,
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT Quiz.quiz_id, Quiz.title FROM Quiz WHERE quiz_id = %s"
	cur.execute(query, (quiz_id,))
	quiz_details = cur.fetchone()

	quiz_detail_keys = ("quiz_id", "title")
	quiz_details = dict(zip(quiz_detail_keys, quiz_details))

	query = """
		SELECT 
			quiz_question_id, question_text, option_1, option_2, option_3, option_4, correct_answer
		FROM Quiz_Question
		WHERE quiz_id = %s
		ORDER BY quiz_question_id 
		LIMIT %s OFFSET %s
	"""

	cur.execute(query, (quiz_id, limit, offset))
	quiz_questions = cur.fetchall()

	cur.close()
	conn.close()

	if quiz_questions is None:
		quiz_questions = []

	quiz_question_keys = ["quiz_question_id", "question_text", "option_1", "option_2", "option_3", "option_4", "correct_answer"]
	quiz_questions = [dict(zip(quiz_question_keys, quiz_question)) for quiz_question in quiz_questions]

	return quiz_details, quiz_questions

def get_quiz_results(
	user_id: int, 
	quiz_id: int
):

	conn = get_db_connection()
	cur = conn.cursor()

	query = """
		SELECT 
			Quiz.quiz_id, Quiz.title, Quiz_Score_Card.user_id, Quiz_Score_Card.total_quiz_questions, Quiz_Score_Card.attempted, Quiz_Score_Card.correct, Quiz_Score_Card.wrong
		FROM Quiz
		LEFT JOIN Quiz_Score_Card
		ON Quiz.quiz_id = Quiz_Score_Card.quiz_id
		WHERE Quiz.quiz_id = %s AND Quiz_Score_Card.user_id = %s
	"""
	
	cur.execute(query, (quiz_id, user_id))
	quiz_details = cur.fetchone()

	if quiz_details is None:
		print("some error occured when fetching quiz results")
	else:
		quiz_keys = ("quiz_id", "title", "user_id", "total_quiz_questions", "attempted", "correct", "wrong")
		quiz_details = dict(zip(quiz_keys, quiz_details))

		query = """
			SELECT
				Quiz_Question.quiz_question_id, Quiz_Question.question_text, 
				Quiz_Question.option_1, Quiz_Question.option_2, Quiz_Question.option_3, Quiz_Question.option_4, 
				Quiz_Question.correct_answer, Quiz_Question_User_Response.user_response
			FROM Quiz_Question
			LEFT JOIN Quiz_Question_User_Response
			ON Quiz_Question.quiz_question_id = Quiz_Question_User_Response.quiz_question_id
			WHERE Quiz_Question.quiz_id = %s AND Quiz_Question_User_Response.user_id = %s
			ORDER BY Quiz_Question.quiz_question_id
		"""

		cur.execute(query, (quiz_id, user_id))
		quiz_questions_results = cur.fetchall()

		if quiz_questions_results is None:
			quiz_questions_results = []

	cur.close()
	conn.close()

	quiz_result_keys = ["quiz_question_id", "question_text", "option_1", "option_2", "option_3", "option_4", "correct_answer", "user_response"]
	quiz_questions_results = [dict(zip(quiz_result_keys, quiz_questions_result)) for quiz_questions_result in quiz_questions_results]

	return quiz_details, quiz_questions_results

def record_user_quiz_response(
	user_id: int,
	quiz_question_id: int,
	user_response: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = """
		SELECT 1 FROM Quiz_Question_User_Response
		WHERE quiz_question_id = %s AND user_id = %s
	"""

	cur.execute(query, (quiz_question_id, user_id))
	response = cur.fetchone()

	if response is None:
		query = """
			INSERT INTO Quiz_Question_User_Response
				(quiz_question_id, user_id, user_response)
			VALUES
				(%s, %s, %s)
		"""

		cur.execute(query, (quiz_question_id, user_id, user_response))
		conn.commit()
	else:
		query = """
			UPDATE Quiz_Question_User_Response SET user_response = %s WHERE quiz_question_id = %s AND user_id = %s
		"""

		cur.execute(query, (user_response, quiz_question_id, user_id))
		conn.commit()		

	cur.close()
	conn.close()

	return "OK"

def score_user_quiz(
	user_id: int, 
	quiz_id: int
):
	conn = get_db_connection()
	cur = conn.cursor()
	
	total_quiz_questions = 10
	attempted = 0
	correct = 0
	wrong = attempted - correct

	query = """
		SELECT
			COUNT(1) as total_quiz_questions,
			SUM(CASE WHEN Quiz_Question_User_Response.user_response IS NOT NULL THEN 1 ELSE 0 END) AS attempted,
			SUM(CASE WHEN Quiz_Question.correct_answer = Quiz_Question_User_Response.user_response THEN 1 ELSE 0 END) AS correct
		FROM Quiz_Question
		LEFT JOIN Quiz_Question_User_Response
		ON Quiz_Question.quiz_question_id = Quiz_Question_User_Response.quiz_question_id AND Quiz_Question_User_Response.user_id = %s
		WHERE Quiz_Question.quiz_id = %s
	"""

	cur.execute(query, (user_id, quiz_id))
	result = cur.fetchone()

	if result is None:
		print("error occured while scoring quiz")
	else:
		total_quiz_questions = result[0]
		attempted = result[1]
		correct = result[2]
		wrong = attempted - correct

	query = "SELECT 1 FROM Quiz_Score_Card WHERE quiz_id = %s AND user_id = %s"
	cur.execute(query, (quiz_id, user_id))
	result = cur.fetchone()

	if result is None:
		query = "INSERT INTO Quiz_Score_Card (quiz_id, user_id, total_quiz_questions, attempted, correct, wrong) VALUES (%s, %s, %s, %s, %s, %s)"

		cur.execute(query, (quiz_id, user_id, total_quiz_questions, attempted, correct, wrong))
		conn.commit()
	else:
		query = "UPDATE Quiz_Score_Card SET total_quiz_questions = %s, attempted = %s, correct = %s, wrong = %s WHERE quiz_id = %s AND user_id = %s"

		cur.execute(query, (total_quiz_questions, attempted, correct, wrong, quiz_id, user_id))
		conn.commit()

	cur.close()
	conn.close()

	return "OK"

def handle_question_vote(
	user_id: int,
	question_id: int,
	up_or_down_vote: str
):
	conn = get_db_connection()
	cur = conn.cursor()

	#extract post_id
	query = "SELECT post_id FROM Question WHERE question_id = %s"
	cur.execute(query, (question_id,))
	post_id = cur.fetchone()[0]

	#check if user has a vote on this post or not and if yes what vote
	query = "SELECT val FROM Post_Vote WHERE question_id = %s AND user_id = %s"
	cur.execute(query, (question_id, user_id))
	result = cur.fetchone()

	if result is None:
		#no existing vote
		#cast new vote
		if up_or_down_vote == 'up':
			#only add up vote
			my_vote = +1
			counter_update = +1
		else:
			#only add down vote
			my_vote = -1
			counter_update = -1
	else:
		#vote already exists
		val = result[0]

		#remove the existing vote
		query = "DELETE FROM Post_Vote WHERE question_id = %s AND user_id = %s"
		cur.execute(query, (question_id, user_id))
		conn.commit()

		if up_or_down_vote == 'up':
			if val == 1:
				#remove up vote
				my_vote = 0
				counter_update = -1
			else:
				#remove down vote - also we'll have to add a up vote
				my_vote = +1
				counter_update = +2
		else:
			if val == 1:
				#remove up vote - also we'll have to add a down vote
				my_vote = -1
				counter_update = -2
			else:
				#remove down vote
				my_vote = 0
				counter_update = +1

	if my_vote != 0:
		query = "INSERT INTO Post_Vote (question_id, user_id, val) VALUES (%s, %s, %s)"
		cur.execute(query, (question_id, user_id, my_vote))
		conn.commit()

	query = "UPDATE Post SET vote_counter = vote_counter + %s WHERE post_id = %s"
	cur.execute(query, (counter_update, post_id))
	conn.commit()

	query = "SELECT vote_counter FROM Post WHERE post_id = %s"
	cur.execute(query, (post_id,))
	vote_count = cur.fetchone()[0]

	cur.close()
	conn.close()

	return vote_count, my_vote

def handle_response_vote(
	user_id: int,
	response_id: int,
	up_or_down_vote: str
):
	conn = get_db_connection()
	cur = conn.cursor()

	#extract post_id
	query = "SELECT post_id FROM Response WHERE response_id = %s"
	cur.execute(query, (response_id,))
	post_id = cur.fetchone()[0]

	#check if user has a vote on this post or not and if yes what vote
	query = "SELECT val FROM Post_Vote WHERE response_id = %s AND user_id = %s"
	cur.execute(query, (response_id, user_id))
	result = cur.fetchone()

	if result is None:
		#no existing vote
		#cast new vote
		if up_or_down_vote == 'up':
			#only add up vote
			my_vote = +1
			counter_update = +1
		else:
			#only add down vote
			my_vote = -1
			counter_update = -1
	else:
		#vote already exists
		val = result[0]

		#remove the existing vote
		query = "DELETE FROM Post_Vote WHERE response_id = %s AND user_id = %s"
		cur.execute(query, (response_id, user_id))
		conn.commit()

		if up_or_down_vote == 'up':
			if val == 1:
				#remove up vote
				my_vote = 0
				counter_update = -1
			else:
				#remove down vote - also we'll have to add a up vote
				my_vote = +1
				counter_update = +2
		else:
			if val == 1:
				#remove up vote - also we'll have to add a down vote
				my_vote = -1
				counter_update = -2
			else:
				#remove down vote
				my_vote = 0
				counter_update = +1

	if my_vote != 0:
		query = "INSERT INTO Post_Vote (response_id, user_id, val) VALUES (%s, %s, %s)"
		cur.execute(query, (response_id, user_id, my_vote))
		conn.commit()

	query = "UPDATE Post SET vote_counter = vote_counter + %s WHERE post_id = %s"
	cur.execute(query, (counter_update, post_id))
	conn.commit()

	query = "SELECT vote_counter FROM Post WHERE post_id = %s"
	cur.execute(query, (post_id,))
	vote_count = cur.fetchone()[0]

	cur.close()
	conn.close()

	return vote_count, my_vote

def load_more_questions(
	user_id: int,
	num_to_load: int,
	offset: int
):

	"""
	load more questions for the "For You" page
	params:
		user_id,
		num_to_load: limit,
		offset
	returns:
		list of questions
		where each question is a dictonary of values
		("question_id", "question_text", "vote_counter", "response_counter", "created_time", "user_id", "user_name")
	"""

	conn = get_db_connection()
	cur = conn.cursor()

	"""
	SELECT \
		Question.question_id, Question.question_title, Question.vote_counter, Question.response_counter, Question.created_time, App_user.user_id, App_user.name\
	FROM Question \
	INNER JOIN App_user\
		ON Question.user_id = App_user.user_id\
	LIMIT %s OFFSET %s
	"""

	query = """
		SELECT 
			Question.question_id, Question.question_title, Question.vote_counter, Question.response_counter, 
			Question.created_time, Question.tags, 
			App_user.user_id, App_user.name, 
			CASE WHEN Follow.followed_user_id IS NULL THEN false ELSE true END AS following	
		FROM Question 
		INNER JOIN App_user
			ON Question.user_id = App_user.user_id
		LEFT JOIN Follow 
			on App_user.user_id = Follow.followed_user_id and Follow.follower_user_id = %s 
		ORDER BY Question.created_time DESC
		LIMIT %s OFFSET %s;
	"""

	cur.execute(query, (user_id, num_to_load, offset))
	questions = cur.fetchall()

	cur.close()
	conn.close()

	if questions is None:
		questions = []

	question_keys = ("question_id", "question_title", "vote_counter", "response_counter", "created_time", "tags", "user_id", "user_name", "following")
	questions = [dict(zip(question_keys, question)) for question in questions]

	return questions

def load_more_quizzes(
	user_id: int,
	limit: int, 
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = """
		SELECT 
			Quiz.quiz_id, Quiz.title, Quiz.created_time, 
			Quiz_Score_Card.user_id, Quiz_Score_Card.total_quiz_questions, Quiz_Score_Card.attempted, Quiz_Score_Card.correct, Quiz_Score_Card.wrong,
			App_user.name
		FROM Quiz
		LEFT JOIN Quiz_Score_Card
		ON Quiz.quiz_id = Quiz_Score_Card.quiz_id
		LEFT JOIN App_user
		ON Quiz.user_id = App_user.user_id
		WHERE Quiz_Score_Card.user_id = %s
		ORDER BY Quiz.created_time
		LIMIT %s OFFSET %s
	"""

	cur.execute(query, (user_id, limit, offset))
	quizzes = cur.fetchall()

	cur.close()
	conn.close()

	quiz_keys = ("quiz_id", "title", "created_time", "user_id", "total_quiz_questions", "attempted", "correct", "wrong", "user_name")
	quizzes = [dict(zip(quiz_keys, quiz)) for quiz in quizzes]

	return quizzes

def load_more_responses(
	user_id: int,
	question_id: int,
	limit: int,
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = """
		WITH ResponseUser AS (
		    SELECT
		        Response.response_id as Response_id, Response.response_text,
				Response.vote_counter, Response.response_counter, Response.created_time,
				App_user.user_id as Response_user_id, App_user.name
		    FROM
		        Response
		        INNER JOIN App_user
		        	ON Response.user_id = App_user.user_id
		    WHERE
		        Response.question_id = %s
		)
		SELECT
		    ru.*, 
		    CASE WHEN f.followed_user_id IS NULL THEN false ELSE true END AS following,
		    CASE WHEN pv.val IS NULL THEN 0 WHEN pv.val = 1 THEN 1 ELSE -1 END AS my_vote
		FROM
		    ResponseUser ru
		    LEFT JOIN Follow f
		    	ON ru.Response_user_id = f.followed_user_id AND f.follower_user_id = %s
		    LEFT JOIN Post_Vote as pv
		    	ON ru.Response_id = pv.response_id AND pv.user_id = %s
		LIMIT %s OFFSET %s
	"""

	cur.execute(query, (question_id, user_id, user_id, limit, offset))

	"""
	query =	"SELECT \
				Response.response_id, Response.response_text, Response.vote_counter, \
				Response.response_counter, Response.created_time, App_user.user_id, App_user.name, \
				CASE WHEN Follow.followed_user_id IS NULL THEN false ELSE true END AS following	\
			FROM Response \
			INNER JOIN App_user \
				ON Response.user_id = App_user.user_id \
			LEFT JOIN Follow \
				on App_user.user_id = Follow.followed_user_id and Follow.follower_user_id = %s \
			WHERE question_id = %s \
			LIMIT %s OFFSET %s"

	cur.execute(query, (user_id, question_id, limit, offset))
	"""

	responses = cur.fetchall()

	cur.close()
	conn.close()

	if responses is None:
		responses = []

	response_keys = ("response_id", "response_text", "vote_counter", "response_counter", "created_time", "user_id", "user_name", "following", "my_vote")
	responses = [dict(zip(response_keys, response)) for response in responses]

	for response in responses:
		response['response_text'] = markdown.markdown(response['response_text'])

	return responses

def load_more_web_search_results(
	question_id: int,
	limit: int,
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT \
				title, description, link \
			FROM Related_web_search_result \
			WHERE question_id = %s \
			LIMIT %s OFFSET %s"

	cur.execute(query, (question_id, limit, offset))
	web_search_results = cur.fetchall()

	cur.close()
	conn.close()

	if web_search_results is None:
		web_search_results = []

	web_search_results_keys = ("title", "description", "link")
	web_search_results = [dict(zip(web_search_results_keys, web_search_result)) for web_search_result in web_search_results]

	return web_search_results

def load_more_video_results(
	question_id: int,
	limit: int,
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT \
				title, description, video_url, thumbnail_url, channel_title, player_embed_html \
			FROM Related_video \
			WHERE question_id = %s \
			LIMIT %s OFFSET %s"

	cur.execute(query, (question_id, limit, offset))
	video_results = cur.fetchall()

	cur.close()
	conn.close()

	if video_results is None:
		video_results = []

	video_results_keys = ("title", "description", "video_url", "thumbnail_url", "channel_title", "player_embed_html")
	video_results = [dict(zip(video_results_keys, video_result)) for video_result in video_results]

	return video_results

def load_more_related_questions(
	question_id: int,
	limit: int,
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT \
				Question.question_id, Question.question_title \
			FROM Related_question \
			LEFT JOIN Question \
			ON Related_question.similar_question_id = Question.question_id\
			WHERE Related_question.question_id = %s \
			LIMIT %s OFFSET %s"

	cur.execute(query, (question_id, limit, offset))
	similar_questions = cur.fetchall()

	cur.close()
	conn.close()

	if similar_questions is None:
		return []

	similar_question_keys = ("question_id", "question_title")
	similar_questions = [dict(zip(similar_question_keys, similar_question)) for similar_question in similar_questions]

	return similar_questions

def make_web_search_request(
	search_query: str,
	num:int = 10
):
	payload = {
		'key': os.environ.get('API_KEY'),
		'q': search_query,
		'cx': os.environ.get('SEARCH_ENGINE_ID'),
		'num': num
	}

	response = requests.get('https://www.googleapis.com/customsearch/v1', params=payload)
	if response.status_code != 200:
		return -1

	return response.json()

def make_youtube_video_search_request(
	search_query: str,
	num:int = 10
):
	search_params = {
		'key' : os.environ.get('API_KEY'),
		'q': search_query,
		'part': 'snippet',
		'maxResults': num,
		'type' : 'video'
	}

	response = requests.get('https://www.googleapis.com/youtube/v3/search', params=search_params)

	if response.status_code != 200:
		return -1

	response = response.json()
	#now we need to fetch the player which we can then embed on our html page
	video_results = dict()
	video_ids = []

	for response_item in response['items']:
		video_results[response_item['id']['videoId']] = {
			"title": response_item["snippet"]["title"],
			"description": response_item["snippet"]["description"],
			"thumbnail_url": response_item["snippet"]["thumbnails"]["high"]["url"],
			"channel_title" : response_item["snippet"]["channelTitle"],
			"player_embed_html": ""
		}
		
		video_ids.append(response_item['id']['videoId'])

	video_params = {
		'key': os.environ.get('API_KEY'),
		'id': ','.join(video_ids),
		'part': 'player',
		'maxResults': num
	}

	response = requests.get('https://www.googleapis.com/youtube/v3/videos', params=video_params)

	if response.status_code != 200:
		return video_results

	response = response.json()

	for response_item in response.get('items', []):
		video_results[response_item["id"]]['player_embed_html'] = response_item["player"]["embedHtml"]

	return video_results

def question_search(
	user_id: int,
	search_query: str,
	limit: int,
	offset: int
):	
	conn = get_db_connection()
	cur = conn.cursor()

	query = """
		SELECT
			Question.question_id, Question.question_title,
			Question.vote_counter, Question.response_counter, Question.created_time, Question.tags,
			App_user.user_id, App_user.name,
			CASE WHEN f.followed_user_id IS NULL THEN false ELSE true END AS following,
			ts_rank_cd(document_vectors, query) as rank
		FROM Question
		INNER JOIN App_user
		        	ON Question.user_id = App_user.user_id
		LEFT JOIN Follow f
		    	ON Question.user_id = f.followed_user_id AND f.follower_user_id = %s
		, websearch_to_tsquery(%s) query
		WHERE document_vectors @@ query 
		ORDER BY rank DESC
		LIMIT %s OFFSET %s;
	"""

	text_highlight_query = """
		SELECT
			Question.question_id,
			ts_headline(Question.question_title, query) as question_title,
			Question.vote_counter, Question.response_counter, Question.created_time, Question.tags,
			App_user.user_id, App_user.name,
			CASE WHEN f.followed_user_id IS NULL THEN false ELSE true END AS following,
			ts_rank_cd(document_vectors, query) as rank
		FROM Question
		INNER JOIN App_user
		        	ON Question.user_id = App_user.user_id
		LEFT JOIN Follow f
		    	ON Question.user_id = f.followed_user_id AND f.follower_user_id = %s
		, websearch_to_tsquery(%s) query
		WHERE document_vectors @@ query 
		ORDER BY rank DESC
		LIMIT %s OFFSET %s;
	"""

	cur.execute(text_highlight_query, (user_id, search_query, limit, offset))
	search_results = cur.fetchall()

	cur.close()
	conn.close()

	if search_results is None:
		search_results = []
	
	search_result_keys = (
						"question_id", "question_title", "vote_counter", "response_counter", 
						"created_time", "tags", "user_id", "user_name", "following", "rank"
					)

	search_results = [dict(zip(search_result_keys, search_result)) for search_result in search_results]

	return search_results

def vote_unvote(
	user_id: int,
	question_id: int,
	response_id: int,
	post_type: str,
	up_or_down_vote: str
):
	"""
	post_type can "question" or "response"
	vote can be "up" or "down"
	
	my_vote:
		0: show nothing highlighted
		+1: show up_vote highlighted
		-1: show down_vote highlighted

	if user already have vote on post:
		delete record 

		if up_vote and val == 1:
			my_vote = 0
			counter = -1
		else if up_vote and val == -1:
			my_vote = +1
			counter = +1
		else if down vote and val == -1:
			my_vote = 0
			counter = +1
		else if down and val == 1:
			my_vote = -1
			counter = -1
	else:
		insert new record with user_id, post_id and val
		if up:
			my_vote = +1
			counter = +1
		else if down:
			my_vote = -1
			counter = -1

	returns vote_count, my_vote
	"""

	if post_type == 'question':
		return handle_question_vote(user_id, question_id, up_or_down_vote)
	else:
		return handle_response_vote(user_id, response_id, up_or_down_vote)


#functions to implement for articles
def get_article_preview(
	user_id: int,
	article_id: int
):
	pass

def add_article(
	user_id: int,
	title: str,
	contents: str,
	tags: str
):
	tags = [tag.strip() for tag in tags.split(',')]
	tags = str(set(tags))
	tags = re.sub(r"[']", "", tags)
	
	description = contents[:50]

	conn = get_db_connection()
	cur = conn.cursor()

	query = "INSERT INTO Article (user_id, title, description, contents, tags) VALUES (%s, %s, %s, %s, %s)"

	cur.execute(query, (user_id, title, description, contents, tags))
	conn.commit()

	query = "SELECT article_id FROM Article WHERE user_id = %s ORDER BY created_time DESC LIMIT 1"
	cur.execute(query, (user_id,))
	article_id = cur.fetchone()

	if article_id is None:
		article_id = -1
	else:
		article_id = article_id[0]

	cur.close()
	conn.close()

	return article_id

def get_article(
	user_id: int,
	article_id: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = """
		WITH Article_User AS (
		    SELECT 
				Article.article_id as article_id, Article.title, Article.contents, Article.vote_counter, Article.response_counter, 
				Article.created_time, Article.tags, 
				App_user.user_id as author_user_id, App_user.name
			FROM Article 
			INNER JOIN App_user
				ON Article.user_id = App_user.user_id
		    WHERE
		        Article.article_id = %s
		)
		SELECT
		    au.*, 
		    CASE WHEN f.followed_user_id IS NULL THEN false ELSE true END AS following,
		    0 as my_vote
		FROM Article_User au
	    LEFT JOIN Follow f
	    	ON au.author_user_id = f.followed_user_id AND f.follower_user_id = %s
	"""

	cur.execute(query, (article_id, user_id))

	article = cur.fetchone()

	if article is None:
		return -1
		
	cur.close()
	conn.close()

	article_keys =	("article_id", "title", "contents", "vote_counter", "response_counter", "created_time", "tags", "user_id", "user_name", "following", "my_vote")
	article = dict(zip(article_keys, article))

	article["contents"] = markdown.markdown(article["contents"])

	return article

def add_article_response(
	user_id: int,
	contents: str
):
	pass

def load_more_articles(
	user_id: int,
	limit: int,
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = """
		SELECT 
			Article.article_id, Article.title, Article.description, Article.thumbnail_url, Article.vote_counter, Article.response_counter, 
			Article.created_time, Article.tags, 
			App_user.user_id, App_user.name, 
			CASE WHEN Follow.followed_user_id IS NULL THEN false ELSE true END AS following	
		FROM Article 
		INNER JOIN App_user
			ON Article.user_id = App_user.user_id
		LEFT JOIN Follow 
			on App_user.user_id = Follow.followed_user_id and Follow.follower_user_id = %s 
		ORDER BY Article.created_time DESC
		LIMIT %s OFFSET %s;
	"""

	cur.execute(query, (user_id, limit, offset))
	articles = cur.fetchall()

	cur.close()
	conn.close()

	if articles is None:
		articles = []

	article_keys = ("article_id", "title", "description", "thumbnail_url", "vote_counter", "response_counter", "created_time", "tags", "user_id", "user_name", "following")
	articles = [dict(zip(article_keys, article)) for article in articles]

	return articles

def load_more_article_responses(
	user_id: int,
	article_id: int,
	limit: int,
	offset: int
):
	pass

def handle_article_vote(
	user_id: int,
	article_id: int,
	up_or_down_vote: str
):
	pass

def handle_article_response_vote(
	user_id: int,
	article_response_id: int,
	up_or_down_vote: str
):
	pass

def article_search(
	user_id: int,
	search_query: str,
	limit: int,
	offset: int
):
	pass

def add_article_response_comment(
	user_id: int, 
	article_response_id: int,
	contents: str,
):
	pass

def load_more_article_response_comments(
	user_id: int, 
	article_response_id: int,
	limit: int,
	offset: int
):
	pass

def delete_article(
	user_id: int,
	article_id: int
):
	pass

def delete_article_response(
	user_id: int,
	article_response_id: int
):
	pass

#COMMENT functions to be implemented
def add_comment(
	user_id: int,
	response_id: int,
	contents: str
):
	pass

def load_more_comments(
	user_id: int,
	response_id: int,
	limit: int,
	offset: int
):
	pass

