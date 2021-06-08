# Acceptance Tests for `run_model_on_camera`

These tests can be run manually to confirm that the code is working as required. Test confirms the following cloud
functions are working:

* `run_model_on_camera`
* `count_objects`
* `bigquery_write`

Note that `${PROJECT_ID}` is meant to represent the identifying name of your current Google Compute Platform project,
and is defined as part of `gcp-setup.sh`. `${PROJECT_ROOT}` is the common name of all your project, so the `main` branch
would have `${PROJECT_ID}` of `${PROJECT_ROOT}-main`.

## Camera with objects present - simple model

The camera `sd_durhamcouncil09` was selected as items are present in the image; this means
we get a non-zero response from `count_objects` but does not confirm the accuracy
of the model (i.e. there may be additional or missing objects detected).

### Test Steps

1. [Transfer](https://console.cloud.google.com/transfer/cloud) the three folders `Durham-images/20200510/0000/`,
`Durham-images/20200510/0010/` and `Durham-images/20200510/0020/` (or any three temporally contiguous folders for the same
area) from
`data-${PROJECT_ROOT}-main` to the test project in use's `data-${PROJECT_NAME}` bucket (use the "Transfer files with these prefixes"
option). **DO NOT** delete the items / move them; simply copy. Delete the transfer once complete
as it cannot be reused.

1. [Transfer](https://console.cloud.google.com/transfer/cloud) all folders
from `models-${PROJECT_ROOT}-main` to the test project in use's `models-${PROJECT_NAME}` bucket.
**DO NOT** delete the items / move them; simply copy.
Delete the transfer once complete as it cannot be reused.

1. Ensure the BigQuery table `NewcastleV0` is either empty or not present in the
dataset `detected_objects` in the test project (delete as required).

1. Select the Cloud Function `run_model_on_camera` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area and click `Test the function`
(replacing the blob name as appropriate if you have used an alterative image; select the central
image of the sequence of three):
    ```
    {
        "data_blob_name": "Durham-images/20200510/0010/sd_durhamcouncil09.jpg",
        "model_blob_name": "NewcastleV0"
    }
    ```

### Expected Outcome

1. `Output` from `Test the function` should be `{"STATUS": "Processed"}`

1. Table `NewcastleV0` should be created and contain 1 row (noting source and camera_id
will be replaced if you used an alternative selection):

Row | source | camera_id | date | time | bus | car | cyclist | motorcyclist | person | truck | van | faulty | missing
-|-|-|-|-|-|-|-|-|-|-|-|-|-
1 | Durham-images | sd_durhamcouncil09 | 2020-05-10 | 00:10:00 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | false | false


## Camera with objects present - pre process |  model and post process

The camera `00001.08859` was selected as items are present in the image |  along with known false positives; this means
we get a non-zero response from `count_objects` but does not confirm the accuracy
of the model (i.e. there may be additional or missing objects detected).

### Test Steps

1. [Transfer](https://console.cloud.google.com/transfer/cloud) just `TfL-images/20200501` from
`data-${PROJECT_ROOT}-main` to the test project in use's `data-${PROJECT_NAME}` bucket (use the "Transfer files with these prefixes"
option). **DO NOT** delete the items / move them; simply copy. Delete the transfer once complete
as it cannot be reused.
  * NOTE: This data was also used with the `count_objects` acceptance tests so you may already have it in place.
  * Example code with more focused transfer to reduce charges (noting to replace `data-${PROJECT_ROOT}-branch-name` with the appropriate target bucket)
    > `gsutil cp gs://data-${PROJECT_ROOT}-main/TfL-images/20200501/0040/00001.08859.jpg gs://data-${PROJECT_NAME}/TfL-images/20200501/0040/`
    > `gsutil cp gs://data-${PROJECT_ROOT}-main/TfL-images/20200501/0050/00001.08859.jpg gs://data-${PROJECT_NAME}/TfL-images/20200501/0050/`
    > `gsutil cp gs://data-${PROJECT_ROOT}-main/TfL-images/20200501/0100/00001.08859.jpg gs://data-${PROJECT_NAME}/TfL-images/20200501/0100/`

1. [Transfer](https://console.cloud.google.com/transfer/cloud) all folders
from `models-${PROJECT_ROOT}-main` to the test project in use's `models-${PROJECT_NAME}` bucket.
**DO NOT** delete the items / move them; simply copy.
Delete the transfer once complete as it cannot be reused.

1. Ensure the BigQuery table `FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0` is either
empty or not present in the
dataset `detected_objects` in the test project (delete as required).

1. Select the Cloud Function `run_model_on_camera` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area and click `Test the function`
(replacing the blob name as appropriate if you have used an alterative image; select the central
image of the sequence of three):
    ```
    {
        "data_blob_name": "TfL-images/20200501/0050/00001.08859.jpg",
        "model_blob_name": "FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0"
    }
    ```

### Expected Outcome

1. `Output` from `Test the function` should be `{"STATUS": "Processed"}`

1. Table `FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0` should be created and contain 1 row (noting source and camera_id
will be replaced if you used an alternative selection):

Row | source | camera_id | date | time | bus | car | cyclist | motorcyclist | person | truck | van | faulty | missing
-|-|-|-|-|-|-|-|-|-|-|-|-|-
1 | TfL-images | 00001.08859 | 2020-05-01 | 00:50:00 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | false | false

## Camera with image missing - pre process |  model and post process

A bogus image name is used to trigger this behaviour.

### Test Steps

1. [Transfer](https://console.cloud.google.com/transfer/cloud) all folders
from `models-${PROJECT_ROOT}-main` to the test project in use's `models-${PROJECT_NAME}` bucket.
**DO NOT** delete the items / move them; simply copy.
Delete the transfer once complete as it cannot be reused.

1. Ensure the BigQuery table `FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0` is either
empty or not present in the
dataset `detected_objects` in the test project (delete as required).

1. Select the Cloud Function `run_model_on_camera` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area and click `Test the function`
    ```
    {
        "data_blob_name": "Test-images/19991231/2350/missing-image.jpg",
        "model_blob_name": "FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0"
    }
    ```

### Expected Outcome

1. `Output` from `Test the function` should be `{"STATUS": "Processed"}`

1. Table `FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0` should be created and contain 1 row:

Row | source | camera_id | date | time | bus | car | cyclist | motorcyclist | person | truck | van | faulty | missing
-|-|-|-|-|-|-|-|-|-|-|-|-|-
1 | Test-images | missing-image | 1999-12-31 | 23:50:00 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | false | true
