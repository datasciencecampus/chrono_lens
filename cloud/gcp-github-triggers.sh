#!/bin/bash
set -e

if [[ $# -ne 2 ]] ; then
    echo 'You must provide "[project id]" "[branch id]" as two arguments'
    exit 0
fi


PROJECT_ID=$1-$2
BRANCH_PATTERN="^$2$" # branch name we will match against to launch triggers

DEPLOY_CONFIG_FILE="cloud/clouddeploy.yaml"

# Check REPO_NAME is defined
if [[ -z ${REPO_NAME} ]]; then
    echo
    echo "*** ERROR ***"
    echo "REPO_NAME not defined in environment"
    echo
    echo "This is the repository name in GitHub, so for 'github.com/myorg/myrepo', it would be 'myrepo'"
    echo
    echo "With the above example, use: export REPO_NAME=myrepo"
    echo
    echo "Exiting..."
    echo
    exit
fi

# Check REPO_OWNER is defined
if [[ -z ${REPO_OWNER} ]]; then
    echo
    echo "*** ERROR ***"
    echo "REPO_OWNER not defined in environment"
    echo
    echo "This is the repository owner in GitHub, so for 'github.com/myorg/myrepo', it would be 'myorg'"
    echo
    echo "With the above example, use: export REPO_OWNER=myorg"
    echo
    echo "Exiting..."
    echo
    exit
fi


## CI Triggers
# Get all triggers
EXISTING_TRIGGERS=`gcloud alpha builds triggers list --format="value(description)" --project=${PROJECT_ID}`

# Cloud Functions are all defined within the "functions" folder
cd functions

# Find all subfolders with src, as these are the folders with GCP function code and create ci/cd triggers
for repo_dir in **/src/
do
    FUNCTION_NAME=${repo_dir%/*/} # get only base dir name e.g. distribute_json_sources/src/ -> distribute_json_sources
    TRIGGER_NAME=${FUNCTION_NAME}

    # If trigger does not exist, create it
    if [[ "${EXISTING_TRIGGERS}" != *"${TRIGGER_NAME}"* ]]
    then
        echo
        echo "*** INFO Creating build triggers for $FUNCTION_NAME function ***"
        echo

        # Read variables from variables.txt
        RUNTIME=`cat ${FUNCTION_NAME}/variables.txt | tr ' ' '\n' | grep runtime`
        TRIGGER_TYPE=`cat ${FUNCTION_NAME}/variables.txt | tr ' ' '\n' | grep trigger`
        MEMORY=`cat ${FUNCTION_NAME}/variables.txt | tr ' ' '\n' | grep memory`
        TIMEOUT=`cat ${FUNCTION_NAME}/variables.txt | tr ' ' '\n' | grep timeout`

        gcloud beta builds triggers create github \
            --description deploy-${TRIGGER_NAME} \
            --repo-name=${REPO_NAME} \
            --repo-owner=${REPO_OWNER} \
            --branch-pattern=${BRANCH_PATTERN} \
            --build-config=${DEPLOY_CONFIG_FILE} \
            --substitutions=_FUNCTION_NAME=${FUNCTION_NAME},_RUNTIME=${RUNTIME},_TRIGGER_TYPE=${TRIGGER_TYPE},_MEMORY=${MEMORY},_TIMEOUT=${TIMEOUT} \
            --project=${PROJECT_ID}
    else
        echo
        echo "*** INFO Deploy trigger for $FUNCTION_NAME function already exists - skipping deployment ***"
        echo
    fi
done

# Move back out of the functions folder
cd ..

echo
echo "*** INFO Trigger creation completed ***"
echo
