# Acceptance Tests for `update_sources`

These tests can be run manually to confirm that the code is working as required. Test confirms the following cloud
functions are working:

* `update_sources`

Note that `${PROJECT_ID}` is meant to represent the identifying name of your current Google Compute Platform project,
and is defined as part of `gcp-setup.sh`

## Trigger the function

This checks the environment variables are correctly set as well as the download functionality.

### Test Steps

1. Empty the `sources-${PROJECT_ID}` bucket (to ensure files have arrived and aren't old files).
1. Trigger the function via the `Testing` tab under cloud functions
(`Triggering event` can be left unmodified from the default).

### Expected Outcome

1. Examine the `sources-${PROJECT_ID}` bucket; the following files should appear, with a modification
recent timestamp (i.e. when the function was triggered):
  * TfL-images.json

## Topic triggering the function

This confirms that the function has been connected to the topic and is launched correctly.

### Test Steps

1. Empty the `sources-${PROJECT_ID}` bucket (to ensure files have arrived and aren't old files).
1. Trigger the `Cloud Scheduler` topic `daily-8am`.

### Expected Outcome

1. Examine the `sources-${PROJECT_ID}` bucket; the following files should appear, with a modification
recent timestamp (i.e. when the function was triggered):
  * TfL-images.json
