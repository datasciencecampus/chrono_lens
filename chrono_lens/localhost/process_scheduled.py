import argparse
import csv
import glob
import json
import logging
import os
import pathlib
import sys
from datetime import datetime, timedelta

import cv2
import numpy
from tqdm import tqdm

import chrono_lens.images.sources.tfl
import chrono_lens.localhost
from chrono_lens.exceptions import ProcessImagesException
from chrono_lens.images.fault_detection import FaultyImageDetector
from chrono_lens.images.newcastle_detector import NewcastleDetector
from chrono_lens.images.static_filter import StaticObjectFilter


def load_from_json(json_file_name):
    with open(json_file_name, 'r') as json_file:
        json_data = json.load(json_file)
    return json_data


def load_from_binary(binary_file_name):
    with open(binary_file_name, 'rb') as binary_file:
        return binary_file.read()


def load_binary_image(image_file_name):
    try:
        raw_image = load_from_binary(image_file_name)
    except FileNotFoundError:
        return None

    raw_image_bytes = numpy.asarray(bytearray(raw_image), dtype=numpy.uint8)
    if raw_image_bytes.size == 0:
        return numpy.zeros((0, 0, 3), numpy.uint8)

    image = cv2.imdecode(raw_image_bytes, 1)  # cv2.CV_LOAD_IMAGE_COLOR)
    if image is None:
        return numpy.zeros((0, 0, 3), numpy.uint8)

    return image


def load_bgr_image_as_rgb(image_file_name):
    image_bgr = load_binary_image(image_file_name)
    if image_bgr is None:
        return None

    if image_bgr.shape[0] == 0:
        return image_bgr

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return image_rgb


def load_bgr_image_as_rgb_if_not_already_loaded(image_rgb, image_file_name):
    if image_rgb is not None:
        return image_rgb

    image_rgb = load_bgr_image_as_rgb(image_file_name)
    if image_rgb is None:
        return None

    if image_rgb.shape[0] == 0:
        return None

    return image_rgb


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
    date_time_path = os.path.join(f"{twenty_minutes_ago:%Y%m%d}", f"{twenty_minutes_ago:%H%M}")
    logging.info(f'Processing data on {date_time_path}')

    model_configuration_file_name = os.path.join(config_path, 'analyse-configuration.json')
    model_configuration = load_from_json(model_configuration_file_name)

    logging.info(f'Model configuration: "{model_configuration["model_blob_name"]}"')

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


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Runs configured model over stored images to generate object counts",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-cf", "--config-folder", default=chrono_lens.localhost.CONFIG_FOLDER,
                        help="Folder where configuration data is stored")

    parser.add_argument("-df", "--download-folder", default=chrono_lens.localhost.DOWNLOAD_FOLDER,
                        help="Folder where image data downloaded")

    parser.add_argument("-cp", "--counts-path", default=chrono_lens.localhost.COUNTS_FOLDER,
                        help="Folder where image counts are stored")

    parser.add_argument("-ll", "--log-level",
                        default=chrono_lens.localhost.DEFAULT_LOG_LEVEL,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Level of detail to report in logs")

    args = parser.parse_args(command_line_arguments)

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(handlers=[handler], level=logging.getLevelName(args.log_level))

    process_scheduled(args.config_folder, args.download_folder, args.counts_path)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
