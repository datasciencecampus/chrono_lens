# Acceptance Tests for `process_day`

These tests can be run manually to confirm that the code is working as required. Test confirms the following cloud
functions are working:

* `process_day`
* `run_model_on_camera`
* `count_objects`
* `bigquery_write`

Note that `${PROJECT_ID}` is meant to represent the identifying name of your current Google Compute Platform project,
and is defined as part of `gcp-setup.sh`. `${PROJECT_ROOT}` is the common name of all your project, so the `main` branch
would have `${PROJECT_ID}` of `${PROJECT_ROOT}-main`.

## Fully populated day

The camera `sd_durhamcouncil01` may have missing images, so we cannot confirm
if 144 images are indeed being analysed. Until stats are generated on the number of "info"
or "processed" responses from `run_model_on_camera`, we cannot be certain this code works.

### Test Steps

1. [Transfer](https://console.cloud.google.com/transfer/cloud) just `Durham-images/20200510` (or any area and day
with a camera that is fully populated - no missing images) from
`data-${PROJECT_ROOT}-main` to the test project in use's `data` bucket (use the "Transfer files with these prefixes"
option). **DO NOT** delete the items / move them; simply copy. Delete the transfer once complete
as it cannot be reused.

1. [Transfer](https://console.cloud.google.com/transfer/cloud) the model `NewcastleV0`
from `models-${PROJECT_ROOT}-main` to the test project in use's `models` bucket.
**DO NOT** delete the items / move them; simply copy.
Delete the transfer once complete as it cannot be reused.

1. Ensure the BigQuery table `NewcastleV0` is either empty or not present in the
dataset `detected_objects` in the test project (delete as required).

1. Select the Cloud Function `process_day` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area and click `Test the function`
(replacing the date and image name as appropriate, to match the day and camera that
are fully populated - no missing images):
    ```
    {
        "date_to_process": "20200510",
        "image_name": "sd_durhamcouncil01.jpg",
        "data_root": "Durham-images",
        "model_blob_name": "NewcastleV0"
    }
    ```

### Expected Outcome

1. `Output` from `Test the function` may time out, as it can take >60s; the function
itself has a 120s timeout, but the test harness may fail before then.

1. Table `NewcastleV0` should be created and contain 144 (24*6) rows
