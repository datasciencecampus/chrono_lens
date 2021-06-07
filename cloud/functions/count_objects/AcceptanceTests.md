# Acceptance Tests for `count_objects`

These tests can be run manually to confirm that the code is working as required for:
* `count_objects`

Note that `${PROJECT_ID}` is meant to represent the identifying name of your current Google Compute Platform project,
and is defined as part of `gcp-setup.sh`. `${PROJECT_ROOT}` is the common name of all your project, so the `main` branch
would have `${PROJECT_ID}` of `${PROJECT_ROOT}-main`.

## Correct arguments provided to function, single model

The simplest case is provided, using a single model (i.e. no pre or post-processing).

### Test Steps

1. [Transfer](https://console.cloud.google.com/transfer/cloud) just `TfL-images/20200501/0050` from
`data-${PROJECT_ROOT}-main` to the test project in use's `data` bucket (use the "Transfer files with these prefixes"
option). **DO NOT** delete the items / move them; simply copy. Delete the transfer once complete
as it cannot be reused.
  * Example code with more focused transfer to reduce charges (noting to replace `${PROJECT_ID}` with the appropriate target bucket)
    > `gsutil cp gs://data-${PROJECT_ROOT}-main/TfL-images/20200501/0050/00001.08859.jpg gs://data-${PROJECT_ID}/TfL-images/20200501/0050/`

1. [Transfer](https://console.cloud.google.com/transfer/cloud) the model `NewcastleV0`
from `models-${PROJECT_ROOT}-main` to the test project in use's `models` bucket.
**DO NOT** delete the items / move them; simply copy.
Delete the transfer once complete as it cannot be reused.
  * example code (noting to replace `${PROJECT_ID}` with the appropriate target bucket)
    > `gsutil cp gs://models-${PROJECT_ROOT}-main/NewcastleV0/* gs://models-${PROJECT_ID}/NewcastleV0/`

1. Select the Cloud Function `count_objects` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area, noting to replace the bucket names
 as appropriate and click `Test the function`
```json
{
    "image_bucket_name": "data-${PROJECT_ID}",
    "image_blob_name": "TfL-images/20200501/0050/00001.08859.jpg",
    "model_bucket_name": "models-${PROJECT_ID}",
    "model_blob_name": "NewcastleV0"
}
```

### Expected Outcome

1. `Output` from `Test the function` should be (whitespace will differ - output will be a single line, the example has
been spread out for readability):
```json
{
  "STATUS": "Processed",
  "results": {
    "bus": 0,
    "car": 2,
    "cyclist": 0,
    "motorcyclist": 0,
    "person": 1,
    "truck": 0,
    "van": 3,
    "faulty": false,
    "missing": false
  }
}
```



## Correct arguments provided to function, model with post-process

The simplest case is provided, using a two models: object counter and post-process.

### Test Steps

1. [Transfer](https://console.cloud.google.com/transfer/cloud) just `TfL-images/20200501` from
`data-${PROJECT_ROOT}-main` to the test project in use's `data` bucket (use the "Transfer files with these prefixes"
option). **DO NOT** delete the items / move them; simply copy. Delete the transfer once complete
as it cannot be reused.
  * Example code with more focused transfer to reduce charges (noting to replace `data-${PROJECT_ID}` with the
  appropriate target bucket, as well as imagery you have stored locally):
    > `gsutil cp gs://data-${PROJECT_ROOT}-main/TfL-images/20200501/0040/00001.08859.jpg gs://data-${PROJECT_ID}/TfL-images/20200501/0040/`
    > `gsutil cp gs://data-${PROJECT_ROOT}-main/TfL-images/20200501/0050/00001.08859.jpg gs://data-${PROJECT_ID}/TfL-images/20200501/0050/`
    > `gsutil cp gs://data-${PROJECT_ROOT}-main/TfL-images/20200501/0100/00001.08859.jpg gs://data-${PROJECT_ID}/TfL-images/20200501/0100/`

1. [Transfer](https://console.cloud.google.com/transfer/cloud) the model `NewcastleV0`
from `models-${PROJECT_ROOT}-main` to the test project in use's `models` bucket.
**DO NOT** delete the items / move them; simply copy.
Delete the transfer once complete as it cannot be reused.
  * example code (noting to replace `data-${PROJECT_ID}` with the appropriate target bucket)
    > `gsutil cp gs://models-${PROJECT_ROOT}-main/NewcastleV0/* gs://models-${PROJECT_ID}/NewcastleV0/`

1. [Transfer](https://console.cloud.google.com/transfer/cloud) the model `StaticObjectFilterV0`
from `models-${PROJECT_ROOT}-main` to the test project in use's `models` bucket.
**DO NOT** delete the items / move them; simply copy.
Delete the transfer once complete as it cannot be reused.
  * example code (noting to replace `data-${PROJECT_ID}` with the appropriate target bucket)
    > `gsutil cp gs://models-${PROJECT_ROOT}-main/StaticObjectFilterV0/* gs://models-${PROJECT_ID}/StaticObjectFilterV0/`

1. Select the Cloud Function `count_objects` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area, noting to replace the bucket and blob names
 as appropriate and click `Test the function`
```json
{
    "image_bucket_name": "data-${PROJECT_ID}",
    "image_blob_name": "TfL-images/20200501/0050/00001.08859.jpg",
    "model_bucket_name": "models-${PROJECT_ID}",
    "model_blob_name": "NewcastleV0_StaticObjectFilterV0"
}
```

### Expected Outcome

1. `Output` from `Test the function` should be (whitespace will differ - output will be a single line, the example has
been spread out for readability):
```json
{
  "STATUS": "Processed",
  "results": {
    "bus": 0,
    "car": 0,
    "cyclist": 0,
    "motorcyclist": 0,
    "person": 1,
    "truck": 0,
    "van": 0,
    "faulty": false,
    "missing": false
  }
}
```
