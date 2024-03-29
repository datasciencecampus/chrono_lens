# Acceptance Tests for `distribute_json_sources`

These tests can be run manually to confirm that the code is working as required. Test confirms the following cloud
functions are working:

* `distribute_json_sources`
* `distribute_uri_sources`
* `download_file`

Note that this is a full system test so will download all images, and to verify this will need an empty bucket
(i.e. to simplify testing), so needs a scratch project ideally. Tests can also be carried out non-destructively,
but are more complex.

Note that `${PROJECT_ID}` is meant to represent the identifying name of your current Google Compute Platform project,
and is defined as part of `gcp-setup.sh`

## Direct trigger - destructive test

This confirms that the environment variables are correctly set as well as the download functionality scales
correctly, and does not suffer from timeouts.

### Test Steps

1. Empty the bucket `data-${PROJECT_ID}` to ensure any downloaded files are easily identified.

1. Run the `update-sources` cloud function to ensure the `sources-${PROJECT_ID}` is up-to-date.

1. Select the Cloud Function `distribute_json_sources` in the test project and open the `Testing` tab.

1. Leave the `Triggering Event` text area with its default text and click `Test the function`.

### Expected Outcome

**NOTE** if the function takes longer than 240s, the test may terminate - the function itself
is registered to have a 240s timeout, and takes ~35.

1. "folder" named `TfL-images` in bucket `data-${PROJECT_ID}`.

1. Attempt to delete the folder to reveal the number of downloaded images:
  * `TfL-images`: 911 files

3. Examine the folder; they should contain a sub-folder of today's date, followed by a sub-folder of the
time the script was run, which contains the actual images/videos. All folders will contain the same date and time.

4. Text response from function of:
```
OK
```

This indicates that 3 files were successfully downloaded.

5. Examine the log output of `distribute_json_sources`:

```
Function execution started
Searching bucket sources-${PROJECT_ID} for JSON files...
=> Reading URLs from TfL-images.json
...search in bucket sources-${PROJECT_ID} for JSON files complete.
Processing: TfL-images.json with {'date_time_folder': '20200603/1258'}
Completed attempt#0: "TfL-images.json""; response="{'STATUS': 'OK', 'OK': 911}"
Function execution took 49861 ms, finished with status: 'ok'
```

All functions should complete without any failures listed in the responses (i.e. all responses are `OK`,
no `Errored` or other responses).

### Clean up

1. You may wish to delete the folders from bucket `data-${PROJECT_ID}` unless they are of further use.


## PubSub scheduled trigger - destructive test

This confirms that the downloads are correctly connected to the Scheduler topic and related PubSub topic,
environment variables are correctly set as well as the download functionality scales
correctly, and does not suffer from timeouts.

### Test Steps

1. Empty the bucket `data-${PROJECT_ID}` to ensure any downloaded files are easily identified.

1. Run the `update-sources` cloud function to ensure the `sources-${PROJECT_ID}` is up-to-date.

1. Trigger the `Cloud Scheduler` topic `every-10mins`.

### Expected Outcome

1. "folder" named `TfL-images` in bucket `data-${PROJECT_ID}`.

1. Attempt to delete the folder to reveal the number of downloaded images:
  * `TfL-images`: 911 files

3. Examine the folders; they should contain a sub-folder of today's date, followed by a sub-folder of the
time the script was run, which contains the actual images/videos. All folders will contain the same date and time.

4. Examine the log output of `distribute_json_sources` (noting `${PROJECT_ID}` should be
replaced with your local project id):

```
Function execution started
Searching bucket sources-${PROJECT_ID} for JSON files...
=> Reading URLs from TfL-images.json
...search in bucket sources-${PROJECT_ID} for JSON files complete.
Processing: TfL-images.json with {'date_time_folder': '20200603/1258'}
Completed attempt#0: "TfL-images.json""; response="{'STATUS': 'OK', 'OK': 911}"
Function execution took 49861 ms, finished with status: 'ok'
```

All functions should complete without any failures listed in the responses (i.e. all responses are `OK`,
no `Errored` or other responses).

### Clean up

1. You may wish to delete the folders from bucket `data-${PROJECT_ID}` unless they are of further use.


## Non-destructive test variants

You can run the trigger-based or direct function based tests without first emptying the bucket,
but you will have to navigate to each sub-folder that represents the time the test was triggered,
to discover how many images are present. Manual clean-up (removal of these test downloads) will also
be more work (however, just ask to delete each unique time folder generated by the test to
determine the number of images downloaded, then confirm the deletion).

It is recommended to trigger the function safely away from 10 minute multiples past the hour
(so avoid :00, :10, :20 etc.) so you can identify the files generated by your test rather than the
scheduled 10 minute trigger.
