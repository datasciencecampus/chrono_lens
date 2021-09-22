import datetime
import json
import os

import google.cloud.storage
from opentelemetry import trace

from dsc_lib.call_handling import extract_request_field, extract_fields_from_image_blob, image_blob_name_from_fields
from dsc_lib.error_handling import report_exception
from dsc_lib.gcloud.logging import setup_logging_and_trace
from dsc_lib.images.fault_detection import FaultyImageDetector
from dsc_lib.images.loader import load_bgr_image_from_blob_as_rgb
from dsc_lib.images.newcastle_detector import NewcastleDetector
from dsc_lib.images.static_filter import StaticObjectFilter

"""
Example JSON call:

{
    "image_blob_name": "Durham-images/20200519/0810/sd_durhamcouncil06.jpg",
    "model_blob_name": "NewcastleV0"
}

{
    "image_blob_name": "Durham-images/20200519/0810/sd_durhamcouncil06.jpg",
    "model_blob_name": "NewcastleV0_StaticObjectFilterV0"
}

{
    "image_blob_name": "Northern-Ireland-images/20200516/0640/10.jpg",
    "model_blob_name": "FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0"
}
"""

setup_logging_and_trace()

# Objects we can reuse between calls
object_detector = None
object_detector_model_name = None

static_object_filter = None
static_object_filter_name = None

faulty_image_filter = None
faulty_image_filter_name = None

# Use same google client each time - save boot-up overhead per call
client = google.cloud.storage.Client()

data_bucket_name = os.environ.get('DATA_BUCKET_NAME')  # Built-in env var
try:
    data_bucket = client.get_bucket(data_bucket_name)
except google.cloud.exceptions.NotFound:
    data_bucket = None

models_bucket_name = os.environ.get('MODELS_BUCKET_NAME')  # Built-in env var
try:
    model_bucket = client.get_bucket(models_bucket_name)
except google.cloud.exceptions.NotFound:
    model_bucket = None


def count_objects(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    tracer = trace.get_tracer(__name__)

    image_blob_name = None
    model_blob_name = None

    try:
        with tracer.start_as_current_span("count_objects"):
            if data_bucket_name is None:
                raise RuntimeError('"DATA_BUCKET_NAME" not defined as an environment variable')

            if models_bucket_name is None:
                raise RuntimeError('"MODELS_BUCKET_NAME" not defined as an environment variable')

            if data_bucket is None:
                raise RuntimeError(f'Google bucket name "{data_bucket_name}" (used for "data_bucket_name")'
                                   ' failed to open a bucket')

            if model_bucket is None:
                raise RuntimeError(f'Google bucket name "{models_bucket_name}" (used for "models_bucket_name")'
                                   ' failed to open a bucket')

            image_blob_name = extract_request_field(request, 'image_blob_name')
            model_blob_name = extract_request_field(request, 'model_blob_name')

            image_source, current_date_time, camera_id = extract_fields_from_image_blob(image_blob_name)

            previous_date_time = current_date_time + datetime.timedelta(minutes=-10)
            previous_image_blob_name = image_blob_name_from_fields(image_source, previous_date_time, camera_id)

            next_date_time = current_date_time + datetime.timedelta(minutes=+10)
            next_image_blob_name = image_blob_name_from_fields(image_source, next_date_time, camera_id)

            with tracer.start_as_current_span("Loading current image from blob"):
                image_rgb = load_bgr_image_from_blob_as_rgb(image_blob_name, data_bucket)
                missing_image = image_rgb is None

            previous_comparable = True
            next_comparable = True

            current_faulty = False
            if not missing_image:
                current_faulty = image_rgb.shape[0] == 0

            previous_image_rgb = None
            next_image_rgb = None

            global object_detector, object_detector_model_name
            global static_object_filter, static_object_filter_name
            global faulty_image_filter, faulty_image_filter_name

            model_stages = model_blob_name.split('_')

            object_detector_model_stage_index = 0

            with tracer.start_as_current_span("Pre-processing filter"):
                for model_pre_process_index, model_pre_process_name in enumerate(model_stages):
                    if model_pre_process_name.startswith('FaultyImageFilter'):
                        if faulty_image_filter_name != model_pre_process_name:
                            model_pre_process_configuration_blob = model_bucket.blob(
                                model_pre_process_name + '/configuration.json')
                            model_pre_process_configuration = json.loads(
                                model_pre_process_configuration_blob.download_as_string())
                            faulty_image_filter = FaultyImageDetector.from_configuration(
                                model_pre_process_configuration)
                            faulty_image_filter_name = model_pre_process_name

                        if not missing_image and not current_faulty:
                            with tracer.start_as_current_span("Loading previous image from blob"):
                                previous_image_rgb = load_bgr_image_from_blob_as_rgb_if_not_already_loaded(
                                    previous_image_rgb, previous_image_blob_name, data_bucket)

                            with tracer.start_as_current_span("Loading next image from blob"):
                                next_image_rgb = load_bgr_image_from_blob_as_rgb_if_not_already_loaded(
                                    next_image_rgb, next_image_blob_name, data_bucket)

                            previous_comparable, current_faulty, next_comparable = \
                                faulty_image_filter.check_current_faulty_and_next_previous_comparable(
                                    previous_image_rgb, image_rgb, next_image_rgb)
                    else:
                        object_detector_model_stage_index = model_pre_process_index
                        break

            object_detector_model_stage_name = model_stages[object_detector_model_stage_index]

            with tracer.start_as_current_span("Initiating detector"):
                if object_detector_model_name != object_detector_model_stage_name:
                    if object_detector_model_stage_name.startswith('Newcastle'):

                        if object_detector is not None:
                            object_detector.close()

                        model_configuration_blob = model_bucket.blob(
                            object_detector_model_stage_name + '/configuration.json')
                        model_configuration_json = model_configuration_blob.download_as_string()
                        model_configuration = json.loads(model_configuration_json)
                        serialized_graph_blob = model_bucket.blob(
                            f'{object_detector_model_stage_name}/{model_configuration["serialized_graph_name"]}')
                        with tracer.start_as_current_span("Loading model from blob"):
                            serialized_graph = serialized_graph_blob.download_as_string()
                        minimum_confidence = model_configuration["minimum_confidence"]

                        with tracer.start_as_current_span("Constructing detector"):
                            object_detector = NewcastleDetector(serialized_graph=serialized_graph,
                                                                minimum_confidence=minimum_confidence)

                        object_detector_model_name = object_detector_model_stage_name
                    else:
                        raise ValueError(
                            f'Model object detector stage is unknown: "{object_detector_model_stage_name}"')

            # Now we have a detector, we can create our "schema"
            # Ensure all object types are initialised to 0 - so if not present, we still report
            object_results = {object_type: 0 for object_type in object_detector.detected_object_types()}
            object_results['faulty'] = current_faulty
            object_results['missing'] = missing_image

            if not current_faulty and not missing_image:
                with tracer.start_as_current_span("Detecting objects"):
                    detected_objects = object_detector.detect(image_rgb)

                with tracer.start_as_current_span("`Post-processing filter"):
                    for model_post_process_name in model_stages[object_detector_model_stage_index + 1:]:
                        if model_post_process_name.startswith('StaticObjectFilter'):
                            if static_object_filter_name != model_post_process_name:
                                model_post_process_configuration_blob = model_bucket.blob(
                                    model_post_process_name + '/configuration.json')
                                model_post_process_configuration = json.loads(
                                    model_post_process_configuration_blob.download_as_string())
                                static_object_filter = StaticObjectFilter.from_configuration(
                                    model_post_process_configuration)
                                static_object_filter_name = model_post_process_name

                            with tracer.start_as_current_span("Loading previous image from blob"):
                                previous_image_rgb = load_bgr_image_from_blob_as_rgb_if_not_already_loaded(
                                    previous_image_rgb, previous_image_blob_name, data_bucket)

                            with tracer.start_as_current_span("Loading next image from blob"):
                                next_image_rgb = load_bgr_image_from_blob_as_rgb_if_not_already_loaded(
                                    next_image_rgb, next_image_blob_name, data_bucket)

                            detected_objects = static_object_filter.filter_static_objects(
                                detected_objects, previous_image_rgb, image_rgb, next_image_rgb,
                                previous_comparable, next_comparable
                            )
                        else:
                            raise ValueError(f'Model post-process stage is unknown: "{model_post_process_name}"')

                if detected_objects is None:
                    object_results['faulty'] = True
                else:
                    for detected_object in detected_objects:
                        label = detected_object[0].lower().strip()
                        object_results[label] += 1

            return_json = {'STATUS': 'Processed', 'results': object_results}
            return json.dumps(return_json)

    except Exception as e:
        return report_exception(e,
                                {'data_bucket_name': data_bucket_name,
                                 'image_blob_name': image_blob_name,
                                 'models_bucket_name': models_bucket_name,
                                 'model_blob_name': model_blob_name},
                                request=request)


def load_bgr_image_from_blob_as_rgb_if_not_already_loaded(image_rgb, image_blob_name, image_bucket):
    if image_rgb is not None:
        return image_rgb

    image_rgb = load_bgr_image_from_blob_as_rgb(image_blob_name, image_bucket)
    if image_rgb is None:
        return None

    if image_rgb.shape[0] == 0:
        return None

    return image_rgb
