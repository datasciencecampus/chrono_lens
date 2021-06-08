# Acceptance Tests for `download_file`

These tests can be run manually to confirm that the code is working as required. Test confirms the following cloud
functions are working:

* `download_file`

Note that `${PROJECT_ID}` is meant to represent the identifying name of your current Google Compute Platform project,
and is defined as part of `gcp-setup.sh`

## Download single file

This confirms that the environment variables are correctly set as well as the download functionality.
An example image is downloaded from TfL.

### Test Steps

1. Delete the folder `test-downloads` if present in bucket `data-${PROJECT_ID}`

1. Select the Cloud Function `download_file` in the test project and open the `Testing` tab.

1. Enter the following into the `Triggering Event` text area and click `Test the function`
```json
{
    "file_url": "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00002.00865.jpg",
    "destination_blob_name": "test-downloads"
}
```

### Expected Outcome

1. File `00002.00865.jpg` appears in `test-downloads` "folder" in bucket `data-${PROJECT_ID}`,
with a recent timestamp (i.e. when the function was run).

1. Script response should be JSON:
```json
{
    "STATUS": "OK"
}
```

### Clean up

1. Delete the folder `test-downloads` from bucket `data-${PROJECT_ID}`
