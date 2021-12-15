
# SEADEC IMPUTATION WITH ALGORITHM MEAN, SQRT TRANSFORMATION, SEATS

# Run function script

source("data_impute_and_seats_functions.R")

library(readr) # for reading text from a file

# ============================= SETTINGS ==================================
# Measures how long the system takes
startTime <- Sys.time()
today <- Sys.Date()

# required if not run on VM - need access token
bq_auth(path = "bigquery-r-auth-token.json")

TRAFFIC_TYPES <- list("car", "motorcyclist", "bus", "truck", "van", "person", "cyclist", c("person", "cyclist"))

locations_and_dates_csv_filename <- "cache/Traffic_cameras_locations_and_start_dates.csv"
locations_datasets_csv_filename <- "cache/list_of_location_datasets.csv"
maxinum_number_of_retries <- 5
minimum_retry_delay <- 60
maximum_retry_delay <- 120

# BigQuery project for SQL query
project <- "PROJECT_ID_PLACEHOLDER"
model_name <- read_file("model-in-use.txt")

# ============================= SETTINGS ==================================

# Query BigQuery to get a list of locations present
bq_data <- NULL
retryCounter <- 0
while (is.null(bq_data) && retryCounter < maxinum_number_of_retries) {
    retryCounter = retryCounter + 1
    bq_data = tryCatch(
    {
        sql <- paste0('
                SELECT DISTINCT source
                FROM PROJECT_ID_PLACEHOLDER.detected_objects.', model_name, '
                WHERE date > "2020-01-01"
                ')
        bq_data <- bq_table_download(bq_project_query(project, sql))
    },
    error = function(e){
        message("Caught an error!")
        print(e)
        message(paste0("Sleeping before retrying query."))
        Sys.sleep(sample(minimum_retry_delay : maximum_retry_delay , 1))
        message("Retrying BigQuery Download")
    },
    warning = function(w){
        message('Caught a warning!')

        print(w)
    }
    )
}
bq_data <- bq_data[order(bq_data$source),]
locations_from_bigquery <- as.data.frame(bq_data)
rm(sql, bq_data, retryCounter)

# If location and date csv doesn't exist then download locations and corresponding dates from bigquery and create csv
# If the csv already exist then read in csv
if (! file.exists(locations_and_dates_csv_filename)) {
  # Create variable to house location and date data for csv
  locations_and_dates_csv_data <- NULL
    locations_and_dates_csv_data <- lapply(locations_from_bigquery$source, FUN = getStartDateForLocationFromBigQuery,
    locations_and_dates = locations_and_dates_csv_data, model_name = model_name,
    maxinum_number_of_retries = maxinum_number_of_retries,
    minimum_retry_delay = minimum_retry_delay, maximum_retry_delay = maximum_retry_delay)
  locations_and_dates_csv_data <- as.data.frame(data.table::rbindlist(locations_and_dates_csv_data, idcol = FALSE))
  locations_and_dates_csv_data$source <- as.character(locations_and_dates_csv_data$source)
  # Save csv
  write.csv(locations_and_dates_csv_data, file = locations_and_dates_csv_filename, quote = FALSE, row.names = FALSE)
} else {
  # Read in the existing csv containing locations and start dates
  locations_and_dates_csv_data <- read.csv2(locations_and_dates_csv_filename,
                                            sep = ",", check.names = FALSE, stringsAsFactors = FALSE, strip.white = TRUE, na.strings = "")
  locations_and_dates_csv_data$date <- as.Date(locations_and_dates_csv_data$date)
}

# Check if the locations from the csv match the locations from bigquery
not_matched_locations <- setdiff(locations_from_bigquery$source, locations_and_dates_csv_data$source)
rm(locations_from_bigquery)
# If there are new locations, get corresponding start date of new location from bigquery and update csv
if (! is.na(not_matched_locations[1])) {
  print("Locations in csv do not match those in bigquery. Loading in new locations and corresponding start dates")
  locations_to_add <- NULL
    locations_to_add <- lapply(not_matched_locations, FUN = getStartDateForLocationFromBigQuery,
    locations_and_dates = locations_to_add, model_name = model_name,
    maxinum_number_of_retries = maxinum_number_of_retries,
    minimum_retry_delay = minimum_retry_delay, maximum_retry_delay = maximum_retry_delay)
  locations_to_add <- as.data.frame(data.table::rbindlist(locations_to_add, idcol = FALSE))
  locations_to_add$source <- as.character(locations_to_add$source)
  locations_to_add$time <- as.character(locations_to_add$time)

  locations_and_dates_csv_data <- rbind(locations_and_dates_csv_data, locations_to_add)
  write.csv(locations_and_dates_csv_data, file = locations_and_dates_csv_filename, quote = FALSE, row.names = FALSE)
  print("CSV with locations and corresponding start date updated")
    rm(locations_to_add)
}
rm(not_matched_locations, locations_and_dates_csv_filename)

# if file doesn't exist.
# If running the VM for the first time or there is no existing location dataset csv
if (! file.exists(locations_datasets_csv_filename)) {
  # Check new data sources if there is at least five weeks of data than download it (not including latest week)
  # Else download latest week and output pdfs for QA
  locations_to_check <- locations_and_dates_csv_data$source
  new_locations_data <- NULL
  new_locations_pdf <- NULL

    new_locations_list <- lapply(locations_to_check, FUN = prepareDataIfNewLocationOtherwiseReportStatus,
                               locations_and_dates = locations_and_dates_csv_data, today = today, last_processed_date = today - 8,
                               project = project, new_locations_data = new_locations_data, new_locations_pdf = new_locations_pdf,
    model_name = model_name, maxinum_number_of_retries = maxinum_number_of_retries,
    minimum_retry_delay = minimum_retry_delay, maximum_retry_delay = maximum_retry_delay)

  new_locations_list <- unlist(new_locations_list, recursive = FALSE)
  new_locations_unlist <- lapply(split(new_locations_list, names(new_locations_list)), function(x) do.call(rbind, x))
  new_locations_data <- new_locations_unlist$new_locations_data

    rm(new_locations_list, new_locations_unlist, locations_to_check, new_locations_pdf)

  if(!is.null(new_locations_data)){
      write.csv(new_locations_data, file = locations_datasets_csv_filename, quote = FALSE, row.names = FALSE)
  }
    rm(locations_and_dates_csv_data, new_locations_data)
} else {
    # Read in the existing csv containing locations of datasets
    locations_in_dataset <- read.csv2(locations_datasets_csv_filename,
    sep = ",", check.names = FALSE, stringsAsFactors = FALSE, strip.white = TRUE, na.strings = "")
    locations_in_dataset$last_date_processed <- as.Date(locations_in_dataset$last_date_processed)

    # Check if the locations from the csv match the locations from dataset
    not_matched_locations <- setdiff(locations_and_dates_csv_data$source, locations_in_dataset$source)

  print("Check if unique locations in existing data set are the same as in the location/date csv")
  # If locations do not match then check that start date of new location.
  # If date is at least five weeks older than date of running then download data for new location, tidy and impute it and add it to existing dataset
  if(!is.na(not_matched_locations[1])){
    print("Locations do not match; checking for 5 weeks of new data...")
    new_locations_data <- NULL
    new_locations_pdf <- NULL

      new_locations_list <- lapply(not_matched_locations, FUN = prepareDataIfNewLocationOtherwiseReportStatus,
                                 locations_and_dates = locations_and_dates_csv_data, today = today, last_processed_date = today - 8,
                                 project = project, new_locations_data = new_locations_data, new_locations_pdf = new_locations_pdf,
      model_name = model_name, maxinum_number_of_retries = maxinum_number_of_retries,
      minimum_retry_delay = minimum_retry_delay, maximum_retry_delay = maximum_retry_delay)

    new_locations_list <- unlist(new_locations_list, recursive = FALSE)
    new_locations_unlist <- lapply(split(new_locations_list, names(new_locations_list)), function(x) do.call(rbind, x))
    new_locations_data <- new_locations_unlist$new_locations_data

      rm(new_locations_list, new_locations_unlist, new_locations_pdf)

    if(!is.null(new_locations_data)){
        new_locations_data <- rbind(locations_in_dataset, new_locations_data)
        write.csv(new_locations_data, file = locations_datasets_csv_filename, quote = FALSE, row.names = FALSE)
    }
  }
    rm(not_matched_locations, locations_and_dates_csv_data, new_locations_data, locations_in_dataset)
}

if (file.exists(locations_datasets_csv_filename)) {

    locations_dates_for_weekly_query <- read.csv2(locations_datasets_csv_filename,
    sep = ",", check.names = FALSE, stringsAsFactors = FALSE, strip.white = TRUE, na.strings = "")
    locations_dates_for_weekly_query$last_date_processed <- as.Date(locations_dates_for_weekly_query$last_date_processed)

    # Load new data from bigquery
    new_locations_dates_for_weekly_query <- NULL
    new_locations_dates_for_weekly_query <- lapply(locations_dates_for_weekly_query$source, FUN = loadLatestBigQueryDataImputeAndAppend,
    locations_and_dates = locations_dates_for_weekly_query, project = project,
    today = today, model_name = model_name,
    new_locations_and_dates = new_locations_dates_for_weekly_query,
    maxinum_number_of_retries = maxinum_number_of_retries,
    minimum_retry_delay = minimum_retry_delay, maximum_retry_delay = maximum_retry_delay)

    new_locations_dates_for_weekly_query <- bind_rows(new_locations_dates_for_weekly_query)
    write.csv(new_locations_dates_for_weekly_query, file = locations_datasets_csv_filename, quote = FALSE, row.names = FALSE)
} else {
    print(paste0("Exiting script early as there is either less than five weeks of data (first run) or no dates between the last processed date ", last_processed_date, " and today ", today))
}
