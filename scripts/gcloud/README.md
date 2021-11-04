# Script pre-requisites

## Python libraries

You will need to have installed the required libraries in `requirements.txt`, preferably in a new
(isolated) virtual environment (such as Anaconda, venv, virtualenv). Install the libraries with:

`pip install -r requirements.txt`

## Python path

The project and shared libraries must be on the current Python path; when using the code, start a command shell
at the project root and use this as the Python source path by entering (in Unix):
```bash
export PYTHONPATH=`pwd`:`pwd`/cloud
```

Alternatively, using Windows, you would require `set PYTHONPATH=<your current folder>:<your current folder>/cloud` where
you manually enter the current folder path.

**NOTE** eventually this requirement would be replaced when an installation script
is created.

## GCP JSON credentials

You will need to have a JSON format private key for a service account; we recommend you create
a service account with minimal privileges:
1. Create a service account via the GCP Console [service accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts)
1. Grant the account the roles: `roles/bigquery.dataViewer`, `roles/bigquery.jobUser`, `roles/bigquery.dataEditor` and
`roles/cloudfunctions.invoker`
1. Add the service account to the `data-${PROJECT_ID}` bucket permissions, namely `storage.legacyObjectReader` and
`storage.legacyBucketWriter`
1. Add the service account to the `sources-${PROJECT_ID}` bucket permissions, namely `storage/legacyBucketReader` and
`storage/legacyObjectReader`
1. Create a key and download it in JSON format
1. Put the key file in a safe (private) folder and note its location; feel free to rename it, e.g. `batch-service-key.json`


# Using `backfill_NEtraveldata.py`

This script explicitly downloads any missing imagery from NE Travel Data into the `data` bucket and clears any "missing"
or "faulty" rows in BigQuery (for the given date, for NE Travel Data only). Use `batch_process_images.py`
to re-processes those missing rows with the model to refresh the BigQuery table (and hence synchronise it with the
latest imagery - hopefully "Missing" images have now arrived, and any marked as "Faulty" due to repeated images
may now be fixed).

The system pulls images every 10 minutes, but the NE Travel Data hosted c/o Newcastle University's
[Urban Observatory](https://urbanobservatory.ac.uk/) may arrive several hours later in batches. Hence this script
(and a variation used in the GCP virtual machine) back-fills any late arriving data; once data has been filled,
then deletes any rows from NETravelData marked as `missing` or `faulty`, and then re-process the affected
date range using the cloud function `process_day`.

The script takes a JSON file as reported by Newcastle's server which lists available cameras; these cameras are then
requested and uploaded to the Google storage bucket for later processing; BiqQuery table entries
for this date range will also have any NE Travel Data processed image records removed if they
are flagged as `Faulty` or `Missing` (so `batch_process_images.py` will then re-process the gaps).

**Note** that a service account is needed to execute this script, with the following permissions:
* `roles/bigquery.dataViewer`
* `roles/bigquery.jobUser`
* `roles/bigquery.dataEditor`
* `roles/cloudfunctions.invoker`
* `storage.legacyObjectReader` and `storage.legacyBucketWriter` permissions on the `data` bucket
* `storage/legacyBucketReader` and `storage/legacyObjectReader` on the `sources` bucket

See the [Cloud README.md](cloud/README.md) for further information;
the Cloud setup scripts will create a service account with these permissions (`backfill-ne@...`).

Command line options are:
* `--JSON-private-key` JSON key for GCP service account with appropriate permissions (see above)
* `--ne-travel-sources-json` JSON file containing NE Travel Data sources as downloaded from Urban Observatory
(example provided in `NEtraveldata_cctv.json`)
* `--start-date` starting date for when images will be processed
* `--end-date` end date for when images will be processed
* `--model-name` name of the machine learning model with optional pre- and post-processing filters (available
models are listed with `--help`)
* `--gcp-region` Google Compute Platform region where your project is hosted (e.g. `europe-west2`)
* `--gcp-project` name of your Google Compute Platform project
* `--help` detailed help on each option, with default arguments listed

## Launching the script

Now you can launch the script, by defining a start date and end date for images to be processed
between (inclusive), and a list of CCTV cameras to refresh from NE Travel Data. This is specific to the
Newcastle University service provider, with a copy to use stored in `scripts/NEtraveldata_cctv.json`. This is used
by the script to call Newcastle University's server and discover available camera views. Finally, the model to process the
data has to be named, such as `FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0`, as this names
 the BigQuery table to be flushed.

So for example, to refresh all selected cameras between 1st and 2nd of June 2020, run:
```bash
cd scripts
python3 backfill_NEtraveldata.py --JSON-private-key="batch-service-key.json" --start-date="20200601" \
  --end-date="20200602" --ne-travel-sources-json="NEtraveldata_cctv.json" \
  --cameras-to-analyse-json="analyse_NETravelData-images.json" \
  --gcp-project=${PROJECT_ID} --model-name="FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0"
```

By default, the script assumes that the project hosting the cloud functions is `${PROJECT_ID}` (as set from running
`cloud/gcp-setup.sh`, but can be
changed / overridden with the `--gcp-project` argument), and that the project is hosted in GCP region `europe-west2`
(can be set with the `--gcp-region` argument).

## Script internals

The python script will:
1. Search the Newcastle University server for any camera images between the given dates, and download any images not
   already present in the `data-${PROJECT_ID}` bucket.
1. Remove any BigQuery results for NE Travel Data between the given dates flagged as "faulty" or "missing"


# Using `download_analysis_camera_list.py`

This script downloads the list of camera IDs to be analysed, from the GCP project.


This script downloads the list of camera IDs to be analysed, from the GCP project, and the list
can then be used by `batch_process_images.py`. It accesses the bucket `sources-${PROJECT_ID}`,
looking in the `analyse` folder for JSON files listing cameras to be processed.

Command line options are:
* `--cameras-to-analyse-file` filename of a JSON file to write camera IDs and image sources into
* `--model-config-file` filename of a test file where to store the name of the model in use to analyse the images
* `--JSON-private-key` JSON key from GCP with permission to invoke cloud functions in the named GCP project
named cameras to process
* `--gcp-region` Google Compute Platform region where your project is hosted (e.g. `europe-west2`)
* `--gcp-project` name of your Google Compute Platform project
* `--help` detailed help on each option, with default arguments listed

The service account represented by the JSON file will need:
* `storage/legacyBucketReader` and `storage/legacyObjectReader` on the `sources` bucket

See the [Cloud README.md](cloud/README.md)  for further information;
the Cloud setup scripts will create a service account with these permissions (`backfill-ne@...`).

## Launching the script

Firstly, you will need to have a JSON format private key for a service account; we recommend you create
a service account with minimal privileges (see above section "Using `batch_process_images.py`").

Now you can launch the script, by defining the JSON private key path, the GCP region and project, and finally
the filename of the file where the camera IDs are to be stored.

So for example, to process all selected cameras between 1st and 2nd of June 2020, run:
```bash
cd scripts
python3 batch_process_images.py --JSON-private-key="batch-service-key.json" --cameras-to-analyse-file="cameralist.json"
```

By default, the script assumes that the project hosting the cloud functions is `${PROJECT_ID}` (as set from running
`cloud/gcp-setup.sh`, but can be
changed / overridden with the `--gcp-project` argument), and that the project is hosted in GCP region `europe-west2`
(can be set with the `--gcp-region` argument).

When running, the JSON files found in the bucket will be named as they are downloaded.

The final output file is ready to be used with `batch_process_images.py` (see next section). The file
consists of a dictionary that maps camera provider names to the list of camera IDs found
under that provider. Hence `NETravelData-images` matches the folder `NETravelData-images` in the
data bucket for the selected project (in effect `data-${PROJECT_ID}`).

## Issues

* Be careful when setting declaring `--gcp-project` and `--gcp-region`, also ensure the service account is created on the
same project and region as used by the script; otherwise you will see access permission failures reported by the script.


# Using `batch_process_images.py`

This script enables a set of images to be processed over a set date range.

This script is useful in running the time series on pre-existing data - for example, if you have started image
acquisition before readying the model, or if you wish to re-process imagery with an alternative model or
alternative settings.

The script calls the cloud function `process_day` which runs a named model on a particular date for a given
list of cameras. `process_day` in turn calls `run_model_on_image` in the same way the scheduled every 10 minute
call is processed, with results placed in BigQuery.

Command line options are:
* `--JSON-private-key` JSON key from GCP with permission to invoke cloud functions in the named GCP project
* `--cameras-json` filename of a JSON file containing a dictionary of image suppliers, each key linked to a list of
named cameras to process
* `--start-date` starting date for when images will be processed
* `--end-date` end date for when images will be processed
* `--model-name` name of the machine learning model with optional pre- and post-processing filters (available
models are listed with `--help`)
* `--gcp-region` Google Compute Platform region where your project is hosted (e.g. `europe-west2`)
* `--gcp-project` name of your Google Compute Platform project
* `--help` detailed help on each option, with default arguments listed

The service account represented by the JSON file will need:
* `roles/cloudfunctions.invoker`

See the [Cloud README.md](cloud/README.md) for further information;
the Cloud setup scripts will create a service account with these permissions (`backfill-ne@...`).


## Launching the script

Launch the script by defining a start date and end date for images to be processed
between (inclusive), and use an appropriate source file containing camera IDs (as generated by
 `download_analysis_camera_list.py`). The file
consists of a dictionary that maps camera provider names to the list of camera IDs found
under that provider. Hence `Durham-images` matches the folder `Durham-images` in the
data bucket for the selected project (in effect `data-${PROJECT_ID}` noting that).

So for example, to process all selected cameras between 1st and 2nd of June 2020, run:
```bash
cd scripts
python3 batch_process_images.py --JSON-private-key="batch-service-key.json" --start-date="20200601" \
  --end-date="20200602" --images-json="all-analyse-cameras.json" \
  --gcp-project=
```

By default, the script assumes that the project hosting the cloud functions is `${PROJECT_ID}` (as set from running
`cloud/gcp-setup.sh`, but can be
changed / overridden with the `--gcp-project` argument), and that the project is hosted in GCP region `europe-west2`
(can be set with the `--gcp-region` argument).

Progress bars will be presented showing the dates being iterated over, along with which image
supplier and camera. This will take approximately 30s per camera image, as it is processing
144 images per selected day (images are captured every 10 minutes, so 6 per hour; hence 24*6=144 images).

Analysis is recorded in the **BigQuery** database, named after the current
model. This will be a data set called `detected_objects` within the project, with a table per model
processed. At present the single model used is called `NewcastleV0`, supplied courtesy of
Newcastle University's Urban Observatory from their [GitHub repository](https://github.com/TomKomar/uo-object_counting).

Additional models are available for pre and post processing, run `python batch_process_images.py -h` to discover more.

## Issues

* Be careful when setting declaring `--gcp-project` and `--gcp-region`, also ensure the service account is created on the
same project and region as used by the script; otherwise you will see access permission failures reported by the script.


# Using `remove_old_images.py`

This script removes images older than a specified number of days from the `data` bucket.

Once images are analysed, they do not need to be retained (unless you are modifying the model or filtering)
and can be removed. In case of system issues, the images can be retained on a rolling deletion basis - this
script is used in the optional virtual machine (see [`cloud/README.md`](cloud/README.md)) to remove images
older than 28 days (4 weeks).

Command line options are:
* `--maximum-number-of-days` maximum number of days an image is retained before it is deleted (date folder is
used to determine when it was created - so if an image was downloaded today but the folder indicated 60 days ago,
running the script with less than 60 days specified will remove the image)
* `--JSON-private-key` JSON key from GCP with permission to invoke cloud functions in the named GCP project
* `--gcp-region` Google Compute Platform region where your project is hosted (e.g. `europe-west2`)
* `--gcp-project` name of your Google Compute Platform project
* `--help` detailed help on each option, with default arguments listed

The service account represented by the JSON file will need:
* `storage.legacyObjectReader` and `storage.legacyBucketWriter` permissions on the `data` bucket
* `storage/legacyBucketReader` and `storage/legacyObjectReader` on the `sources` bucket

See the [Cloud README.md](cloud/README.md) for further information;
the Cloud setup scripts will create a service account with these permissions (`backfill-ne@...`).

## Launching the script

Firstly, you will need to have a JSON format private key for a service account; we recommend you create
a service account with minimal privileges (see above section "Using `batch_process_images.py`").

Now you can launch the script, by defining the JSON private key path, the GCP region and project, and finally
the "maximum number of days" before images are to be deleted. Note that "maximum number of days" must be 1 or more,
as we cannot delete today's images - they are still arriving via the "distribute_json_sources" cloud function
triggered by the Cloud Scheduler.

So for example, to remove all images older than 28 days, run:
```bash
cd scripts
python3 remove_old_images.py --JSON-private-key="batch-service-key.json" --maximum-number-of-days=28
```

By default, the script assumes that the project hosting the cloud functions is `${PROJECT_ID}` (as set from running
`cloud/gcp-setup.sh`, but can be
changed / overridden with the `--gcp-project` argument), and that the project is hosted in GCP region `europe-west2`
(can be set with the `--gcp-region` argument).

When running, the `sources-${PROJECT_ID}` bucket folder `ingest` is searched for JSON files; these files represent the names of
the image sources to be searched, with `NETravelData` assumed automatically as it uses a dedicated
cloud function rather than a JSON file.

The named camera sources are then used as folders to search in the `data-${PROJECT_ID}` bucket; any date folders
within these folders with a date older than the specified number of days is then assumed to be too old
and hence deleted.

## Issues

* Be careful when setting declaring `--gcp-project` and `--gcp-region`, also ensure the service account is created on the
same project and region as used by the script; otherwise you will see access permission failures reported by the script.
