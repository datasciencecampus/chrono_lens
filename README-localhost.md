# Identifying Objects in Traffic Cameras - Local Host Variant

This project aims to examine public traffic camera feeds,
build vision models that can detect objects in these feeds,
and to store the object counts for further analysis such as
trending over time. Camera data is stored in the short term
to enable models to be trained, and to support late data arrival.
Once processed, the camera data no longer needs to be stored unless alternative models are required to be
trialled later.

This document describes how to host the project on a single machine.

## Limitations

* NE Travel Data ingestion is not supported
* For simplicity, database support is not provided - instead CSV files are generated one per day (akin to database
sharding), which can be imported into a database as required.
* Time series analysis has not been ported to `localhost`; the R code is available in
`cloud/vm`, but assumes the data is hosted in BigQuery.

# Design and Architecture of the Solution to Object Identification
The object identification is experimental, and hence needs to be re-evaluated
multiple times across the same dataset. With this in mind, rather than
streaming data through a model to generate results, we instead collect the
data in bucket storage for later processing (and potentially re-processing
with a refined model). This creates the following requirements:

1. Discover available image sources
1. Update image sources regularly (e.g. daily)
1. Download all images at regular intervals and store for later processing

Once imagery is downloaded, we can then process. There are two scenarios:

1. Run a specified model over historical data, or
1. Run a specified model over newly received data

Finally, images can be deleted once no longer required.

## Discovering Available Image Sources
This is initiated by manually looking for public sources of data,
as we are focused on a publicly available and reusable solution.
If you are using your own data, this step is simply to determine
what data you have and where it is stored - assuming you will follow this workflow
and upload your data to google cloud to be processed.

The result of this phase is a JSON file per camera provider
(e.g. Transport for London (TfL), North East Travel Information),
which is stored in a `localhost/config/ingest` folder. For instance, TfL cameras
sources would be stored in `localhost/config/ingest/TfL-images.json`, which is a list
of image URLs.

## Updating Image Sources

Given suppliers of publicly available cameras often provide API
endpoints on the web, we have a python tool that calls these
once a day to update the list of camera images we should
download. This is the `scripts/localhost/update_sources.py` script,
which generates a JSON file describing each available camera
and its image URL where it can be downloaded.
Detailed usage instructions are presented in [`scripts/localhost/README.md`](scripts/localhost/README.md).

This script needs to be called daily (or as often as you wish to updated of available imagery);
we recommend daily at 3am. Other suppliers may not provide such an endpoint, in which case
this function is not needed.

**Note** you may wish to reduce the number of images the system ingests - in which case, run this utility once to
populate the `JSON` files, then remove unnecessary cameras. For example, TfL will ingest >900 cameras, yet you may
only wish to download (and later process) far fewer. Don't forget to likewise reduce the cameras to be analysed to
reflect the reduced list, otherwise the CSV will contain many entries flagged as `missing`.

## Download All Images at Regular Intervals

The python script `scripts/localhost/download_files.py` needs to be called at 10 minute intervals past the hour,
which will request each image listed in the JSON files
stored in the `localhost/config/ingest` folder. Each image is stored in
the `localhost/data` folder, using the naming convention
`<camera supplier>/<date as YYYYMMDD>/<time HHMM>/<camera ID>.<format>`.
* "Camera supplier" is the name of the JSON file (without the `.json` extension)
* Date and time are when the request was triggered - not when the
image was actually captured
  * Hence the date/time may be up to 10 minutes out
  * However, this ensures a consistent, simplified folder structure
  * Actual capture date/time may be stored in JPEG metadata,
    depending on supplier
* Camera ID is the base name of the source image file - which
  we assume is a unique ID for that supplier's camera
* File extension is as originally provided - it may be JPEG,
or it something else; for instance, TfL offer both JPEG and MP4.

To trigger regular downloads, the local system's scheduler should be used. Under Microsoft Windows
there is the [Task Scheduler](https://docs.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)
(_note: this link is for developer API access rather than the UI_) or
UN*X [crontab](https://man7.org/linux/man-pages/man5/crontab.5.html) (_also suitable for MacOS_).

`scripts/localhost/download_files.py` internally retries downloads in the case when the
URL doesn't return a 200 (success code) or 404 (not found) - e.g. if a 504
"Gateway timeout" error code is returned, then the client should try again.
A random length delay is triggered before retrying to improve load balance and chances of success.
Detailed usage instructions are presented in [`scripts/localhost/README.md`](scripts/localhost/README.md).

### `crontab` Quick Guide (UN*X / MacOS)

Using `crontab` we are able to execute Python scripts automatically at regular intervals. This is perfect for running
bash scripts which in turn will execute `download_files.py` and `process_scheduled.py`. Below is a quick simple guide
on installing and setting up `crontab` for users on MacOS. We highly recommend **NOT** setting up chrono_lens within the
`Documents` folder due to its symbolic link nature. Instead we recommend the 'Home' folder.

**1. Creating Bash Scripts for `crontab`**

Within a text editor you will need to write two simple bash scripts to 1. activate your virtual environment
(both will do this), 2. one will execute `download_file.py`, and 3. the second will execute `process_scheduled.py`.

**An example bash script for download_files.py:**

`#!/bin/bash`
`export PYTHONPATH='/location/of/your/chrono_lens_folder'`
`cd /location/of/your/chrono_lens_folder`
`source venv/bin/activate`
`python3 scripts/localhost/download_files.py`

Save the above as `download_files_bash_script.sh`. Repeat accordingly for `process_scheduled.py`.

**2. Accessing `crontab`**

Within the terminal app execute `sudo crontab -u your_username -e` and `crontab` will open in the VI text editor.
Enter `SHIFT + I` to allow editing ("insert" mode in the VI editor). Enter the following:

`0/10 * * * * /location/of/your/download_files_bash_script.sh`
`0/10 * * * * /location/of/your/process_scheduled_bash_script.sh`

Enter `ESC` and then `SHIFT + Z` and `SHIFT + Z` again. This will save your edits to `crontab`.

The `0/10 * * * *` commands an execution every 10-minutes starting at 0 minutes past the hour; we found
[crontab guru](https://crontab.guru/#0/10_*_*_*_*) useful for an explanation of the fields.

**3. Setting Permissions (to Enable `crontab` to Access Your Scripts)**

**WARNING** this step will ensure `crontab` can access your files - you may be able to use weaker permissions, but the below
approach has been tested to work. You should consider carefully if you want to do this on a shared / multi-user machine,
as this will render your files visible to other users.

We need to ensure all of the bash scripts and tree of directories above has 'read, execute access for everyone'.
We can achieve this by executing simple commands within the terminal application. Simply go to the location of your
saved bash script and execute the following separately:

`chmod 755 download_files_bash_script.sh`
`chmod 755 process_scheduled_bash_script.sh`
`chmod 755` within the folder containing your bash scripts and each parent folder above.

Images and counts should now be populating your `chrono_lens/local_host` sub-folders within 10 minutes.

## Run a Specified Model Over Historical Data
The storage of the data in a local folder enables us to re-process data with different
models, and to compare results to see impact of models. With this in mind,
we need to be able to run any model, and store its results for comparison.
The approach we took is to store models parameters in the `localhost/config/models` folder,
where the root folder name is a specific model version - hence for the RCNN model
received from Newcastle University, we have a folder called `NewcastleV0`. Inside the
bucket the file `configuration.json` defines any specific parameters - such as
filename of serialised model.

In addition, models can be daisy-chained to form a pipeline, where the pipeline is defined
as a sequence of model names separated by `_`.
At present this is limited to pre-processing with a `FaultyImageFilter` and
post-processing with a `StaticObjectFilter`,
used when the model name is defined as `FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0`.

The specific model to use is declared in `localhost/config/analyse-configuration.json`.

**NOTE:** given that settings are local to the user, we do not store them in GitHub. However,
as a starting point, we have provided our configurations in the `chrono_lens/localhost/exampleJSON` folder.
The JSON files present need to be copied to the appropriate `localhost` subfolder; this is achieved by replacing
underscores (`_`) with folder separators (which depend on your local system; Windows will need `\`, UN*X will need `/`).
For example, `localhost_config_models_FaultyImageFilterV0_configuration.json` should be copied to a UN*X folder
of `localhost/config/models/FaultyImageFilterV0/configuration.json`. Note that the RCNN weights must be supplied
as an additional file - see next section.

The script to use is `scripts/locahost/process_scheduled.py`;
detailed usage instructions are presented in [`scripts/localhost/README.md`](scripts/localhost/README.md).

### Newcastle Model
This model is detected by its name starting with `Newcastle` - underneath it is an RCNN
defined using tensorflow. The JSON configuration file defines the file name of the
serialised model weights, and reference information for the user (ignored by the pipeline),
such as GitHub source. The user can hence provide multiple variants of the model by putting
each model in a different root folder. A local copy of the serialised weights is provided at
`tests/test_data/test_detector_data/fig_frcnn_rebuscov-3.pb` and must be copied into the
`localhost/config/models/NewcastleV0/` folder.

### Faulty Image Filter (Pre-process)
This filter rejects images if they are corrupt; two forms are detected:
1. Large portion of image contain repeated rows of exactly the same R,G,B values, and
2. Large proportion of a pure greyscale where R=G=B (for different values of pure grey in the area); this
detects a "camera off" static image.

The constants that define thresholds for faulty image detection are defined in the
JSON configuration file. To run alternative settings, a different folder should be created
so that existing model configurations are unchanged to enable re-running of models as required
and hence ensure repeatability. The new configuration hence has a new configuration folder, and this
is what is supplied (for instance, you may make a v1 variant, so model name would be
`FaultyImageFilterV0`, and could be used with the Newcastle model via
`FaultyImageFilterV1_NewcastleV0` or with the static object filter with
`FaultyImageFilterV1_NewcastleV0_StaticObjectFilterV0`).

### Static Object Filter (Post-process)
The constants that define thresholds for static object detection are defined in the
JSON configuration file. To run alternative settings, a different folder should be created
so that existing model configurations are unchanged to enable re-running of models as required
and hence ensure repeatability. The new configuration hence has a new configuration folder, and this
is what is supplied (for instance, you may make a v1 variant, so model name would be
`FaultyImageFilterV1`, and could be used with the Newcastle model via `NewcastleV0_StaticObjectFilterV1`).

## Running Models
The python script `scripts/localhost/batch_process_images.py` will run selected models over named cameras
across a selected date range. Refer to `scripts/localhost/README.md` for full instructions.

## Deleting Images Once No Longer Required

Once images have been processed, they do not need to be retained, unless they need to be
re-processed (e.g. if model experimentation is being carried out). The script `scripts/localhost/remove_old_images.py`
deletes images older than 28 days (4 weeks), as this is deemed a sufficient window to detect
recent issues and sufficient historical images to correct the time series.
Detailed usage instructions are presented in [`scripts/localhost/README.md`](scripts/localhost/README.md).

# Differing Results to ONS Faster Indicators

Note, running the default models and camera locations provided will yield results that differ from those published by
ONS Faster Indicators. This difference will arise from internal factors such as variation in camera sampling times and
manual imputation when cameras are unavailable for sustained periods. Furthermore, external changes such as camera addresses
changing over time will impact results. The current lists of selected cameras are valid as of 25/01/2021.

# Adding Cameras to be Processed After Images Have Been Downloaded

The python script `scripts/localhost/update_sources.py` populates the folder
`localhost/config/ingest`, creating one JSON file per camera image supplier. However, images are not analysed unless
they are specified in `localhost/config/analyse` JSON files

## Uploading Models

**Our default models have already been installed for you. However this section will detail how to add your own models
if you so wish to do so.**

Each model, pre- and post-processor follows the naming pattern: `objectV#` where the `V#` is used to demark a version
number - such as `V0`. This enables multiple configurations to be defined, with the idea that existing configurations
that have been used are not modified, but new variants created instead. With this, previous processing runs
can be recreated with ease, as the full name of each model/processor is used to name the database where results are
stored. Already set-up and ready, we have 1 of each defined (model, pre, post):
1. `FaultyImageFilterV0` - pre-processor, marks images as faulty if they are unchanging or contain "camera unavailable"
imagery
1. `NewcastleV0` - a model, an RCNN as provided from Newcastle University's Urban Observatory (see file
[`uo-object_counting/app/fig_frcnn_rebuscov-3.pb`](https://github.com/TomKomar/uo-object_counting/commit/26c9f29b46ba7afa6294934ab8326fd4d5f3418d#diff-f631985316405adc5fec3f864f5bd72f"))
1. `StaticObjectFilterV0` - a post-processor, that rejects detected objects that do not move between frames

If, for instance, the pre-processor `FaultyImageFilterV0` and the model `NewcastleV0` are used, then a folder
named `FaultyImageFilterV0_NewcastleV0` will be created in `localhost/counts` where a CSV file will be generated
for each calendar day.

### Adding Cameras to be Analysed

**Camera locations have already been added for you and include TfL.
The following section details how one would add additional locations.**

Each camera supplier needs a JSON file in the `localhost/config/analyse` folder, and is used to determine which images will be processed.
An JSON files is present in the [`chrono_lens/localhost/exampleJSON/localhost_config_analyse_TfL-images.json`](chrono_lens/localhost/exampleJSON/localhost_config_analyse_TfL-images.json)
file. Each JSON file contains a list of camera names, for example, `TfL-images.json`:
```JSON
[
  "00001.01251",
  "00001.01252",
  "00001.01445",
  "00001.01606",
  "..."
]
```

The named cameras in a JSON file are mapped to images named `<JSON base filename>/YYYYMMDD/HHMM/<camera name>.jpg`, where
"JSON base filename" is the JSON filename without the ".json" extension.
