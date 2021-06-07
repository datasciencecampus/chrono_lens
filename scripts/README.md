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
