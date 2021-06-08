import json
import logging
import os

from opentelemetry import trace

from dsc_lib.call_handling import extract_request_field
from dsc_lib.error_handling import report_exception
from dsc_lib.gcloud.async_functions import run_cloud_function_async_with_parameter_list
from dsc_lib.gcloud.logging import setup_logging_and_trace

setup_logging_and_trace()

gcp_region = os.environ.get('FUNCTION_REGION', '')  # Built-in env var
gcp_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var

count_objects_endpoint = f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/count_objects'
logging.info(f'Using count_objects_endpoint: "{count_objects_endpoint}"')

bigquery_write_endpoint = f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/bigquery_write'
logging.info(f'Using bigquery_write_endpoint: "{bigquery_write_endpoint}"')


def run_model_on_image(request):
    """
    Example JSON call:

{
    "data_blob_name": "Durham-images/20200510/0010/sd_durhamcouncil09.jpg",
    "model_blob_name": "NewcastleV0"
}
    """
    tracer = trace.get_tracer(__name__)

    data_blob_name = None
    model_blob_name = None

    try:
        with tracer.start_as_current_span("run_model_on_image"):

            data_blob_name = extract_request_field(request, 'data_blob_name')
            model_blob_name = extract_request_field(request, 'model_blob_name')

            count_objects_args = {
                "model_blob_name": model_blob_name
            }

            with tracer.start_as_current_span('CF call: count_objects'):
                object_count_response_dict_list = run_cloud_function_async_with_parameter_list(
                    json_key='image_blob_name', json_values=[data_blob_name], partial_json=count_objects_args,
                    endpoint=count_objects_endpoint)

            object_count_response_dict = object_count_response_dict_list[0]
            logging.info(f'count_objects completed',
                         {
                             "data_blob_name": data_blob_name,
                             "model_blob_name": model_blob_name,
                             "count_objects_results": object_count_response_dict
                         })
            if object_count_response_dict['STATUS'] != 'Processed':
                message = f'object_count request reported "{object_count_response_dict["STATUS"]}":' \
                    f' "{object_count_response_dict}"'
                logging.error(f'ERROR: {message}')
                if object_count_response_dict['Message'].startswith('Failed after'):
                    raise ConnectionError(message)
                else:
                    raise RuntimeError(message)

            bigquery_write_args = {
                "model_blob_name": model_blob_name,
                "model_results_json": json.dumps(object_count_response_dict['results'])
            }

            with tracer.start_as_current_span('CF call: bigquery_write'):
                bigquery_write_response_dict_list = run_cloud_function_async_with_parameter_list(
                    json_key='image_blob_name', json_values=[data_blob_name], partial_json=bigquery_write_args,
                    endpoint=bigquery_write_endpoint)

            bigquery_write_response_dict = bigquery_write_response_dict_list[0]

            logging.info(f'bigquery_write completed', bigquery_write_response_dict)
            if bigquery_write_response_dict['STATUS'] != 'Processed':
                message = f'bigquery_write request reported "{bigquery_write_response_dict["STATUS"]}":' \
                    f' "{bigquery_write_response_dict}"'
                logging.error(f'ERROR: {message}')
                if bigquery_write_response_dict['Message'].startswith('Failed after'):
                    raise ConnectionError(message)
                else:
                    raise RuntimeError(message)

            if object_count_response_dict['results']['faulty']:
                return json.dumps({'STATUS': 'Faulty'})
            elif object_count_response_dict['results']['missing']:
                return json.dumps({'STATUS': 'Missing'})
            else:
                return json.dumps({'STATUS': 'Processed'})

    except Exception as e:
        return report_exception(e,
                                {'data_blob_name': data_blob_name,
                                 'model_blob_name': model_blob_name},
                                request=request)
