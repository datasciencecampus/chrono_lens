#!/bin/bash
set -e

echo
echo "*** WARNING ***"
echo
echo "*** Using Debian debian-10-buster-v20200910 which is superceded by newer versions."
echo "*** Staying with old version due to complexity of configuring rjdemetra and related dependencies."
echo
echo "*** END WARNING ***"
echo
echo


if [[ $# -ne 2 ]] ; then
    echo 'You must provide "[project id]" "[branch id]" as two arguments'
    exit 0
fi

# script variables
export PROJECT_ID=$1-$2
ZONE="europe-west2-a"  # europe-west2-a has T4 GPUs if needs be
VM_NAME="impute-seats"

PROJECT_NUMBER=`gcloud projects list --filter=${PROJECT_ID} --format="value(PROJECT_NUMBER)"`
VM_USERNAME=`gcloud auth list --filter="status:ACTIVE" --format="value(ACCOUNT)" | cut -d@ -f1 | tr "." "_"`


echo
echo "*** INFO 1/6 Creating VM ***"
echo
# uses default service account:     --service-account=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
# uses startup script https://cloud.google.com/compute/docs/instances/startup-scripts/linux#passing-local
# No external IP address (use "enable-network.sh" and "disable-network.sh" to enable/disable external network)

gcloud beta compute --project=${PROJECT_ID} instances \
    create ${VM_NAME} \
    --zone=${ZONE} \
    --machine-type=custom-2-46080-ext \
    --subnet=default \
    --no-address \
    --no-restart-on-failure \
    --maintenance-policy=TERMINATE \
    --service-account=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/bigquery,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/trace.append,https://www.googleapis.com/auth/devstorage.read_write \
    --image=debian-10-buster-v20200910 \
    --image-project=debian-cloud \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-standard \
    --boot-disk-device-name=${VM_NAME} \
    --reservation-affinity=any \
    --metadata-from-file startup-script=vm/root-startup.sh

echo
echo "*** INFO 2/6 Waiting 60s for VM to start up"
echo
sleep 60

echo
echo "*** INFO 3/6 Enabling external IP"
echo
gcloud compute --project=${PROJECT_ID} instances add-access-config ${VM_NAME} --zone ${ZONE}

echo
echo "*** INFO 4/6 Copying files to VM"
echo
gcloud compute --project=${PROJECT_ID} scp vm/install.sh ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE}
gcloud compute --project=${PROJECT_ID} scp vm/runner-startup.sh ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE}
gcloud compute --project=${PROJECT_ID} scp vm/bigquery-r-auth-token.json ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE}
gcloud compute --project=${PROJECT_ID} scp vm/backfill-ne-auth-token.json ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE}
gcloud compute --project=${PROJECT_ID} scp vm/*.R ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE}

gcloud compute --project=${PROJECT_ID} scp ../requirements-gcloud.txt ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE}
gcloud compute --project=${PROJECT_ID} scp ../chrono_lens ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE} --recurse
gcloud compute --project=${PROJECT_ID} scp ../scripts/gcloud/*.py ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE}
gcloud compute --project=${PROJECT_ID} scp ../scripts/gcloud/NEtraveldata_cctv.json ${VM_USERNAME}@${VM_NAME}:. --zone=${ZONE}

echo
echo "*** INFO 5/6 Installing software on VM"
echo
gcloud compute --project=${PROJECT_ID} ssh ${VM_USERNAME}@${VM_NAME} --zone=${ZONE} --command="./install.sh ${PROJECT_ID}" | tee install.log

echo
echo "*** INFO 6/6 Shutting down VM"
echo
gcloud compute --project=${PROJECT_ID} instances stop ${VM_NAME} --zone ${ZONE}
