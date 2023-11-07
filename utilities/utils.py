import os
import psycopg2
import markdown

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

	query = "SELECT \
				Question.question_id, Question.question_title, Question.vote_counter, Question.response_counter, Question.created_time, App_user.user_id, App_user.name\
			FROM Question \
			INNER JOIN App_user\
				ON Question.user_id = App_user.user_id\
			LIMIT %s OFFSET %s"

	cur.execute(query, (num_to_load, offset))
	questions = cur.fetchall()
	
	if questions is None:
		questions = []

	question_keys = ("question_id", "question_title", "vote_counter", "response_counter", "created_time", "user_id", "user_name")
	questions = [dict(zip(question_keys, question)) for question in questions]

	cur.close()
	conn.close()

	return questions

def add_question(
	user_id: int,
	question_title: str,
	question_text:str
):

	conn = get_db_connection()
	cur = conn.cursor()

	query = "INSERT INTO Question (user_id, question_title, question_text) VALUES (%s, %s, %s)"

	cur.execute(query, (user_id, question_title, question_text))
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

	return question_id

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

	query = "SELECT \
				Response.response_id, Response.response_text, Response.vote_counter, Response.response_counter, Response.created_time, App_user.user_id, App_user.name\
			FROM Response \
			INNER JOIN App_user\
				ON Response.user_id = App_user.user_id\
			WHERE Response.user_id = %s \
			ORDER BY Response.created_time DESC LIMIT 1"
	
	cur.execute(query, (user_id,))
	response = cur.fetchone()

	cur.close()
	conn.close()

	if response is None:
		return -1

	response_keys = ("response_id", "response_text", "vote_counter", "response_counter", "created_time", "user_id", "user_name")
	response = dict(zip(response_keys, response))

	return response

def vote_unvote(
	post_id: int,
	user_id: int,
	vote_type: str
):
	"""
	vote_type = "up" or "down"
	add vote if doesn't exists already else remove vote
	return +1 for upvote -1 for down vote and 0 for vote removal
	"""

	val = 1 if vote_type == 'up' else -1

	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT 1 FROM Post_Vote WHERE post_id = %s AND user_id = %s"
	cur.execute(query, (post_id, user_id))
	result = cur.fetchone()

	if result is None:
		#vote doesn't exists
		query = "INSERT INTO Post_Vote (post_id, user_id, val) VALUES (%s, %s, %s)"

		cur.execute(query, (post_id, user_id, val))
		conn.commit()
	else:
		val = 0
		query = "DELETE FROM Post_Vote WHERE post_id = %s AND user_id = %s"

		cur.execute(query, (post_id, user_id))
		conn.commit()

	cur.close()
	conn.close()

	return val

def follow_unfollow(
	follower_user_id: int,
	followed_user_id: int
):
	"""
	add follow if not already else remove
	return: followed, unfollowed
	"""
	status = 'followed'

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
		status = 'unfollowed'
		query = "DELETE FROM Follow WHERE follower_user_id = %s AND followed_user_id = %s"

		cur.execute(query, (follower_user_id, followed_user_id))
		conn.commit()

	cur.close()
	conn.close()

	return status

def get_question(
	question_id: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT \
				Question.question_id, Question.question_title, Question.question_text, Question.vote_counter, Question.response_counter, Question.created_time, App_user.user_id, App_user.name \
			FROM Question \
			INNER JOIN App_user\
			ON Question.user_id = App_user.user_id \
			WHERE question_id = %s"

	cur.execute(query, (question_id,))
	question = cur.fetchone()

	if question is None:
		return -1
		
	question_keys = ("question_id", "question_title", "question_text", "vote_counter", "response_counter", "created_time", "user_id", "user_name")
	question = dict(zip(question_keys, question))

	cur.close()
	conn.close()

	question["question_text"] = markdown.markdown(question["question_text"])

	return question

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

def load_more_responses(
	question_id: int,
	limit: int,
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query =	"SELECT \
				Response.response_id, Response.response_text, Response.vote_counter, Response.response_counter, Response.created_time, App_user.user_id, App_user.name \
			FROM Response \
			INNER JOIN App_user \
				ON Response.user_id = App_user.user_id \
			WHERE question_id = %s \
			LIMIT %s OFFSET %s"

	cur.execute(query, (question_id, limit, offset))
	responses = cur.fetchall()

	if responses is None:
		responses = []

	response_keys = ("response_id", "response_text", "vote_counter", "response_counter", "created_time", "user_id", "user_name")
	responses = [dict(zip(response_keys, response)) for response in responses]

	cur.close()
	conn.close()

	return responses