import os
import psycopg2

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

