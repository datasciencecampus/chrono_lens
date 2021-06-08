#!/bin/bash
set -e

if [[ $# -ne 3 ]] ; then
    echo 'You must provide "[project id]" "[branch id]" "[function name]" as three arguments'
    echo 'NOTE: "all" for "[function name]" will trigger all functions rather than just the named function'
    exit 0
fi


PROJECT_ID=$1-$2
BRANCH_PATTERN="^$2$" # branch name we will match against to launch triggers

DEPLOY_CONFIG_FILE="cloud/clouddeploy.yaml"


# Cloud Functions are all defined within the "functions" folder
cd functions

# Find all subfolders with src, as these are the folders with GCP function code and create ci/cd triggers
for repo_dir in **/src/
do
    FUNCTION_NAME=${repo_dir%/*/} # get only base dir name e.g. distribute_json_sources/src/ -> distribute_json_sources

    # Deploy the function if its name matches the 3rd argument (cloud function to deploy) or if "all" was specified
    if [[ "${3}" == "${FUNCTION_NAME}" ]] || [[ "${3}" == "all" ]]
    then
        echo
        echo "*** INFO Deploying cloud function $FUNCTION_NAME ***"
        echo

        # Read variables from variables.txt
        RUNTIME=`cat ${FUNCTION_NAME}/variables.txt | tr ' ' '\n' | grep runtime`
        TRIGGER_TYPE=`cat ${FUNCTION_NAME}/variables.txt | tr ' ' '\n' | grep trigger`
        MEMORY=`cat ${FUNCTION_NAME}/variables.txt | tr ' ' '\n' | grep memory`
        TIMEOUT=`cat ${FUNCTION_NAME}/variables.txt | tr ' ' '\n' | grep timeout`

        # Copy in dsc_lib so it appears as local to the src directory; we'll remove it after installing
        cp -r ../dsc_lib ${FUNCTION_NAME}/src/

        # --quiet used to stop query "Allow unauthenticated invocations of new function [func name]? (y/N)?
        # so instead will use default response of "N" (cannot specify "do not permit", only "do permit" with
        # --allow-unauthenticated which is the opposite of what we require)
        gcloud functions deploy ${FUNCTION_NAME} \
            --${MEMORY} \
            --${RUNTIME} \
            --${TIMEOUT} \
            --${TRIGGER_TYPE} \
            --source=${FUNCTION_NAME}/src/ \
            --project=${PROJECT_ID} \
            --region=europe-west2 \
            --set-env-vars=SOURCES_BUCKET_NAME=sources-${PROJECT_ID} \
            --set-env-vars=DATA_BUCKET_NAME=data-${PROJECT_ID} \
            --set-env-vars=MODELS_BUCKET_NAME=models-${PROJECT_ID} \
            --set-env-vars=VM_INSTANCE_NAME=impute-seats \
            --set-env-vars=VM_ZONE_NAME=europe-west2-a \
            --set-env-vars=GCP_PROJECT=${PROJECT_ID} \
            --set-env-vars=FUNCTION_REGION=europe-west2 \
            --quiet

        # Remove temporary dsc_lib copy after installation
        rm -rf ${FUNCTION_NAME}/src/dsc_lib
    else
        echo
        echo "*** INFO ...skipping deploy of cloud function ${FUNCTION_NAME}... ***"
        echo
    fi
done

# Move back out of the functions folder
cd ..

echo
echo "*** INFO Cloud Function deployment completed ***"
echo
