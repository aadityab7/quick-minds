# Update the requirements.txt file

1. `pip freeze > requirements.txt`

# Build Tailwind CSS file

Steps to follow for set up : [https://tailwindcss.com/docs/installation](https://tailwindcss.com/docs/installation)

1. `npx tailwindcss -i ./project/static/CSS/input.css -o ./project/static/CSS/output.css`

# Update GitHub Repository

1. check status of changes made: `git status`
2. stage changes: `git add .`
3. `git commit -m "msg"`
4. `git push origin main` 

# To deploy the latest version of app from local environment to cloud

1. `gcloud run deploy quick-minds --source .`

**NOTE**: here `quick-minds` is the name of my service


# To initialize database from cloud shell:	

1. Create a Cloud SQL instance with PostgreSQL and in that create a database `quickminds`
2. Go to [https://console.cloud.google.com/welcome?project=airy-period-401611&cloudshell=true](https://console.cloud.google.com/welcome?project=airy-period-401611&cloudshell=true)
3. `gcloud sql connect quickminds --user=postgres`
4. Enter DB_PASSWORD
5. `\c quickminds`
6. Enter DB_PASSWORD
7. copy and paste all the drop table commands
8. copy and paste all the create table commands

# Steps to create google cloud storage (bucket):

1. `gsutil mb gs://quickmindsimagestoragebucket`
2. `gsutil defacl set public-read gs://quickmindsimagestoragebucket`

# The environment variables needed:

- PORT
- DB_AVAILABLE
- DEVELOPMENT_SERVER
- DB_PORT
- DB_USERNAME
- DB_PASSWORD
- DB_NAME
- DB_HOST
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- FACEBOOK_CLIENT_ID
- FACEBOOK_CLIENT_SECRET
- GITHUB_CLIENT_ID
- GITHUB_CLIENT_SECRET
- SEARCH_ENGINE_ID
- STORAGE_BUCKET_NAME
- API_KEY

# To use Google Search API for web search:

1. Enable Custom Search API
2. Create a custom search engine (named : **quick minds web search**)
3. Get the Search Engine ID
4. The search API request will need to include:
	- cx: name of custom search engine
	- q: query string
	- num: number of search results to get (max = 10)
	- api_key: for auth