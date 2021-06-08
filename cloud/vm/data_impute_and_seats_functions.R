# FUNCTIONS USED FOR SEADEC IMPUTATION WITH ALGORITHM MEAN, SQRT TRANSFORMATION, SEATS

# ============================= LOAD PACKAGES ==================================

library(rjdhf) # for SEATS
library(xts) # convert data-frame to xts format
library(dplyr) # data wrangling
library(tidyr) # data wrangling
library(data.table) # data wrangling
library(lubridate) # date manipulation
library(imputeTS) # missing data imputation
library(bigrquery) # BigQuery data access
library(progress) # progress bar
library(ggplot2) # plotting
library(ggExtra) # ggplot theme options
library(viridis) # colour palette
library(stringr) # string manipulation
library(readr) # for reading text from a file

options(scipen = 20) # to prevent large integer numbers changing to scientific format and failing to parse in BigQuery

# ============================= LOAD PACKAGES ==================================


# ============================= FUNCTIONS ==================================

# Function to query bigquery to get the start date and time for each location not in the csv
getStartDateForLocationFromBigQuery <- function(location, locations_and_dates, model_name){
  print("Querying BigQuery to get start dates for each location not found in csv")
  sql <- paste0('
                SELECT date, time
                FROM PROJECT_ID_PLACEHOLDER.detected_objects.', model_name, '
                WHERE date > "2020-01-01"
                AND source = "' , location, '"
                ORDER BY date ASC, time ASC
                LIMIT 1
                ')
  bq_data <- bq_table_download(bq_project_query(project, sql))
  date_time <- as.data.frame(c("source" = location, bq_data))

  if (is.null(locations_and_dates)) {
    locations_and_dates <- date_time
  } else {
    locations_and_dates <- rbind(locations_and_dates, date_time)
  }

  return(locations_and_dates)
}

# Function to download new location data, tidy and impute it if there is at least five weeks data inside bigquery
# If there isn't at least five weeks of data for a location then it will download the latest week in order for QA pdfs to be produced
checkStartDateOfNewLocation <- function(location, locations_and_dates, today, last_processed_date, project, new_locations_data, new_locations_pdf, model_name){
  # Get start date of new location
  start_date_of_new_location <- locations_and_dates[locations_and_dates$source == location, "date"]
  # If there is at least five weeks of data in bigquery then download it up to last_processed_date
  if(start_date_of_new_location <= today - 7*5){
    print(paste0("Start date for ", location, " is at least five weeks before current date"))
    print(paste0("Downloading data for ", location, " from bigquery since ", start_date_of_new_location))
    sql = paste0('
                SELECT *
                FROM `PROJECT_ID_PLACEHOLDER.detected_objects.', model_name, '`
                WHERE date > DATE(', format(start_date_of_new_location - 1, "%Y, %m, %d"), ') and date < DATE(', format(last_processed_date + 1, "%Y, %m, %d"), ')
                AND source = "' , location, '"
                ')
    print(paste0("Loading data for new data source ", location, " from BigQuery"))
      data_for_new_source <- bq_table_download(bq_project_query(project, sql), page_size = 40000)
    print("Finished loading new data from BigQuery")

      # Ensure there are no duplicate rows
    data_for_new_source_distinct <- distinct(data_for_new_source)
    rm(data_for_new_source)

    # Tidy data
    print("Running tidyData function on new data source")
    data_for_new_source_tidy <- tidyData(data_for_new_source_distinct)
    rm(data_for_new_source_distinct)

    if(is.null(new_locations_data)){
      new_locations_data <- data_for_new_source_tidy
    } else {
      new_locations_data <- rbind(new_locations_data, data_for_new_source_tidy)
    }
  } else {
      print(paste0("There are not enough days of data available for ", location, " (five weeks required) so downloading latest week and outputting pdfs"))
    sql = paste0('
                SELECT *
                FROM `PROJECT_ID_PLACEHOLDER.detected_objects.', model_name, '`
                WHERE date > DATE(', format(today - 8, "%Y, %m, %d"), ') and date < DATE(', format(today, "%Y, %m, %d"), ')
                AND source = "' , location, '"
                ')

    print(paste0("Loading data for new data source ", location, " from BigQuery"))
      data_for_new_source <- bq_table_download(bq_project_query(project, sql), page_size = 20000)
    print("Finished loading new data from BigQuery")

      # Ensure there are no duplicate rows
    data_for_new_source_distinct <- distinct(data_for_new_source)
    rm(data_for_new_source)

      # Tidy data
    print("Running tidyData function on new data source")
    data_for_new_source_tidy <- tidyData(data_for_new_source_distinct)
    rm(data_for_new_source_distinct)

      if(is.null(new_locations_pdf)){
      new_locations_pdf <- data_for_new_source_tidy
    } else {
      new_locations_pdf <- rbind(new_locations_pdf, data_for_new_source_tidy)
    }
  }

    return(list(new_locations_data = new_locations_data, new_locations_pdf = new_locations_pdf))
}

# Function to produce and output status report pdf of present, missing, faulty per camera per location (long version)
produceStatusReportPerCameraPDFLongVersion <- function(df, date, filename = ""){
  # Add a new column that is TRUE if camera isn't missing or faulty, FALSE otherwise
  df$Legend <- "present"
  df$Legend <- ifelse(df$missing == TRUE, "missing", df$Legend)
  df$Legend <- ifelse(df$faulty == TRUE, "faulty", df$Legend)
  locations <- sort(unique(df$source))

  # Set name for pdf to be created
  pdf_file_name <- paste0("outputs/Status_report_per_camera_long_version_", format(date, "%Y%m%d"), filename, ".pdf")
  pdf(file = pdf_file_name)
  # Apply produceStatusReportPDFgraphs to each loaction
  sapply(locations, FUN = produceStatusReportPerCameraPDFgraphsLongVersion, df = df)
  dev.off()

  return(print("PDF generated"))
}
produceStatusReportPerCameraPDFgraphsLongVersion <- function(location, df){
  # Select only data for chosen location
  df <- df[df$source == location,]

  counter_df <- data.frame(camera_id = sort(unique(df$camera_id)))
  counter_df <- counter_df %>%
    mutate(counter = 1 + cumsum(c(0,as.numeric(diff(camera_id))!= 0)), # this counter starting at 1 increments for each new dog
           subgroup = as.factor(ceiling(counter/50)))
  df <- left_join(df, counter_df, by = "camera_id")

  dates <- sort(unique(df$date))
  for(i in 1:length(dates)){
    df_plot <- df[df$date == dates[i],]
    # Create date time points for x axis
    datetime_labels <- as.character(seq.POSIXt(from = as.POSIXct(paste0(dates[i], " 00:00:00"), tz = "UTC"),
                                               by = "1 hours", length.out = 24))

    for (j in 1:length(unique(df_plot$subgroup))) {
      df_plot %>%
        filter(subgroup == j) -> plot_data

      p <- ggplot(data = plot_data) +
        geom_point(aes(x = as.character(datetime), y = camera_id, colour = Legend), shape = 15) +
        scale_colour_manual(values = c("present" = "#F0E442", "faulty" = "#0072B2", "missing" = "#D55E00")) +
        scale_x_discrete(breaks = datetime_labels) +
        labs(title = paste0(location), " camera status", x = "Date", y = "Camera") +
        theme_bw() +
        theme(plot.title = element_text(size = 12)) +
        theme(axis.text.y = element_text(size = 8)) +
        theme(axis.text.x = element_text(size = 8)) +
        theme(axis.title.y = element_text(size = 10)) +
        theme(axis.title.x = element_text(size = 10)) +
        theme(axis.text.x = element_text(angle = 90, hjust = 0.5))

      #Shrink the plot so there is less space between the y axis if number of cameras on plot is less than 25
      if(length(unique(plot_data$camera_id)) < 20){
        p <- p + coord_fixed(ratio = 10)
      }
      print(p)
    }
  }
}

# Functions to output PDF for last four weeks data for cars for each location (graph form)
produceLastFourWeekHistoryDataPDF <- function(df, date){
  pdf_file_name <- paste0("outputs/Four_week_history_", format(date, "%Y%m%d"), ".pdf")
  pdf(file = pdf_file_name)
  sapply(CAMERA_LOCATIONS, FUN = produceLastFourWeekHistoryDataPDFgraphs, df = df)
  dev.off()
  return(print("PDF generated"))
}
produceLastFourWeekHistoryDataPDFgraphs <- function(location , df){
  plot_data <- df[df$Type == "car" & df$Location == location,]
  plot_data <- plot_data %>% pivot_longer(!c(Location, Type, Date), names_to = "Data_type", values_to = "Value")

  p <- ggplot(data = plot_data, aes(x = Date, y = Value, group = Data_type)) +
    geom_line(aes(linetype = Data_type, colour = Data_type), size = 1) +
    scale_linetype_manual(values = c("solid", "dotted", "twodash")) +
    scale_colour_manual(values = c("#000000", "#F0E442", "#56B4E9")) +
    scale_x_date(breaks = unique(plot_data$Date)) +
    labs(title = paste0(location, " - car"), x = "", y = "Value") +
    theme_classic() +
    theme(plot.title = element_text(size = 14)) +
    theme(axis.text.y = element_text(size = 8)) +
    theme(axis.text.x = element_text(size = 8)) +
    theme(axis.title.y = element_text(size = 10)) +
    theme(axis.title.x = element_text(size = 10)) +
    theme(axis.text.x = element_text(angle = 90, hjust = 0.5))

  print(p)
}

# Function to aggregate and seasonally adjust newly imputed data (outer loop)
applyAggregateAndSeasonalAdjustmentOuter <- function(camera, df_imputed, df_final_data, trafficTypes){
  print(paste0("Running aggregateData for ", camera))
  df_daily <- aggregateData(df = df_imputed, camLocation = camera)

  final_daily = NULL
  final_daily <- lapply(trafficTypes, FUN = applyAggregateAndSeasonalAdjustmentInner, df = df_daily,
                        final_df = final_daily, camera = camera)

  final_daily <- as.data.frame(data.table::rbindlist(final_daily, idcol = FALSE))

  if(is.null(df_final_data)){
    df_final_data <- final_daily
  } else {
    df_final_data <- rbind(df_final_data, final_daily)
  }

  return(df_final_data)
}

# Function to aggregate and seasonally adjust newly imputed data (inner loop)
applyAggregateAndSeasonalAdjustmentInner <- function(traf_type, df, final_df, camera){
  print(paste0("Running timeseries for ", traf_type))

  result_daily <- timeseriesDaily(df = df, trafficType = traf_type)

  if(length(traf_type) == 2){
    traf_name <- paste0(traf_type[1],"_", traf_type[2])
  } else {
    traf_name <- traf_type
  }

  cols_to_bind_daily <- data.frame("Location" = rep(camera, nrow(result_daily)), "Type" = rep(traf_name, nrow(result_daily)))

  result_daily <- cbind(cols_to_bind_daily, result_daily)

  if(is.null(final_df)){
    final_df <- result_daily
  } else {
    final_df <- rbind(final_df, result_daily)
  }
  return(final_df)
}

# Function to produce and output status report pdf of present, missing, faulty per camera per location
produceStatusReportPerCameraPDF <- function(df, date, filename = ""){
  # Add a new column that is TRUE if camera isn't missing or faulty, FALSE otherwise
  df$Legend <- "present"
  df$Legend <- ifelse(df$missing == TRUE, "missing", df$Legend)
  df$Legend <- ifelse(df$faulty == TRUE, "faulty", df$Legend)
  locations <- sort(unique(df$source))

  # Set name for pdf to be created
  pdf_file_name <- paste0("outputs/Status_report_per_camera_", format(date, "%Y%m%d"), filename, ".pdf")
  pdf(file = pdf_file_name)
  # Apply produceStatusReportPDFgraphs to each loaction
  sapply(locations, FUN = produceStatusReportPerCameraPDFgraphs, df = df)
  dev.off()

  return(print("PDF generated"))
}
produceStatusReportPerCameraPDFgraphs <- function(location, df){
  # Create date time points for x axis
  dateMin <- min(df$date)
  dateMax <- max(df$date)
  time <- format(seq.POSIXt(from = as.POSIXct(paste0(dateMin, " 00:00:00"), tz = "UTC"),
                            by = "12 hours", length.out = (as.numeric(dateMax - dateMin) + 1) * 2), "%H:%M:%S")
  date <- as.Date(seq.POSIXt(from = as.POSIXct(paste0(dateMin, " 00:00:00"), tz = "UTC"),
                             by = "12 hours", length.out = (as.numeric(dateMax - dateMin) + 1) * 2))
  datetime_labels <- as.character(seq.POSIXt(from = as.POSIXct(paste0(dateMin, " 00:00:00"), tz = "UTC"),
                                             by = "12 hours", length.out = (as.numeric(dateMax - dateMin) + 1) * 2))
  # Select only data for chosen location
  df <- df[df$source == location,]

  counter_df <- data.frame(camera_id = sort(unique(df$camera_id)))
  counter_df <- counter_df %>%
    mutate(counter = 1 + cumsum(c(0,as.numeric(diff(camera_id))!= 0)), # this counter starting at 1 increments for each new dog
           subgroup = as.factor(ceiling(counter/50)))
  df <- left_join(df, counter_df, by = "camera_id")

  for (i in 1 : length(unique(df$subgroup))) {
    df %>%
      filter(subgroup == i) -> plot_data

    p <- ggplot(data = plot_data) +
      geom_point(aes(x = as.character(datetime), y = camera_id, colour = Legend), shape = 15) +
      scale_colour_manual(values = c("present" = "#F0E442", "faulty" = "#0072B2", "missing" = "#D55E00")) +
      scale_x_discrete(breaks = datetime_labels) +
      labs(title = paste0(location), " camera status", x = "Date", y = "Camera") +
      theme_bw() +
      theme(plot.title = element_text(size = 14)) +
      theme(axis.text.y = element_text(size = 8)) +
      theme(axis.text.x = element_text(size = 8)) +
      theme(axis.title.y = element_text(size = 10)) +
      theme(axis.title.x = element_text(size = 10)) +
      theme(axis.text.x = element_text(angle = 90, hjust = 0.5))

    # Shrink the plot so there is less space between the y axis if number of cameras on plot is less than 25
    if(length(unique(plot_data$camera_id)) < 25){
      p <- p + coord_fixed(ratio = 50)
    }
    print(p)
  }
}

# Function to produce and output status report pdf of present, missing, faulty per location
produceStatusReportPerLocationPDF <- function(df, date, filename = ""){
  # Add a new column that is TRUE if camera isn't missing or faulty, FALSE otherwise
  df$present <- ifelse(df$missing == FALSE & df$faulty == FALSE, TRUE, FALSE)
  locations <- sort(unique(df$source))

  # Set name for pdf to be created
  pdf_file_name <- paste0("outputs/Status_report_per_location_", format(date, "%Y%m%d"), filename, ".pdf")
  pdf(file = pdf_file_name)
  # Apply produceStatusReportPDFgraphs to each loaction
  sapply(locations, FUN = produceStatusReportPerLocationPDFgraphs, df = df)
  dev.off()

  return(print("PDF generated"))
}
produceStatusReportPerLocationPDFgraphs <- function(location, df){
  # Select location data
  df <- df[df$source == location,]

  # Aggregate faulty, missing, present counts by datetime
  plot_data <- aggregate(df[, c("faulty", "missing", "present")], by = list(datetime = floor_date(df$datetime, unit = "hour")), FUN = sum)

  # Add total column
  plot_data <- plot_data %>% mutate(total = faulty + missing + present)

  # Transform the data so that there are 3 columns - datetime, status, count
  plot_data <- plot_data %>% pivot_longer(!datetime, names_to = "status", values_to = "count")
  plot_data <- plot_data %>% mutate(day = date(plot_data$datetime),
                                    hour = hour(plot_data$datetime))

  p <- ggplot(plot_data, aes(day, hour, fill = count)) +
    geom_tile(color = "white", size = 0.1) +
    scale_fill_viridis(name = paste0("Count"), option = "C") +
    facet_grid(~ status) +
    scale_y_continuous(trans = "reverse", breaks = unique(plot_data$hour)) +
    scale_x_date(breaks = unique(plot_data$day)) +
    labs(title = paste0(location), x = "", y = "Hour Commencing") +
    theme_minimal(base_size = 10) +
    theme(legend.position = "bottom") +
    theme(plot.title = element_text(size = 14, hjust = 0.5)) +
    theme(axis.title = element_text(size = 12)) +
    theme(axis.text = element_text(size = 10)) +
    theme(axis.text.x = element_text(angle = 90, hjust = 0.5)) +
    theme(legend.title = element_text(size = 12)) +
    theme(legend.text = element_text(size = 8)) +
    theme(strip.background = element_rect(colour = "white")) +
    theme(strip.text = element_text(size = 12)) + # present, faulty, missing headings
    theme(axis.ticks = element_blank()) +
    removeGrid()
  print(p)
}

# Function to produce and output percentage stacked barchart showing missing, faulty, present counts per location
produceCameraStatusGraph <- function(df, date, filename = ""){
  # Add a new column that is TRUE if camera isn't missing or faulty, FALSE otherwise
  df$present <- ifelse(df$missing == FALSE & df$faulty == FALSE, TRUE, FALSE)

  num_of_cameras <- aggregate(data=df, camera_id ~ source, function(x) length(unique(x)))
  num_of_cameras$source_camera <- paste0(num_of_cameras$source, "; cameras: ", num_of_cameras$camera_id)

  df <- left_join(df, num_of_cameras[,c("source", "source_camera")], by = "source")
  # Aggregate faulty, missing, present counts by location
  to_plot <- aggregate(df[, c("faulty", "missing", "present")], by = list(location = df$source_camera), FUN = sum)

  # Transform the data so that there are 3 columns - location, status, count
  to_plot <- to_plot %>% pivot_longer(!location, names_to = "status", values_to = "count")

  # Plot percentage stacked barchart
  status_plot <- ggplot(to_plot, aes(fill = status, y = count, x = location)) +
    geom_bar(position = "fill", stat = "identity") +
    scale_fill_viridis(discrete = T) +
    ggtitle(paste0("Camera status week ending ", date-1)) +
    xlab("") +
    ylab("Percentage of processed images") +
    scale_y_continuous(labels = scales::percent_format()) +
    scale_x_discrete(labels = function(x) stringr::str_wrap(x, width = 10))

  ggsave(paste0("outputs/status_report_", format(date, "%Y%m%d"), filename,".png"), plot = status_plot, width = 11.5, height = 6.5)
}

# Function to loading existing imputed data if it exists, else it returns a NULL dataset
loadExistingImputedData <- function(imputed_filename){
  # Check if previous imputed data Rda is available
  if( file.exists(imputed_filename) )
  {
    # If so - load it, find last date in it
    print("Loading existing data")
    imputed_data = readRDS(file = imputed_filename)
    # Ensure date and datetime column are the right type
    imputed_data$date <- as.Date(imputed_data$date)
    imputed_data$datetime <- as.POSIXct(imputed_data$datetime, tz = "UTC")
    last_processed_date = as.Date(max(imputed_data$date))
  } else {
    # If not - set imputed_data to NULL and set last date as "2000-01-01"
    print("No existing data so setting to NULL")
    imputed_data = NULL
    last_processed_date = as.Date("2020-01-01")
    #  last_processed_date = as.Date("2020-07-01")
  }
  returnList <- list("imputed_data" = imputed_data, "last_processed_date" = last_processed_date)
  return(returnList)
}

# Function to get data from SQL, after "last date" and before "today"
loadBigQueryData <- function(last_processed_date, project, date, locations_for_weekly_query, model_name){
  today <- date
  sql = paste0("
              SELECT *
              FROM `PROJECT_ID_PLACEHOLDER.detected_objects.", model_name, "`
              WHERE date > DATE(", format(last_processed_date, "%Y, %m, %d"), ") and date < DATE(", format(today, "%Y, %m, %d"), ")
              AND source IN ('" , paste(locations_for_weekly_query, collapse = "','"), "')
              ")
  print(paste0("Loading new data from BigQuery after ", format(last_processed_date, "%Y-%m-%d"), " and before ", format(today, "%Y-%m-%d")))
  bq_data <- bq_table_download(bq_project_query(project, sql), page_size = 20000)
  print("Finished loading new data from BigQuery")

  return(bq_data)
}

# Function to get the previous four weeks from the latest imputed dataset (if it exists)
getPrevFourWeeksAppendedWithLatest <- function(prev_imputed_data, tidied_data){
  if (is.null(prev_imputed_data))
  {
    print("No existing data so skipping merge")
    imputed_data_with_unimputed_tail <- tidied_data
  } else {
    # Take previous 4 weeks
    imputed_subset <- prev_imputed_data[prev_imputed_data$date >= max(prev_imputed_data$date) - (7 * 4 - 1) & prev_imputed_data$date <= max(prev_imputed_data$date),]
    # Join on the new week of data
    print("Merging new data to old")
    imputed_data_with_unimputed_tail <- rbind(imputed_subset, tidied_data)
  }

  return(imputed_data_with_unimputed_tail)
}

# Function to clean and prepare data
tidyData <- function(df){

  # Convert time into type datetime and change into format hms
  # Create column with date and time together and convert it to type posixct
  # Drop new column time_temp
  tidied_df <- df %>%
    mutate(time_temp = as_datetime(as.numeric(time))) %>%
    mutate(time = paste(hour(time_temp), minute(time_temp), second(time_temp), sep = ":")) %>%
    mutate(datetime = paste0(date, "", time)) %>%
    mutate(datetime = as.POSIXct(datetime, tz = "UTC")) %>%
    #select(c(-source, -time, -date, -time_temp))
    select(-time_temp)

  # Ensure columns to numeric
  tidied_df[,c("bus", "car", "cyclist", "motorcyclist", "person", "truck", "van")] <-
    lapply(tidied_df[,c("bus", "car", "cyclist", "motorcyclist", "person", "truck", "van")], as.numeric)

  # Convert missing or faulty to NA
  tidied_df$bus <- ifelse(tidied_df$missing == TRUE | tidied_df$faulty == TRUE, NA, tidied_df$bus)
  tidied_df$car <- ifelse(tidied_df$missing == TRUE | tidied_df$faulty == TRUE, NA, tidied_df$car)
  tidied_df$cyclist <- ifelse(tidied_df$missing == TRUE | tidied_df$faulty == TRUE, NA, tidied_df$cyclist)
  tidied_df$motorcyclist <- ifelse(tidied_df$missing == TRUE | tidied_df$faulty == TRUE, NA, tidied_df$motorcyclist)
  tidied_df$person <- ifelse(tidied_df$missing == TRUE | tidied_df$faulty == TRUE, NA, tidied_df$person)
  tidied_df$truck <- ifelse(tidied_df$missing == TRUE | tidied_df$faulty == TRUE, NA, tidied_df$truck)
  tidied_df$van <- ifelse(tidied_df$missing == TRUE | tidied_df$faulty == TRUE, NA, tidied_df$van)

  tidied_df$cameraloc <- paste(tidied_df$source, tidied_df$camera_id, sep = "_")

  # Reducing weight of multiple views in NETravelData-images
  # Get unique camera ids from dataset
  unique_camera_id <- unique(tidied_df$cameraloc)

  # Create a new data frame with unique camera ids and empty column for housing how many views a camera has
  ne_camera_ids <- as.data.frame(matrix(0, ncol = 2, nrow = length(unique_camera_id)))
  colnames(ne_camera_ids) <- c("cameraloc", "view_count")
  ne_camera_ids$cameraloc <- unique_camera_id

  for (id in ne_camera_ids$cameraloc) {
    # If view and netraveldata are in the camera id id then take a substring of the id (remove the last 2 digits)
    # count how many times that camera occurs in unique camera ids
    if (grepl("View", id, fixed = TRUE) & grepl("NETravelData", id, fixed = TRUE)){
      temp_id <- substr(id, start = 1, stop = nchar(id)-2)
      view_count <- sum(grepl(temp_id, unique_camera_id, fixed = TRUE) == TRUE)
      ne_camera_ids[ne_camera_ids$cameraloc == id, "view_count"] <- view_count
    } else {
      # Assign view_count to be 1 as camera id has no views other than itself
      ne_camera_ids[ne_camera_ids$cameraloc == id, "view_count"] <- 1
    }
  }

  # Join view_count back on to original data by cameraloc
  tidied_df <- left_join(tidied_df, ne_camera_ids, by = "cameraloc")
  tidied_df <- as.data.frame(tidied_df)

  # Divide traffic values by view_count
  tidied_df[,c("car", "motorcyclist", "bus", "truck", "van", "person", "cyclist")] <-
    tidied_df[,c("car", "motorcyclist", "bus", "truck", "van", "person", "cyclist")] / tidied_df[,"view_count"]

  tidied_df <- tidied_df %>%
    select(-c(view_count))

  return(tidied_df)
}

# Function to perform imputation
imputeData <- function(df, last_imputed_date = NULL){

  # Convert data frame to xts
  df <- xts(df, order.by = df$datetime)

  cols_to_impute <- c("bus", "car", "cyclist", "motorcyclist", "person", "truck", "van")

  # Perform seadec imputation with algorithm mean, frequency 1008 (6 in hour * 24 in day * 7 in week)
  cameralocs <- unique(df$cameraloc)
  num_cameralocs <- length(cameralocs)
  pb <- progress_bar$new(format = "[:bar] :current/:total (:percent) in :elapsed eta: :eta", total = num_cameralocs)
  # if all rows after "last_imputed_date" do not contain NAs or whatnot, no need to impute - skip camera!
  for(cameraloc in cameralocs){
    #print(cameraloc)
    pb$tick()
    for(column in cols_to_impute){
      df[df$cameraloc == cameraloc, column] <- tryCatch({
        na_seadec(ts(as.numeric(df[df$cameraloc == cameraloc, column]), start = 1, frequency = 1008), algorithm = "mean")
      }, warning = function(w) {
        print(paste0(cameraloc, ":", column, " produced warning: ", w))
        print("...returning camera without imputation, set to 0")
        return(df[df$cameraloc == cameraloc, column] <- 0)
      }, error = function(e) {
        print(paste0(cameraloc, ":", column, " produced error: ", e))
        print("...returning camera without imputation, set to 0")
        return(df[df$cameraloc == cameraloc, column] <- 0)
        #return(df[df$cameraloc == cameraloc, column])
      }, finally = {
        #cleanup-code
      })
    }
  }

  # Convert xts back to data frame
  df <- as.data.frame(df, stringsAsFactors = FALSE)

  # Ensure columns are numeric
  df[,c("bus", "car", "cyclist", "motorcyclist", "person", "truck", "van")] <-
    lapply(df[,c("bus", "car", "cyclist", "motorcyclist", "person", "truck", "van")], as.numeric)

  # Added to set any negative values to 0
  df[,c("bus", "car", "cyclist", "motorcyclist", "person", "truck", "van")][df[,c("bus", "car", "cyclist", "motorcyclist", "person", "truck", "van")] < 0] <- 0

  df$date <- as.Date(df$date)
  return(df)
}

# Function to aggregate data from every 10 minutes to daily
aggregateData <- function(df, camLocation){

  # Create datetime column
  # Drop columns faulty and missing
  df <- df %>%
    filter(source == camLocation) %>%
    mutate(date = as.Date(date)) %>%
    mutate(datetime = paste0(date, " ", time)) %>%
    mutate(datetime = as.POSIXct(datetime, tz = "UTC")) %>%
    select(-c(missing, faulty, camera_id, date, time, source))

  dates <- as.Date(df$datetime)

  # Replace datatime column with new converted dates
  df$datetime <- as.character(dates)
  rm(dates)

  # Aggregate cameras into one
  data_cam_sum <- aggregate(df[,c("bus", "car", "cyclist", "motorcyclist", "person", "truck", "van")],
                            by = list(datetime = df$datetime) , FUN = sum)

  # Convert date column into posixc or date
  dates <- as.Date(data_cam_sum$datetime)

  returnList <- list("dataset" = data_cam_sum, "dates" = dates)
  return(returnList)
}

# Function to check if object is empty
isEmpty <- function(x) {
  return(identical(x, numeric(0)))
}

# Function to get outlier from SEATS
getOutliers <- function(dfCleaning, dfY){
  if(!isEmpty(dfCleaning$model$b)){
    pre_adj <- xts(t(matrix(rep(dfCleaning$model$b, length(dfY)), ncol = length(dfY))) * dfCleaning$model$X, order.by = time(dfY))
    out_jd <- dfCleaning$model$variables
    out_names <- paste0(substr(out_jd, 1, 3), time(dfY)[as.numeric(substr(out_jd, 4, nchar(out_jd)))])
  } else {
    pre_adj <- xts(t(matrix(0L, nrow = 1, ncol =length(dfY))), order.by = time(dfY))
    out_names <- "none"
  }

  colnames(pre_adj) <- c(out_names)
  outs <- pre_adj

  # Select LS
  ls_outs <- outs[, substr(out_names, 1, 2) == "LS"]
  # Select AO
  ao_outs <- outs[, substr(out_names, 1, 2) == "AO"]
  # Select WO
  wo_outs <- outs[, substr(out_names, 1, 2) == "WO"]

  # Apply row sum
  ls_ts <- xts(apply(ls_outs, 1, sum), order.by = time(dfY))
  aowo_ts <- xts(apply(ao_outs, 1, sum) + apply(wo_outs, 1, sum), order.by = time(dfY))

  returnList <- list("ls_ts" = ls_ts, "aowo_ts" = aowo_ts)
  return(returnList)
}

# Function to perform SEATS on daily data
timeseriesDaily <- function(df, trafficType){
  data_to_use <- df$dataset
  dates <- df$dates

  if(length(trafficType) == 2){
    y_trafficType <- rowSums(data_to_use[, trafficType])
    traf_name <- paste0(trafficType[1],"_", trafficType[2])
  } else {
    y_trafficType <- data_to_use[, trafficType]
    traf_name <- trafficType
  }

  # Order y by dates
  y_trafficType_xts <- xts(y_trafficType, order.by = dates)
  colnames(y_trafficType_xts) <- traf_name

  y_orig <- y_trafficType_xts
  # Square root y
  y <- sqrt(y_trafficType_xts)
  # Perform fractional airline estimation with period 7 (as each observation is a daily), critical values 4
  cleaning <- rjdhf::fractionalAirlineEstimation(y,period=c(7),outliers = c("ao","ls","wo"), criticalValue = 4)

  # Calculate t value
  tval_b <- cleaning$model$b/ sqrt(diag(cleaning$model$bcov))
  data.frame(cleaning$model$variables, tval_b)

  y_clean <- cleaning$model$linearized

  # Perform fractional airline decomposition with period 24
  c1 <- rjdhf::fractionalAirlineDecomposition(y_clean, period=7)

  # Get outliers ao, ls, wo
  outliers <- getOutliers(dfCleaning = cleaning, dfY = y)
  ls_ts <- outliers$ls_ts
  aowo_ts <- outliers$aowo_ts

  sa <- (xts(c1$decomposition$sa, order.by = time(y)) + ls_ts + aowo_ts)^2
  tr <- (xts(c1$decomposition$t, order.by = time(y)) + ls_ts)^2
  ir <- xts(c1$decomposition$i, order.by = time(y))
  s <- xts(c1$decomposition$s, order.by = time(y))

  returnList <- list("sa" = round(sa), "tr" = round(tr), "y" = round(y_orig))
  temp <- merge(returnList$sa, returnList$tr, returnList$y)
  temp_index <- as.data.frame(index(temp))
  temp <- as.data.frame(temp)
  to_return <- cbind(temp_index, temp)
  colnames(to_return) <- c("Date", "SA", "Trend", "Original")

  return(to_return)
}

# ============================= FUNCTIONS ==================================
