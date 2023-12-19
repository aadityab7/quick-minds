#import the complete flask app from the project folder / library 
#and start the flask web app if this file is executed.

from project import app
import os

if __name__ == '__main__':
  app.run(
    debug = True,
    host = "0.0.0.0", 
    port = int(os.environ.get("PORT",8080)), 
    ssl_context="adhoc"
  )


#app.run(debug = True)
#app.run(debug = True, host = "0.0.0.0", port = int(os.environ.get("PORT",8080)), ssl_context="adhoc")
#app.run(debug = True, host = "0.0.0.0", port = int(os.environ.get("PORT",8080)))