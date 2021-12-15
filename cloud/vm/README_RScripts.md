# Overview of R scripts used to generate time series data for Faster Indicators

This guide covers an overview of the main R scripts used.

# Table of Contents
1. [data_impute_run.R](#data_impute_runr)
2. [data_seats_run.R](#data_seats_runr)
3. [data_impute_and_seats_functions.R](#data_impute_and_seats_functionsr)

## `data_impute_run.R`

This script is in charge of downloading data from BigQuery, tidying and imputing the data and outputting QA files.
Each location is processed separately and will be stored in separate `.Rda` files, e.g. `TfL-images.Rda`. The CSV
file `list_of_location_datasets.csv` will list the location names of datasets currently being processed weekly and
their corresponding latest date in each dataset. This file isused so the R script knows which locations to download
and process for the weekly query.
The CSV file `Traffic_cameras_locations_and_start_dates.csv` lists the locations present in BigQuery and their
corresponding start dates. This file is used so the R script knows when a new location is added to BigQuery and when
to download the data.

There will be a copy of each of the following QA files for each location processed. There will also be a copy for any
new locations added in BigQuery but which do not have at least 5 weeks of data:
* `status_report_YYMMDD_location_name.png`
* `Status_report_per_camera_YYMMDD_location_name.pdf`
* `Status_report_per_camera_long_version_YYMMDD_location_name.pdf`
* `Status_report_per_location_YYMMDD_location_name.pdf`

Below is an outline of the code for script `data_impute_run.R`:

*	Get list of locations present in BigQuery
*	`cache/Traffic_cameras_locations_and_start_dates.csv` exists?
    * No – download locations and corresponding start dates from BigQuery and create CSV
    * Yes – Read in CSV
* Compare locations from CSV and those downloaded from BigQuery. Are there new locations?
    * Yes – get corresponding start date for new locations from BigQuery and update CSV
* `cache/list_of_location_datasets.csv` exists?
    * No – for each new data source is there at least five weeks of data?
        * Yes – download data up to ‘today – 8’ (i.e. download up to but not including the latest week of data), tidy,
          impute and save as Rda file. Add location name and last processed date to
          `cache/list_of_location_datasets.csv`.
        * No – Download latest week and output PDFs for QA purposes.
    * Yes – Read in existing `cache/list_of_location_datasets.csv`. Check if locations in
      `cache/list_of_location_datasets.csv` match with the ones in
      `cache/Traffic_cameras_locations_and_start_dates.csv`. Do locations match?
        * No – check start data of new location, is there at least five weeks of data?
            * Yes – download data up to ‘today – 8’ (i.e. download up to but not including the latest week of data),
            tidy, impute and save as Rda file. Add location name and last processed date to
            `cache/list_of_location_datasets.csv`.
            * No – Download latest week and output PDFs for QA purposes.
* `cache/list_of_location_datasets.csv` exists?
    * Yes – read in CSV. For each location in CSV download latest week of data, tidy and output QA files. Read in
      existing dataset for location, merge last 4 weeks of data onto new data and impute missing data in new data.
      Append new week of data onto existing dataset and save Rda. Save updated last processed data to CSV.
    * No – exit script

## `data_seats_run.R`

This script is run after `data_imputes_run.R` and is in charge of aggregating the data and performing SEATS. Each
location is aggregated and has SEATS applied separately. The results of SEATS then gets merged together to produce
the CSV file for Faster Indicators. Next, a PDF showing a four week history is produced using this data.

This script outputs 2 files:
* `Trafcam_data_YYMMDD.csv`
* `Four_week_history_YYMMDD.pdf`

## `data_impute_and_seats_functions.R`

This script houses all the functions used in the other two scripts.
