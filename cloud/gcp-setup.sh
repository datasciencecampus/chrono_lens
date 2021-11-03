#!/bin/bash
set -e

if [[ $# -ne 2 ]] ; then
    echo 'You must provide "[project id]" "[branch id]" as two arguments'
    exit 0
fi

# script variables
export PROJECT_ID=$1-$2

# Check PROJECT_ID is legal (not too long; 30 chars max; also 6 chars min)
if [[ ${#PROJECT_ID} -gt 30 ]]; then
    echo
    echo "*** ERROR ***"
    echo "PROJECT_ID='$PROJECT_ID' is longer than 30 characters; cannot use"
    echo "Exiting..."
    echo
    exit
fi

# Check GCP_FOLDER_NAME is defined
if [[ -z ${GCP_FOLDER_NAME} ]]; then
    echo
    echo "*** ERROR ***"
    echo "GCP_FOLDER_NAME not defined in environment"
    echo
    echo "This is the name of the folder where your project will be created; look at the GCP web pages - the"
    echo "project selection drop-down can offer 'all' projects - find your folder in there. Select that name;"
    echo "confirm with your local GCP account holder. For example under 'yourcompany' there may be a folder"
    echo "called 'myproject' that you are to use."
    echo
    echo "With the above example, you may need to enter: export GCP_FOLDER_NAME=myproject"
    echo
    echo "Exiting..."
    echo
    exit
fi


REGION="europe-west2"  # europe-west2 is London
ZONE="europe-west2-a"  # europe-west2-a has T4 GPUs if needs be
# folder id for the area where project needs to be created in

SOURCES_BUCKET_NAME="sources-${PROJECT_ID}"
LABELS_BUCKET_NAME="labels-${PROJECT_ID}"
DATA_BUCKET_NAME="data-${PROJECT_ID}"
MODELS_BUCKET_NAME="models-${PROJECT_ID}"
EXPORTS_BUCKET_NAME="exports-${PROJECT_ID}"

ORGANIZATION_ID=`gcloud organizations list --format="value(ID)"`
BILLING_ACCOUNT_ID=`gcloud beta billing accounts list --format="value(ACCOUNT_ID)"`
FOLDER_ID=`gcloud resource-manager folders list --organization ${ORGANIZATION_ID} --filter="DISPLAY_NAME=${GCP_FOLDER_NAME}" --format="value(ID)"`

# Check FOLDER_ID is defined
if [[ -z ${FOLDER_ID} ]]; then
    echo
    echo "*** ERROR ***"
    echo "FOLDER_ID was not set by script"
    echo
    echo "Usually an indication that GCP_FOLDER_NAME was not correctly defined in the environment or the"
    echo "ORGANIZATION_ID failed to be set from 'gcloud organisations list' a few lines earlier in the script."
    echo
    echo "Exiting..."
    echo
    exit
fi


echo "*** INFO 1/12: Requesting for Authentication ***"
echo
gcloud auth login


echo
echo "*** INFO 2/12: Creating Project ***"
echo
gcloud projects create ${PROJECT_ID} \
    --folder ${FOLDER_ID}

PROJECT_NUMBER=`gcloud projects list --filter=${PROJECT_ID} --format="value(PROJECT_NUMBER)"`

echo
echo "*** INFO 3/12: Link Project to billing account ***"
echo
gcloud alpha billing projects link ${PROJECT_ID} \
    --billing-account ${BILLING_ACCOUNT_ID}


echo
echo "*** INFO 4/12: Selecting Project ***"
echo
gcloud config set project ${PROJECT_ID}


echo
echo "*** INFO 5/12: Enabling GCP APIs ***"
echo
gcloud services enable compute.googleapis.com               # general resources - needed before anything is created
gcloud services enable cloudresourcemanager.googleapis.com  # access GCP resource metadata (e.g. permissions)
gcloud services enable cloudbuild.googleapis.com            # github triggers
gcloud services enable cloudfunctions.googleapis.com        # cloud functions
gcloud services enable cloudscheduler.googleapis.com        # cloud scheduler (crontab for cloud)
gcloud services enable appengine.googleapis.com             # appengine needed for cloud scheduler
gcloud services enable bigquery.googleapis.com              # BigQuery usage


echo
echo "*** INFO 6/12: 60s delay - allow APIs to enable ***"
echo
sleep 60


echo
echo "*** INFO 7/12 Creating buckets ***"
echo
# -p not supplied so links with default project (this was set earlier to the newly created project and can be
# confirmed with `gcloud config get-value project`)
gsutil mb -c standard -l ${REGION} gs://${SOURCES_BUCKET_NAME}  # Where camera sources will be stored
gsutil mb -c standard -l ${REGION} gs://${LABELS_BUCKET_NAME}   # Where labelled imagery will be stored for use & sharing
gsutil mb -c standard -l ${REGION} gs://${DATA_BUCKET_NAME}     # Where downloaded imagery etc will be stored for analysis
gsutil mb -c standard -l ${REGION} gs://${MODELS_BUCKET_NAME}   # Where serialised models will be stored for reuse
gsutil mb -c standard -l ${REGION} gs://${EXPORTS_BUCKET_NAME}  # Where results are hosted for sharing / export


echo
echo "*** INFO 8/12 Adding permissions"
echo

echo "Permitting cloud build to deploy functions"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com \
    --role=roles/cloudfunctions.developer

echo
echo "Permitting deploy build rule to upload function source code"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:service-${PROJECT_NUMBER}@gcf-admin-robot.iam.gserviceaccount.com \
    --role=roles/storage.objectCreator

echo
echo "Permitting deployment of functions from trigger"
gcloud iam service-accounts add-iam-policy-binding ${PROJECT_ID}@appspot.gserviceaccount.com \
    --member=serviceAccount:service-${PROJECT_NUMBER}@gcf-admin-robot.iam.gserviceaccount.com \
    --role=roles/iam.serviceAccountUser

echo
echo "Permitting deployment of functions from trigger"
gcloud iam service-accounts add-iam-policy-binding ${PROJECT_ID}@appspot.gserviceaccount.com \
    --member=serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com \
    --role=roles/iam.serviceAccountUser

echo
echo "Permitting function service account to invoke other functions"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com  \
    --role=roles/cloudfunctions.invoker

echo
echo "Permitting function service account to read from storage"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com  \
    --role=roles/storage.objectViewer

echo
echo "Permitting function service account to write to storage"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com  \
    --role=roles/storage.objectCreator

echo
echo "Permitting function service account to create/read/write/delete to/from BigQuery"
# Need: bigquery.tables.create, bigquery.tables.updateData, bigquery.tables.delete
# Contained in roles/bigquery.dataOwner (see https://cloud.google.com/bigquery/docs/access-control)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com  \
    --role=roles/bigquery.dataOwner

echo
echo "Permitting trigger launched code (unit tests) to create/read/write/delete to/from tables in BigQuery"
# Need: bigquery.tables.create, bigquery.tables.updateData, bigquery.tables.delete
# Contained in roles/bigquery.dataOwner (see https://cloud.google.com/bigquery/docs/access-control)
# Also need bigquery.jobs.create to run search etc as SQL scripts
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com \
    --role=roles/bigquery.dataOwner

echo
echo "Permitting trigger launched code (unit tests) to run SQL jobs in BigQuery"
# Need bigquery.jobs.create to run search etc as SQL scripts
# Contained in roles/bigquery.user (see https://cloud.google.com/bigquery/docs/access-control)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com \
    --role=roles/bigquery.user

echo
echo "Creating bigquery-r service account for use by VM"
gcloud iam service-accounts create bigquery-r \
    --description="R access to BigQuery from VM" \
    --display-name="BigQuery R access for VM"

echo
echo "Adding BigQuery dataset view access to bigquery-r service account"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:bigquery-r@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/bigquery.dataViewer

echo
echo "Adding BigQuery job creation access to bigquery-r service account"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:bigquery-r@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/bigquery.jobUser

echo
echo "Creating bigquery-r service account key for use in VM"
gcloud iam service-accounts keys create vm/bigquery-r-auth-token.json \
  --iam-account bigquery-r@${PROJECT_ID}.iam.gserviceaccount.com

echo
echo "Creating backfill-ne service account for use by VM"
gcloud iam service-accounts create backfill-ne \
    --description="Python access to BigQuery and Bucket Storage from VM" \
    --display-name="BigQuery and Bucket access for VM"

echo
echo "Adding BigQuery dataset delete access to backfill-ne service account"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/bigquery.dataViewer

echo
echo "Adding BigQuery job creation access to backfill-ne service account"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/bigquery.jobUser

echo
echo "Adding BigQuery data editor access to backfill-ne service account"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/bigquery.dataEditor

echo
echo "Adding cloud function invoker access to backfill-ne service account"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/cloudfunctions.invoker

echo
echo "Adding legacy object read access to backfill-ne service account on data bucket"
# to add "storage.buckets.get" access
# Can't add legacy access to project, has to be via bucket. backfill-ne needs access to data bucket,
# VM account itself uploads to export bucket under different access.
gsutil iam ch serviceAccount:backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com:roles/storage.legacyObjectReader \
    gs://data-${PROJECT_ID}

echo
echo "Adding legacy bucket read access to backfill-ne service account on sources bucket"
# to add "storage.buckets.get" access
# Can't add legacy access to project, has to be via bucket. backfill-ne needs access to sources bucket,
# VM account itself uploads to export bucket under different access.
gsutil iam ch serviceAccount:backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com:roles/storage.legacyBucketReader \
    gs://sources-${PROJECT_ID}

echo
echo "Adding legacy bucket blob read access to backfill-ne service account on sources bucket"
# to add "storage.buckets.get" access
# Can't add legacy access to project, has to be via bucket. backfill-ne needs access to sources bucket,
# VM account itself uploads to export bucket under different access.
gsutil iam ch serviceAccount:backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com:roles/storage.legacyObjectReader \
    gs://sources-${PROJECT_ID}

echo
echo "Adding legacy bucket write access to backfill-ne service account on data bucket"
# to add "storage.buckets.get" access
# Can't add legacy access to project, has to be via bucket. backfill-ne needs access to data bucket,
# VM account itself uploads to export bucket under different access.
gsutil iam ch serviceAccount:backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com:roles/storage.legacyBucketWriter \
    gs://data-${PROJECT_ID}

echo
echo "Creating backfill-ne service account key for use in VM"
gcloud iam service-accounts keys create vm/backfill-ne-auth-token.json \
  --iam-account backfill-ne@${PROJECT_ID}.iam.gserviceaccount.com


echo
echo "*** INFO 9/12 Creating Cloud Scheduler and Topic ***"
echo
# Have to create an app engine app in order to use scheduler
gcloud app create --project=${PROJECT_ID} --region=${REGION}
gcloud pubsub topics create scheduled-daily-3am
# schedule is crontab format, see: https://crontab.guru/#0_3_*_*_*
gcloud scheduler jobs create pubsub daily-3am --schedule="0 3 * * *" --topic=scheduled-daily-3am --message-body="Its 3am, time to work"

gcloud pubsub topics create scheduled-every-10mins
# schedule is crontab format, see: https://crontab.guru/#*/10_*_*_*_*
gcloud scheduler jobs create pubsub every-10mins --schedule="*/10 * * * *" --topic=scheduled-every-10mins --message-body="At every 10th minute, time to work"


echo
echo "*** INFO 10/12 Creating BigQuery dataset ***"
echo
# No expiry set, so should not expire
bq --location=${REGION} --project_id=${PROJECT_ID} mk \
    --dataset \
    --description "Detected objects" \
    ${PROJECT_ID}:detected_objects


echo
echo "*** INFO 11/12 Deploying Cloud Functions ***"
echo
./gcp-deploy-functions.sh $1 $2 all


echo
echo
echo "*** INFO 12/12 Uploading default analysis configuration ***"
echo
./gcp-upload-example-analysis.sh $1 $2


echo
echo
echo "********************************************************"
echo "* OPTIONAL: Connecting Google Cloud Build to GitHub"
echo "*"
echo "* NOTE: YOU WILL NEED 'Owner' PRIVILEGES ON GITHUB TO DO THIS"
echo "*"
echo "* 1. Go to Cloud Build Triggers page and link your repo:"
echo "*"
echo "*    https://console.cloud.google.com/cloud-build/triggers"
echo "*"
echo "*    Select 'Manage repository'"
echo "*    Select 'Connect repository'"
echo "*    Select 'GitHub (Cloud Build GitHub App)'"
echo "*    Select 'Install Google Cloud Build' if offered, into your GitHub repo"
echo "*    Select your repository in GCP, and confirm that you understand"
echo "*      GitHub content will be transferred to GCP, and then 'Connect repository'"
echo "*    Select 'Connect repository'"
echo "*"
echo "*    When offered, do not create any triggers and 'skip for now' as the next"
echo "*      script will do the work. Select 'continue' to confirm skipping this step."
echo "*"
echo "*    You will now see the newly connected repository listed as 'inactive',"
echo "*      so you are ready to connect the repository by triggers in the next step."
echo "*"
echo "* 2. run './gcp-github-triggers.sh $1 $2' to setup CI triggers"
echo "********************************************************"
echo
echo
echo "However, you will now need to:"
echo "1. Trigger 'update-sources' Cloud Function to populate 'sources-$1-$2/ingest' bucket folder"
echo "Note that example model configurations and a selection of cameras to analyse have already been uploaded."
