# Script pre-requisites

## Python libraries

You will need to have installed the required libraries in `requirements-localhost.txt`, preferably in a new
(isolated) virtual environment (such as Anaconda, venv, virtualenv). Install the libraries with:

`pip install -r requirements-localhost.txt`

## Python path

The project and shared libraries must be on the current Python path; when using the code, start a command shell
at the project root and use this as the Python source path by entering (in Unix):
```bash
export PYTHONPATH=`pwd`
```

Alternatively, using Windows, you would require `set PYTHONPATH=<your current folder>` where
you manually enter the current folder path.

**NOTE** eventually this requirement would be replaced when an installation script
is created.


# Limitations

At present, the NE Travel Data is not supported with a stand-alone machine (just the GCP implementation).
Also, database integration is not supported (CSV files are output per day which can then be ingested
into a database as required). Finally, time series analysis in R is not supported either (this code is
still linked to GCP BigQuery, refer to `cloud/vm` for R source code).


# Using `batch_process_images.py`

This script enables a set of images to be processed over a set date range.

This script is useful in running the time series on pre-existing data - for example, if you have started image
acquisition before readying the model, or if you wish to re-process imagery with an alternative model or
alternative settings.

This script works the same as `scripts/local/process_scheduled.py`, only processing a date range rather
than a single sample.

Command line options are:
* `--start-date` starting date for when images will be processed
* `--end-date` end date for when images will be processed
* `--config-folder` folder where configuration data is stored (default: `localhost/config`)
* `--download-folder` folder where image data downloaded (default: `localhost/data`)
* `--counts-path` folder where image counts are stored (default: `localhost/counts`)
* `--log-level` Level of detail to report in logs (default: `INFO`)
* `--help` detailed help on each option, with default arguments listed

## Launching the script

Launch the script by defining a start date and end date for images to be processed
between (inclusive), the script will detect image sources from the `localhost/config/analyse` folder.

So for example, to process all selected cameras between 1st and 2nd of June 2020, run:
```bash
python3 scripts/localhost/batch_process_images.py --start-date="20200601" --end-date="20200602"
```

Progress bars will be presented showing the dates being iterated over, along with which image
supplier and camera. This will take approximately 30s per camera image, as it is processing
144 images per selected day (images are captured every 10 minutes, so 6 per hour; hence 24*6=144 images).

Analysis is recorded in CSV files, generating one CSV file per day in the folder named after the current
model (defined in `scripts/localhost/config/analyse-configuration.json`).
At present the single detection model used is called `NewcastleV0`, supplied courtesy of
Newcastle University's Urban Observatory from their [GitHub repository](https://github.com/TomKomar/uo-object_counting).


# Using `download_files.py`

This script downloads the set of camera images to local disc; it should be called every 10 minutes to
accumulate imagery to process.

Command line options are:
* `--config-folder` folder where configuration data is stored (default: `localhost/config`)
* `--download-folder` folder where image data downloaded (default: `localhost/data`)
* `--maximum-download-attempts` maximum number of download attempts per image (default: 5)
* `--log-level` Level of detail to report in logs (default: `INFO`)
* `--help` detailed help on each option, with default arguments listed

## Launching the script

The script can be launched without arguments, as the defaults will be sufficient;
this will search the `localhost/config/ingest` folder for image sources, which will then
be downloaded into the `localhost/data` folder.

For example, run:
```bash
python3 scripts/localhost/download_files.py
```

Progress bars will be presented showing the cameras being iterated over, noting that the execution time will
depend on your internet connection. The script downloads items serially (one at a timer), so does not maximise
download bandwidth.


# Using `process_scheduled.py`

This script analyses images taken 20 minutes ago, and should be called every 10 minutes to "chase" the downloaded
images. Note that it processes 20 minutes in arrears as it requires images before and after the analysed image
(in time), to detect static objects.

Command line options are:
* `--config-folder` folder where configuration data is stored (default: `localhost/config`)
* `--download-folder` folder where image data downloaded (default: `localhost/data`)
* `--counts-path` folder where image counts are stored (default: `localhost/counts`)
* `--log-level` Level of detail to report in logs (default: `INFO`)
* `--help` detailed help on each option, with default arguments listed

## Launching the script

Launch the script with the defaults, the script will detect image sources from the `localhost/config/analyse` folder.

So for example, to process all selected cameras on the current data:
```bash
python3 scripts/localhost/process_scheduled.py
```

Progress bars will be presented showing the cameras being iterated over. There will be a delay as the model
is loaded, then the processing will start. It will take ~1s per image, depending on local hardware
(the model uses tensorflow, so will take advantage of multiple cores or, if installed, a GPU).

Analysis is recorded in CSV files, generating one CSV file per day in the folder named after the current
model (defined in `scripts/localhost/config/analyse-configuration.json`).
At present the single detection model used is called `NewcastleV0`, supplied courtesy of
Newcastle University's Urban Observatory from their [GitHub repository](https://github.com/TomKomar/uo-object_counting).


# Using `remove_old_images.py`

This script removes images older than a specified number of days from the `data` bucket.

Once images are analysed, they do not need to be retained (unless you are modifying the model or filtering)
and can be removed. In case of system issues, the images can be retained on a rolling deletion basis - default
is to remove images older than 28 days (4 weeks).

Command line options are:
* `--maximum-number-of-days` maximum number of days an image is retained before it is deleted (date folder is
used to determine when it was created - so if an image was downloaded today but the folder indicated 60 days ago,
running the script with less than 60 days specified will remove the image)
* `--download-folder` folder where image data was downloaded - and where it will be removed (default: `localhost/data`)
* `--log-level` Level of detail to report in logs (default: `INFO`)
* `--help` detailed help on each option, with default arguments listed

## Launching the script

Script uses the default data download location, so to to remove all images older than 28 days just use defaults:
```bash
python3 scripts/localhost/remove_old_images.py
```


# Using `update_sources.py`

This script updates the list of cameras available to ingest (but does not amend the list to be analysed).

Command line options are:
* `--config-folder` folder where configuration data is stored (default: `localhost/config`)
* `--log-level` Level of detail to report in logs (default: `INFO`)
* `--help` detailed help on each option, with default arguments listed

## Launching the script

Launch the script with the defaults, the script will store image sources in the `localhost/config/ingest` folder.

So for example, to process all selected cameras on the current data:
```bash
python3 scripts/localhost/update_sources.py
```

Each image provider is listed as it is examined for camera sources. At present only Transport for London
is supported (TfL), but this can be expanded by the user as required.
