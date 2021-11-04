#!/bin/bash

if [[ $# -ne 1 ]] ; then
    echo 'You must provide a log filename as the only argument.'
    echo 'Recommend to use todays date and time, such as:'
    echo 'runner-startup.sh logs/manual-run-2020117-1506.log'
    exit 0
fi

PROJECT_ID="PROJECT_ID_PLACEHOLDER"

# Reminder that VM startup messages will be shown in /var/log/daemon.log (for Debian)
#
# Startup triggered logs also available via "sudo journalctl -u google-startup-scripts.service"
# (unsure if manually triggered script execution will also appear here)
#
# Startup script can be triggered manually via "sudo google_metadata_script_runner startup"


# Note that script will be run via "sudo" so may not be starting in the home folder...
cd ~runner

export PYTHONPATH=chrono_lens

echo "================================================================================" >> $1
echo >> $1
echo "Getting list of cameras to process..." >> $1
echo >> $1
python3 download_analysis_camera_list.py -ctaf=cameras-to-analyse.json -mcf=model-in-use.txt -jpk=backfill-ne-auth-token.json -gp=${PROJECT_ID} >> $1 2>&1
echo >> $1

MODEL_IN_USE=`cat model-in-use.txt`

echo "================================================================================" >> $1
echo >> $1
echo "Backfilling NE Travel Data..." >> $1
echo >> $1
# Run backfill script, piping stdout and stderr to log...
python3 backfill_NEtraveldata.py -jpk=backfill-ne-auth-token.json -netsj=NEtraveldata_cctv.json -gp=${PROJECT_ID} -mn=${MODEL_IN_USE} > $1 2>&1
echo >> $1

echo "================================================================================" >> $1
echo >> $1
echo "Processing cameras missing in BigQuery table..." >> $1
echo >> $1
python3 batch_process_images.py -cj=cameras-to-analyse.json -jpk=backfill-ne-auth-token.json -gp=${PROJECT_ID} -mn=${MODEL_IN_USE} >> $1 2>&1

echo >> $1
echo "================================================================================" >> $1
echo >> $1
echo "Removing images older than 28 days..." >> $1
echo >> $1
python3 remove_old_images.py -mnod=28 -jpk backfill-ne-auth-token.json -gp ${PROJECT_ID} >> $1 2>&1

echo >> $1
echo "================================================================================" >> $1
echo >> $1

DAYOFWEEK=$(date +"%a")
if [[ "${DAYOFWEEK}" == "Mon" ]]
then

echo >> $1
echo "Its Monday - time to generate faster indicators..." >> $1
echo >> $1

# Pull last stashed copy back from bucket
imputed_dataset_filename="cache/imputed_dataset.Rda"
gsutil cp gs://exports-${PROJECT_ID}/FasterIndicators/cache/imputed_dataset_latest.Rda ${imputed_dataset_filename} >> $1 2>&1

# Run R script
Rscript data_impute_and_seats_run.R >> $1 2>&1

# Copy results to bucket
today=$(date +"%Y%m%d")

gsutil cp ${imputed_dataset_filename} gs://exports-${PROJECT_ID}/FasterIndicators/cache/imputed_dataset_${today}.Rda >> $1 2>&1
gsutil cp ${imputed_dataset_filename} gs://exports-${PROJECT_ID}/FasterIndicators/cache/imputed_dataset_latest.Rda >> $1 2>&1

gsutil cp -r outputs/*${today}*.* >> $1 2>&1

fi

next_monday=`date -dmonday +%Y%m%d`
gsutil -h "Content-Type:text/plain" cp $1 gs://exports-${PROJECT_ID}/FasterIndicators/${next_monday}/
