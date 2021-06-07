# Acceptance Tests for `bigquery_write`

These tests can be run manually to confirm that the code is working as required in:
* `bigquery_write`

## Correct arguments provided to function

The simplest case is provided, using an unusual schema to ensure the table is correctly
created.

### Test Steps

1. Ensure the BigQuery table `NewcastleV0` is either empty or not present in the
dataset `detected_objects` in the test project (delete as required).

1. Select the Cloud Function `bigquery_write` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area and click `Test the function`
    ```
    {
        "image_blob_name": "Durham-images/20200510/0000/sd_durhamcouncil01.jpg",
        "model_blob_name": "NewcastleV0",
        "model_results_json": "{\"biscuits\": 3, \"faulty\": false}"
    }
    ```

### Expected Outcome

1. `Output` from `Test the function` should be `{"STATUS": "Processed"}`

1. Table `NewcastleV0` should be created and contain 1 row:


Row	source | camera_id | date | time | biscuits | faulty
-|-|-|-|-|-
1 | Durham-images | sd_durhamcouncil01 | 2020-05-10 | 00:00:00 | 3 | false
