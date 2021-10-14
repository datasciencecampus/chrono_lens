import csv
import glob
import logging
import os
import pathlib
from collections import defaultdict
from datetime import datetime, timedelta
from functools import partial

from dateutil import rrule
from tqdm import tqdm

from chrono_lens.images.fault_detection import FaultyImageDetector
from chrono_lens.images.newcastle_detector import NewcastleDetector
from chrono_lens.images.static_filter import StaticObjectFilter
from chrono_lens.localhost.io import load_from_json, load_from_binary, load_bgr_image_as_rgb, \
    load_bgr_image_as_rgb_if_not_already_loaded


def discover_cameras(config_path):
    number_of_cameras_read = 0
    number_of_files_read = 0
    camera_tuples_to_process = []
    analysis_config_folder = os.path.join(config_path, 'analyse')
    logging.info(f'Searching folder {analysis_config_folder} for JSON files...')
    for json_filename in glob.glob(os.path.join(analysis_config_folder, '*.json')):
        logging.debug(f'=>  Reading URLs from {json_filename}')
        base_json_name = os.path.basename(json_filename)
        base_name = os.path.splitext(base_json_name)[0]

        camera_names = load_from_json(json_filename)
        number_of_cameras_read += len(camera_names)
        number_of_files_read += 1

        for camera_name in camera_names:
            camera_tuples_to_process.append((base_name, camera_name))
    logging.info(f'...search in folder {analysis_config_folder} for JSON files complete;'
                 f' read in {number_of_cameras_read} image URLs across {number_of_files_read} files.')
    return camera_tuples_to_process


def generate_counts(base_name, sample_date_time, camera_name, download_path,
                    pre_filter_tuples, model_tuple, post_filter_tuples):
    sample_image_file_name = os.path.join(download_path, base_name, f"{sample_date_time:%Y%m%d}",
                                          f"{sample_date_time:%H%M}", f"{camera_name}.jpg")

    previous_date_time = sample_date_time + timedelta(minutes=-10)
    previous_image_file_name = os.path.join(download_path, base_name, f"{previous_date_time:%Y%m%d}",
                                            f"{previous_date_time:%H%M}", f"{camera_name}.jpg")

    next_date_time = sample_date_time + timedelta(minutes=+10)
    next_image_file_name = os.path.join(download_path, base_name, f"{next_date_time:%Y%m%d}",
                                        f"{next_date_time:%H%M}", f"{camera_name}.jpg")

    image_rgb = load_bgr_image_as_rgb(sample_image_file_name)
    missing_image = image_rgb is None

    previous_comparable = True
    next_comparable = True

    current_faulty = False
    if not missing_image:
        current_faulty = image_rgb.shape[0] == 0

    previous_image_rgb = None
    next_image_rgb = None

    for pre_filter_tuple in pre_filter_tuples:
        if not missing_image and not current_faulty:
            faulty_image_filter = pre_filter_tuple[1]

            previous_image_rgb = load_bgr_image_as_rgb_if_not_already_loaded(
                previous_image_rgb, previous_image_file_name)

            next_image_rgb = load_bgr_image_as_rgb_if_not_already_loaded(
                next_image_rgb, next_image_file_name)

            previous_comparable, current_faulty, next_comparable = \
                faulty_image_filter.check_current_faulty_and_next_previous_comparable(
                    previous_image_rgb, image_rgb, next_image_rgb)

    # Now we have a detector, we can create our "schema"
    # Ensure all object types are initialised to 0 - so if not present, we still report
    object_detector = model_tuple[1]

    object_results = {object_type: 0 for object_type in object_detector.detected_object_types()}
    object_results['faulty'] = current_faulty
    object_results['missing'] = missing_image

    if not current_faulty and not missing_image:
        detected_objects = object_detector.detect(image_rgb)

        for post_filter_tuple in post_filter_tuples:
            static_object_filter = post_filter_tuple[1]

            previous_image_rgb = load_bgr_image_as_rgb_if_not_already_loaded(
                previous_image_rgb, previous_image_file_name)

            next_image_rgb = load_bgr_image_as_rgb_if_not_already_loaded(
                next_image_rgb, next_image_file_name)

            detected_objects = static_object_filter.filter_static_objects(
                detected_objects, previous_image_rgb, image_rgb, next_image_rgb,
                previous_comparable, next_comparable)

            if detected_objects is None:
                object_results['faulty'] = True
            else:
                for detected_object in detected_objects:
                    label = detected_object[0].lower().strip()
                    object_results[label] += 1

    return object_results


def load_models(model_blob_name, config_path):
    pre_filter_tuples = []
    post_filter_tuples = []

    model_stages = model_blob_name.split('_')

    object_detector_model_stage_index = 0

    for model_pre_process_index, model_pre_process_name in enumerate(model_stages):
        if model_pre_process_name.startswith('FaultyImageFilter'):
            model_pre_process_configuration_file_name = os.path.join(config_path, "models", model_pre_process_name,
                                                                     "configuration.json")

            model_pre_process_configuration = load_from_json(model_pre_process_configuration_file_name)

            faulty_image_filter = FaultyImageDetector.from_configuration(model_pre_process_configuration)

            pre_filter_tuples.append((model_pre_process_name, faulty_image_filter))
        else:
            # Unknown pre-process stage, assume its the main object counting model;
            # so make a note of the stage and finish
            object_detector_model_stage_index = model_pre_process_index
            break

    object_detector_model_stage_name = model_stages[object_detector_model_stage_index]

    if object_detector_model_stage_name.startswith('Newcastle'):

        model_configuration_file_name = os.path.join(config_path, "models", object_detector_model_stage_name,
                                                     "configuration.json")
        model_configuration = load_from_json(model_configuration_file_name)

        serialized_graph_file_name = os.path.join(config_path, "models", object_detector_model_stage_name,
                                                  model_configuration["serialized_graph_name"])

        serialized_graph = load_from_binary(serialized_graph_file_name)
        minimum_confidence = model_configuration["minimum_confidence"]

        object_detector = NewcastleDetector(serialized_graph=serialized_graph,
                                            minimum_confidence=minimum_confidence)

        model_tuple = (object_detector_model_stage_name, object_detector)

    else:
        raise ValueError(
            f'Model object detector stage is unknown: "{object_detector_model_stage_name}"')

    for model_post_process_name in model_stages[object_detector_model_stage_index + 1:]:
        if model_post_process_name.startswith('StaticObjectFilter'):
            model_post_process_configuration_file_name = os.path.join(config_path, "models", model_post_process_name,
                                                                      "configuration.json")

            model_post_process_configuration = load_from_json(model_post_process_configuration_file_name)

            static_object_filter = StaticObjectFilter.from_configuration(model_post_process_configuration)

            post_filter_tuples.append((model_post_process_name, static_object_filter))

        else:
            raise ValueError(f'Model post-process stage is unknown: "{model_post_process_name}"')

    return pre_filter_tuples, model_tuple, post_filter_tuples


def process_scheduled(config_path, download_path, counts_path):
    os.makedirs(counts_path, exist_ok=True)
    now = datetime.now()
    twenty_minutes_ago = now - timedelta(minutes=20)
    twenty_minutes_ago = twenty_minutes_ago - timedelta(minutes=twenty_minutes_ago.minute % 10,
                                                        seconds=twenty_minutes_ago.second,
                                                        microseconds=twenty_minutes_ago.microsecond)

    # twenty_minutes_ago = datetime(2021, 10, 13, 18, 00, 00)

    date_time_path = os.path.join(f"{twenty_minutes_ago:%Y%m%d}", f"{twenty_minutes_ago:%H%M}")
    logging.info(f'Processing data on {date_time_path}')

    model_configuration_file_name = os.path.join(config_path, 'analyse-configuration.json')
    model_configuration = load_from_json(model_configuration_file_name)

    logging.info(f'Model configuration: "{model_configuration["model_blob_name"]}"')

    camera_tuples_to_process = discover_cameras(config_path)

    logging.info('Loading models...')
    pre_filter_tuples, model_tuple, post_filter_tuples = load_models(model_configuration["model_blob_name"],
                                                                     config_path)
    logging.info('...loaded models')

    logging.info('Preparing CSV...')
    object_count_keys = sorted(model_tuple[1].detected_object_types()) + ['faulty', 'missing']
    sorted_object_count_keys = sorted(object_count_keys)
    column_names = ['date', 'time', 'supplier', 'camera_id'] + sorted_object_count_keys

    csv_folder_name = os.path.join(counts_path, model_configuration["model_blob_name"])
    os.makedirs(csv_folder_name, exist_ok=True)

    csv_file_name = os.path.join(csv_folder_name, f"{twenty_minutes_ago:%Y%m%d}.csv")
    csv_file_exists = pathlib.Path(csv_file_name).is_file()

    if not csv_file_exists:
        with open(csv_file_name, 'a') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(column_names)

    logging.info('...prepared CSV')

    logging.info("Processing images...")
    with open(csv_file_name, 'a') as csv_file:
        writer = csv.writer(csv_file)

        for image_tuple_to_download in tqdm(camera_tuples_to_process, desc='Processing images', unit='images'):
            base_name = image_tuple_to_download[0]
            camera_name = image_tuple_to_download[1]

            object_counts = generate_counts(base_name, twenty_minutes_ago, camera_name, download_path,
                                            pre_filter_tuples, model_tuple, post_filter_tuples)

            field_values = [f"{twenty_minutes_ago:%Y%m%d}", f"{twenty_minutes_ago:%H%M}", base_name, camera_name]
            field_values += [object_counts[key] for key in sorted_object_count_keys]
            writer.writerow(field_values)

    logging.info("...processed images.")


def batch_process(config_path, download_path, counts_path, start_date, end_date):
    os.makedirs(counts_path, exist_ok=True)

    model_configuration_file_name = os.path.join(config_path, 'analyse-configuration.json')
    model_configuration = load_from_json(model_configuration_file_name)

    logging.info(f'Model configuration: "{model_configuration["model_blob_name"]}"')

    camera_tuples_to_process = discover_cameras(config_path)

    logging.info('Loading models...')
    pre_filter_tuples, model_tuple, post_filter_tuples = load_models(model_configuration["model_blob_name"],
                                                                     config_path)
    logging.info('...loaded models')

    dates_to_process = list(rrule.rrule(rrule.DAILY, dtstart=start_date, until=end_date))
    for image_date in tqdm(dates_to_process, desc='Processing images per day', unit='days'):

        logging.debug('Preparing CSV...')
        object_count_keys = sorted(model_tuple[1].detected_object_types()) + ['faulty', 'missing']
        sorted_object_count_keys = sorted(object_count_keys)
        column_names = ['date', 'time', 'supplier', 'camera_id'] + sorted_object_count_keys

        csv_folder_name = os.path.join(counts_path, model_configuration["model_blob_name"])
        os.makedirs(csv_folder_name, exist_ok=True)

        csv_file_name = os.path.join(csv_folder_name, f"{image_date:%Y%m%d}.csv")
        csv_file_exists = pathlib.Path(csv_file_name).is_file()

        # Generate dict of dict of list: "provider" -> "time" -> "processed cameras"
        # [matches later nested loop logic for easy check if a camera has already been analysed at a specified time]
        cameras_per_time_per_provider = defaultdict(partial(defaultdict, list))
        if csv_file_exists:
            with open(csv_file_name, 'r') as csv_file:
                csv_reader = csv.reader(csv_file)
                imported_column_names = csv_reader.__next__()
                if imported_column_names != column_names:
                    raise ValueError(f'Existing CSV file "{csv_file_name}" has different columns to those expected')

                time_column_index = column_names.index('time')
                supplier_column_index = column_names.index('supplier')
                camera_id_column_index = column_names.index('camera_id')

                for csv_row in csv_reader:
                    time_value = csv_row[time_column_index]
                    supplier_value = csv_row[supplier_column_index]
                    camera_id_value = csv_row[camera_id_column_index]

                    cameras_per_time_per_provider[supplier_value][time_value].append(camera_id_value)

        else:
            # Create CSV file with just column headings ready for use
            with open(csv_file_name, 'a') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(column_names)

        logging.debug('...prepared CSV')

        with open(csv_file_name, 'a') as csv_file:
            writer = csv.writer(csv_file)

            datetimes_to_process = list(rrule.rrule(rrule.MINUTELY, interval=10, dtstart=image_date,
                                                    until=image_date + timedelta(hours=23, minutes=50)))

            for image_datetime in datetimes_to_process:

                for image_tuple_to_download in tqdm(camera_tuples_to_process,
                                                    f'Processing images for {image_datetime:%Y%m%d %H%M}',
                                                    unit='images', leave=False):

                    base_name = image_tuple_to_download[0]
                    camera_name = image_tuple_to_download[1]

                    if camera_name in cameras_per_time_per_provider[base_name][f'{image_datetime:%H%M}']:
                        # Already present, so skip - don't reprocess & create a duplicate
                        continue

                    object_counts = generate_counts(base_name, image_datetime, camera_name, download_path,
                                                    pre_filter_tuples, model_tuple, post_filter_tuples)

                    field_values = [f"{image_datetime:%Y%m%d}", f"{image_datetime:%H%M}", base_name, camera_name]
                    field_values += [object_counts[key] for key in sorted_object_count_keys]
                    writer.writerow(field_values)
