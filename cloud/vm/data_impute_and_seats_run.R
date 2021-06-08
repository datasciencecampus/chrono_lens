# SEADEC IMPUTATION WITH ALGORITHM MEAN, SQRT TRANSFORMATION, SEATS

# Run function script

source("data_impute_and_seats_functions.R")

# ============================= SETTINGS ==================================
# Measures how long the system takes
startTime <- Sys.time()
today <- Sys.Date()

# required if not run on VM - need access token
bq_auth(path = "bigquery-r-auth-token.json")

TRAFFIC_TYPES <- list("car", "motorcyclist", "bus", "truck", "van", "person", "cyclist", c("person", "cyclist"))

imputed_data_filename <- "cache/imputed_dataset.Rda"
locations_and_dates_csv_filename <- "cache/Traffic_cameras_locations_and_start_dates.csv"

# BigQuery project for SQL query
project = "PROJECT_ID_PLACEHOLDER"
model_name <- read_file("model-in-use.txt")

# ============================= SETTINGS ==================================
# Query BigQuery to get a list of locations present
sql <- paste0('
                SELECT DISTINCT source
                FROM PROJECT_ID_PLACEHOLDER.detected_objects.', model_name, '
                WHERE date > "2020-01-01"
                ')
bq_data <- bq_table_download(bq_project_query(project, sql))
bq_data <- bq_data[order(bq_data$source),]
locations_from_bigquery <- as.data.frame(bq_data)
rm(sql, bq_data)

# If location and date csv doesn't exist then download locations and corresponding dates from bigquery and create csv
# If the csv already exist then read in csv
if (! file.exists(locations_and_dates_csv_filename)) {
  # Create variable to house location and date data for csv
  locations_and_dates_csv_data <- NULL
  locations_and_dates_csv_data <- lapply(locations_from_bigquery$source, FUN = getStartDateForLocationFromBigQuery, locations_and_dates = locations_and_dates_csv_data, model_name = model_name)
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
  locations_to_add <- lapply(not_matched_locations, FUN = getStartDateForLocationFromBigQuery, locations_and_dates = locations_to_add)
  locations_to_add <- as.data.frame(data.table::rbindlist(locations_to_add, idcol = FALSE))
  locations_to_add$source <- as.character(locations_to_add$source)
  locations_to_add$time <- as.character(locations_to_add$time)

  locations_and_dates_csv_data <- rbind(locations_and_dates_csv_data, locations_to_add)
  write.csv(locations_and_dates_csv_data, file = locations_and_dates_csv_filename, quote = FALSE, row.names = FALSE)
  print("CSV with locations and corresponding start date updated")
  rm(locations_to_add, locations_and_dates_csv_filename)
}
rm(not_matched_locations)

print("Loading in existing traffic camera data set")
load_existing_data <- loadExistingImputedData(imputed_data_filename)
imputed_data <- load_existing_data$imputed_data
last_processed_date <- load_existing_data$last_processed_date

# If running the VM for the first time or there is no existing imputed dataset
if(is.null(imputed_data)){
  # Check new data sources if there is at least five weeks of data than download it (not including latest week)
  # Else download latest week and output pdfs for QA
  locations_to_check <- locations_and_dates_csv_data$source
  new_locations_data <- NULL
  new_locations_pdf <- NULL
  new_locations_list <- lapply(locations_to_check, FUN = checkStartDateOfNewLocation,
                               locations_and_dates = locations_and_dates_csv_data, today = today, last_processed_date = today - 8,
                               project = project, new_locations_data = new_locations_data, new_locations_pdf = new_locations_pdf,
                               model_name = model_name)

  new_locations_list <- unlist(new_locations_list, recursive = FALSE)
  new_locations_unlist <- lapply(split(new_locations_list, names(new_locations_list)), function(x) do.call(rbind, x))
  new_locations_data <- new_locations_unlist$new_locations_data
  new_locations_pdf <- new_locations_unlist$new_locations_pdf

  rm(new_locations_list, new_locations_unlist, locations_to_check)

  if(!is.null(new_locations_data)){
    # Impute missing data
    print("Running imputeData function on new data source")
    new_locations_data_imputed <- imputeData(df = new_locations_data)
    print("Finished imputeData function on new data source")
    rm(new_locations_data)

    print("Saving update imputed dataset")
    saveRDS(new_locations_data_imputed, file = imputed_data_filename)
  }

  if(!is.null(new_locations_pdf)){
      print("There isn't five weeks or more of data so outputting pdfs for latest week for QA")

    print("Producing graph for faulty, missing, present camera counts")
    produceCameraStatusGraph(df = new_locations_pdf, date = today, filename = "_new_data_source")

    print("Produce PDF per camera per location")
    produceStatusReportPerCameraPDF(df = new_locations_pdf, date = today, filename = "_new_data_source")

    print("Produce PDF per camera per location (long version)")
    produceStatusReportPerCameraPDFLongVersion(df = new_locations_pdf, date = today, filename = "_new_data_source")

    print("Produce PDF heatmap per location")
    produceStatusReportPerLocationPDF(df = new_locations_pdf, date = today, filename = "_new_data_source")

    rm(new_locations_pdf)
  }
  rm(locations_and_dates_csv_data, last_processed_date, load_existing_data, imputed_data)
} else {
  print("There is an existing dataset")
  # Get list of locations in dataset
  locations_in_dataset <- unique(imputed_data$source)
  # Check if the locations from the csv match the locations from dataset
  not_matched_locations <- setdiff(locations_and_dates_csv_data$source, locations_in_dataset)
  rm(locations_in_dataset)

  print("Check if unique locations in existing data set are the same as in the location/date csv")
  # If locations do not match then check that start date of new location.
  # If date is at least five weeks older than date of running then download data for new location, tidy and impute it and add it to existing dataset
  if(!is.na(not_matched_locations[1])){
    print("Locations do not match; checking for 5 weeks of new data...")
    new_locations_data <- NULL
    new_locations_pdf <- NULL
    new_locations_list <- lapply(not_matched_locations, FUN = checkStartDateOfNewLocation,
                                 locations_and_dates = locations_and_dates_csv_data, today = today, last_processed_date = today - 8,
                                 project = project, new_locations_data = new_locations_data, new_locations_pdf = new_locations_pdf,
                                 model_name = model_name)

    new_locations_list <- unlist(new_locations_list, recursive = FALSE)
    new_locations_unlist <- lapply(split(new_locations_list, names(new_locations_list)), function(x) do.call(rbind, x))
    new_locations_data <- new_locations_unlist$new_locations_data
    new_locations_pdf <- new_locations_unlist$new_locations_pdf

    rm(new_locations_list, new_locations_unlist)

    if(!is.null(new_locations_data)){

      # Impute missing data
      print("Running imputeData function on new data source")
      new_locations_data_imputed <- imputeData(df = new_locations_data)
      print("Finished imputeData function on new data source")
      rm(new_locations_data)

      imputed_data_updated <- rbind(imputed_data, new_locations_data_imputed)
      print("Saving update imputed dataset")
      saveRDS(imputed_data_updated, file = imputed_data_filename)
      rm(imputed_data_updated, new_locations_data_imputed)
    }

    if(!is.null(new_locations_pdf)){
      print("There isn't more than 28 days of data so outputting pdfs for latest week for QA")

      print("Producing graph for faulty, missing, present camera counts")
      produceCameraStatusGraph(df = new_locations_pdf, date = today, filename = "_new_data_source")

      print("Produce PDF per camera per location")
      produceStatusReportPerCameraPDF(df = new_locations_pdf, date = today, filename = "_new_data_source")

      print("Produce PDF per camera per location (long version)")
      produceStatusReportPerCameraPDFLongVersion(df = new_locations_pdf, date = today, filename = "_new_data_source")

      print("Produce PDF heatmap per location")
      produceStatusReportPerLocationPDF(df = new_locations_pdf, date = today, filename = "_new_data_source")

      rm(new_locations_pdf)
    }
  }
  rm(not_matched_locations, locations_and_dates_csv_data, last_processed_date, load_existing_data, imputed_data)
}

# Load existing imputed data if it exists
load_existing_data <- loadExistingImputedData(imputed_data_filename)
imputed_data <- load_existing_data$imputed_data
last_processed_date <- load_existing_data$last_processed_date
locations_for_weekly_query <- unique(imputed_data$source)
num_of_days_to_impute <- as.numeric(today - last_processed_date) - 1

if(!today - 1 == last_processed_date & !is.null(locations_for_weekly_query)){
  # Load new data from bigquery
  new_data <- loadBigQueryData(last_processed_date = last_processed_date, project = project, date = today,
                               locations_for_weekly_query = locations_for_weekly_query, model_name = model_name)

  # Ensure there are no duplicate rows
  new_data_distinct <- distinct(new_data)
  rm(new_data)

  print("Running tidyData function on new data")
  new_tidy_data <- tidyData(new_data_distinct)
  rm(new_data_distinct)

  print("Producing graph for faulty, missing, present camera counts")
  produceCameraStatusGraph(df = new_tidy_data, date = today)

  print("Produce PDF per camera per location")
  produceStatusReportPerCameraPDF(df = new_tidy_data, date = today)

  print("Produce PDF per camera per location (long version)")
  produceStatusReportPerCameraPDFLongVersion(df = new_tidy_data, date = today)

  print("Produce PDF heatmap per location")
  produceStatusReportPerLocationPDF(df = new_tidy_data, date = today)

  # If previous imputed data exists then take last 4 weeks to merge onto new data, otherwise just keep the whole data set
  imputed_data_with_unimputed_tail <- getPrevFourWeeksAppendedWithLatest(prev_imputed_data = imputed_data, tidied_data = new_tidy_data)

  rm(new_tidy_data)

  print("Running imputeData function")
  new_imputed_data <- imputeData(df = imputed_data_with_unimputed_tail)
  print("Finished imputeData function")

  rm(imputed_data_with_unimputed_tail)

  # If imputing with last 4 weeks of data, merge the new week but on with the existing imputed data
  if (!is.null(imputed_data)){
    print("Merging newly imputed week back onto existing imputed data")
    data_to_add_imputed <- new_imputed_data[new_imputed_data$date > max(new_imputed_data$date) - num_of_days_to_impute,]
    new_imputed_data <- rbind(imputed_data, data_to_add_imputed)
    rm(data_to_add_imputed)
  }

  rm(imputed_data)

  # save data as "previous data" (.Rda ?)
  print("Saving imputed dataset")
  saveRDS(new_imputed_data, file = imputed_data_filename)

  # perform SEATS
  # export last 7 days data as CSV file with todays date (eg "2020-08-17-export.csv")
  # upload exported CSV to cloud bucket (can just exit andlet command line perform upload)

  # ============================= SETTINGS ==================================

  CAMERA_LOCATIONS <- unique(new_imputed_data$source)

  # Daily time series
  final_data = NULL
  final_data <- lapply(CAMERA_LOCATIONS, FUN = applyAggregateAndSeasonalAdjustmentOuter, df_imputed = new_imputed_data,
                       df_final_data = final_data, trafficTypes = TRAFFIC_TYPES)
  final_data <- as.data.frame(data.table::rbindlist(final_data, idcol = FALSE))
  print("Saving csv")
  write.csv(final_data, file = paste0("outputs/Trafcam_data_", format(today, "%Y%m%d"), ".csv"), quote = FALSE, row.names = FALSE)

  # Output PDF for four week history for cars for each location (graph form)
  final_data$Date <- as.Date(final_data$Date)
  last_processed_date <- max(final_data$Date)
  final_data_subset <- final_data[final_data$Date > last_processed_date - (num_of_days_to_impute + 28), ]
  produceLastFourWeekHistoryDataPDF(df = final_data_subset, date = today)

  rm(final_data_subset)
} else {
    print(paste0("Exiting script early as there is either less than five weeks of data (first run) or no dates between the last processed date ", last_processed_date, " and today ", today))
}
