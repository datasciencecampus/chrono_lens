import json
import logging
import os

from google.cloud import bigquery
from opentelemetry import trace

from chrono_lens.gcloud.bigquery import convert_model_name_to_table_name
from chrono_lens.gcloud.call_handling import extract_request_field
from chrono_lens.gcloud.error_handling import report_exception
from chrono_lens.gcloud.logging import setup_logging_and_trace

setup_logging_and_trace()

bigquery_client = bigquery.Client()

gcloud_region = os.environ.get('FUNCTION_REGION', '')  # Built-in env var
gcloud_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var

DATASET_NAME = 'detected_objects'  # As defined in gcp-setup.sh (BigQuery dataset creation)


def bigquery_write(request):
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
    model_results_json = None

    try:
        with tracer.start_as_current_span("bigquery_write"):
            image_blob_name = extract_request_field(request, 'image_blob_name')
            model_blob_name = extract_request_field(request, 'model_blob_name')
            model_results_json = extract_request_field(request, 'model_results_json')
            model_results = json.loads(model_results_json)

            model_name = convert_model_name_to_table_name(model_blob_name)
            source, date, time, camera_filename = image_blob_name.split('/')
            camera_id = os.path.splitext(camera_filename)[0]

            with tracer.start_as_current_span("Checking table"):
                table_names_list = [table_obj.table_id for table_obj in bigquery_client.list_tables(DATASET_NAME)]
                if model_name not in table_names_list:
                    with tracer.start_as_current_span("Creating table"):
                        # Create table for model if one doesn't exist
                        dict_schema = {'source': 'STRING', 'camera_id': 'STRING', 'date': 'DATE',
                                       'time': 'TIME'}  # default schema
                        for result_name in model_results.keys():
                            result_type = type(model_results[result_name])
                            if result_type is int:
                                dict_schema[result_name] = 'INTEGER'
                            elif result_type is bool:
                                dict_schema[result_name] = 'BOOLEAN'
                            else:
                                raise ValueError(f'{result_name} is of unhandled type in results: "{result_type}"')
                        create_table(model_name, dict_schema)

            table_id = ".".join([gcloud_project, DATASET_NAME, model_name])
            table = bigquery_client.get_table(table_id)

            entry = {
                'source': source,
                'camera_id': camera_id,
                'date': f'{date[0:4]}-{date[4:6]}-{date[6:8]}',
                'time': f'{time[0:2]}:{time[2:4]}:00'
            }
            for result_name, obj_result in model_results.items():
                entry[result_name] = obj_result

            # insert_row_json func needs a list of dictionaries, 1 dict per entry
            new_row = [entry]
            row_id = entry['camera_id'] + '_' + entry['source'] + '_' + entry['date'] + '_' + entry['time']
            # row_ids is a temporary (1 minute) ID for a given row, to prevent duplication within that time.
            # See ticket #264; refer to: https://cloud.google.com/bigquery/streaming-data-into-bigquery#dataconsistency
            # noting that `insertId` is the `row_ids` in the python API
            with tracer.start_as_current_span("Appending to table"):
                errors = bigquery_client.insert_rows_json(table, new_row, row_ids=[row_id])

            if not errors:
                return json.dumps({'STATUS': 'Processed'})

            return_message = 'ERRORS:\n'
            for e in errors:
                logging.error(e)
                return_message = return_message + f'Item#{e["index"]}:\n'
                for item_error in e["errors"]:
                    return_message += f'Reason:"{item_error["reason"]}; message="{item_error["message"]}"\n'
            raise RuntimeError(return_message)

    except Exception as e:
        return report_exception(e,
                                {'image_blob_name': image_blob_name,
                                 'model_blob_name': model_blob_name,
                                 'model_results_json': model_results_json},
                                request=request)


def create_table(table_name, dict_schema):
    schema = []
    for col_name, field_type in dict_schema.items():
        column = bigquery.SchemaField(col_name, field_type, mode="REQUIRED")
        schema.append(column)

    table_id = ".".join([gcloud_project, DATASET_NAME, table_name])
    table = bigquery.Table(table_id, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(field="date")
    table.require_partition_filter = True
    table = bigquery_client.create_table(table)

    logging.warning(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")
    return
