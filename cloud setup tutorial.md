# To initialize database from cloud shell:	

1. `gcloud sql connect quickminds --user=postgres`
2. Enter DB_PASSWORD
3. `/c quickminds`
4. Enter DB_PASSWORD
5. copy and paste all the drop commands
6. copy and paste all the create commands

# To deploy the latest version of app from local environment to cloud

1. `gcloud run deploy --source .`
2. Select the default service name **quick-minds** by pressing enter

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