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
			query = "SELECT user_id, name, picture_url FROM App_user WHERE github_id = '%s'"

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

	"""
	SELECT \
		Question.question_id, Question.question_title, Question.vote_counter, Question.response_counter, Question.created_time, App_user.user_id, App_user.name\
	FROM Question \
	INNER JOIN App_user\
		ON Question.user_id = App_user.user_id\
	LIMIT %s OFFSET %s
	"""

	query = "SELECT \
				Question.question_id, Question.question_title, Question.vote_counter, Question.response_counter, \
				Question.created_time, App_user.user_id, App_user.name, \
				CASE WHEN Follow.followed_user_id IS NULL THEN false ELSE true END AS following	\
			FROM Question \
			INNER JOIN App_user\
				ON Question.user_id = App_user.user_id\
			LEFT JOIN Follow \
				on App_user.user_id = Follow.followed_user_id and Follow.follower_user_id = %s \
			LIMIT %s OFFSET %s;"

	cur.execute(query, (user_id, num_to_load, offset))
	questions = cur.fetchall()
	
	if questions is None:
		questions = []

	question_keys = ("question_id", "question_title", "vote_counter", "response_counter", "created_time", "user_id", "user_name", "following")
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


def handle_question_vote(
	user_id,
	question_id,
	up_or_down_vote
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
			#added up vote
			value = 1
			my_vote = 0
			counter_update = +1
		else:
			#added down vote
			value = -1
			my_vote = 1
			counter_update = -1


		query = "INSERT INTO Post_Vote (question_id, user_id, val) VALUES (%s, %s, %s)"
		cur.execute(query, (question_id, user_id, value))
		conn.commit()
		
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
				my_vote = 2
				counter_update = -1
			else:
				#remove down vote
				my_vote = 3
				counter_update = +1
		else:
			if val == 1:
				#remove up vote
				my_vote = 2
				counter_update = -1
			else:
				#remove down vote
				my_vote = 3
				counter_update = +1

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
	user_id,
	response_id,
	up_or_down_vote
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
			#added up vote
			value = 1
			my_vote = 0
			counter_update = +1
		else:
			#added down vote
			value = -1
			my_vote = 1
			counter_update = -1

		query = "INSERT INTO Post_Vote (response_id, user_id, val) VALUES (%s, %s, %s)"
		cur.execute(query, (response_id, user_id, value))
		conn.commit()

		
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
				my_vote = 2
				counter_update = -1
			else:
				#remove down vote
				my_vote = 3
				counter_update = +1
		else:
			if val == 1:
				#remove up vote
				my_vote = 2
				counter_update = -1
			else:
				#remove down vote
				my_vote = 3
				counter_update = +1

	query = "UPDATE Post SET vote_counter = vote_counter + %s WHERE post_id = %s"
	cur.execute(query, (counter_update, post_id))
	conn.commit()

	query = "SELECT vote_counter FROM Post WHERE post_id = %s"
	cur.execute(query, (post_id,))
	vote_count = cur.fetchone()[0]

	cur.close()
	conn.close()

	return vote_count, my_vote

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
		0: add up_vote
		1: add down_vote
		2: remove up_vote
		3: remove down_vote

	if user already have vote on post:
		delete record 

		if up_vote and val == 1:
			my_vote = 2
			counter = -1
		else if up_vote and val == -1:
			my_vote = 3
			counter = +1
		else if down vote and val == -1:
			my_vote = 3
			counter = +1
		else if down and val == 1:
			my_vote = 2
			counter = -1
	else:
		insert new record with user_id, post_id and val
		if up:
			my_vote = 0
			counter = +1
		else if down:
			my_vote = 1
			counter = -1

	returns vote_count, my_vote
	"""

	if post_type == 'question':
		return handle_question_vote(user_id, question_id, up_or_down_vote)
	else:
		return handle_response_vote(user_id, response_id, up_or_down_vote)


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

def get_question(
	user_id: int,
	question_id: int
):
	conn = get_db_connection()
	cur = conn.cursor()

	query = "SELECT \
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

	cur.execute(query, (user_id, question_id,))
	question = cur.fetchone()

	if question is None:
		return -1
		
	question_keys = ("question_id", "question_title", "question_text", "vote_counter", "response_counter", "created_time", "user_id", "user_name", "following")
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
	user_id: int,
	question_id: int,
	limit: int,
	offset: int
):
	conn = get_db_connection()
	cur = conn.cursor()

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
	responses = cur.fetchall()

	if responses is None:
		responses = []

	response_keys = ("response_id", "response_text", "vote_counter", "response_counter", "created_time", "user_id", "user_name", "following")
	responses = [dict(zip(response_keys, response)) for response in responses]

	for response in responses:
		response['response_text'] = markdown.markdown(response['response_text'])

	cur.close()
	conn.close()

	return responses