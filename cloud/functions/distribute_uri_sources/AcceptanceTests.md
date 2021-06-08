# Acceptance Tests for `distribute_uri_sources`

These tests can be run manually to confirm that the code is working as required. Test confirms the following cloud
functions are working:

* `distribute_uri_sources`
* `download_file`

Note that `${PROJECT_ID}` is meant to represent the identifying name of your current Google Compute Platform project,
and is defined as part of `gcp-setup.sh`

## Download single JSON, multiple JPEGs

This confirms that the environment variables are correctly set as well as the download functionality.
An example image is downloaded from TfL.

### Test Steps

1. Delete the folder `blob-test` if present in bucket `data-${PROJECT_ID}`

1. Create a file called `blob-test.json` in bucket `sources-${PROJECT_ID}`, that contains:
```json
[
    "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00002.00865.jpg",
    "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00001.02151.jpg",
    "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00001.07450.jpg"
]
```
(example `blob-test.json` is in the tests folder for re-use).

1. Select the Cloud Function `distribute_uri_sources` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area and click `Test the function`
```json
{
    "json_blob_name": "blob-test.json",
    "date_time_folder": "20200101/0123"
}
```

### Expected Outcome

1. Files `00001.02151.jpg`, `00001.07450.jpg` and `00002.00865.jpg` appear in `blob-test/20200101/0123` "folder" in
bucket `data-${PROJECT_ID}`, with recent timestamps (i.e. when the function was run). These filenames
are matching the ones in the `blob-test.json` file provided.

1. JSON response from function of:
```json
{
  "STATUS": "OK",
  "OK": 3
}
```

This indicates that 3 files were successfully downloaded.

### Clean up

1. Delete the blob `blob-test.json` from bucket `sources-${PROJECT_ID}`

1. Delete the folder `blob-test` from bucket `data-${PROJECT_ID}`
