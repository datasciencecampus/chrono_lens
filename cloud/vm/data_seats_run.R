# RUN SEATS SCRIPT

# Run function script

source("data_impute_and_seats_functions.R")

# ============================= SETTINGS ==================================
today <- Sys.Date()

TRAFFIC_TYPES <- list("car", "motorcyclist", "bus", "truck", "van", "person", "cyclist", c("person", "cyclist"))

# Read in csv containing locations and start dates
locations_datasets_csv_filename <- "cache/list_of_location_datasets.csv"
locations_in_dataset <- read.csv2(locations_datasets_csv_filename,
sep = ",", check.names = FALSE, stringsAsFactors = FALSE, strip.white = TRUE, na.strings = "")

final_df <- NULL
final_df <- lapply(locations_in_dataset$source, FUN = loadLocationDataAndPerformSeats,
today = today, traffic_type = TRAFFIC_TYPES, final_df = final_df)
final_data <- as.data.frame(data.table::rbindlist(final_df, idcol = FALSE))

print("Saving csv")
write.csv(final_data, file = paste0("outputs/Trafcam_data_", format(today, "%Y%m%d"), ".csv"), quote = FALSE, row.names = FALSE)

# Output PDF for four week history for cars for each location (graph form)
final_data$Date <- as.Date(final_data$Date)
last_processed_date <- max(final_data$Date)
num_of_days_to_impute <- as.numeric(today - (last_processed_date - 7)) - 1
CAMERA_LOCATIONS <- unique(final_data$Location)
final_data_subset <- final_data[final_data$Date > last_processed_date - (num_of_days_to_impute + 28),]
produceLastFourWeekHistoryDataPDF(df = final_data_subset, date = today, camera_locations = CAMERA_LOCATIONS)

rm(final_data_subset)
