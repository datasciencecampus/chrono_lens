# Acceptance Tests for `start_vm`

These tests can be run manually to confirm that the code is working as required. Test confirms the following cloud
functions are working:

* `start_vm`

## Starting the VM directly from the Cloud Function

This confirms that the environment variables are correctly set as well as the VM being created.

### Test Steps

1. Make sure the VM `impute-seats` is installed and powered off

1. Select the Cloud Function `start_vm` in the test project and open the `Testing` tab.

1. Leave the `Triggering Event` text area unchanged (it is just `{ }`) and click `Test the function`

### Expected Outcome

1. VM `impute-seats` has now powered on

### Clean up

1. Power off the VM `impute-seats`


## Starting the VM from the scheduler

This confirms that the scheduler is triggering the Cloud Function

### Test Steps

1. Make sure the VM `impute-seats` is installed and powered off

1. Select the `Cloud Scheduler` in Google Cloud Platform Console

1. Click on the `RUN NOW` button against the `monday-3am` job

### Expected Outcome

1. VM `impute-seats` has now powered on

### Clean up

1. Power off the VM `impute-seats`
