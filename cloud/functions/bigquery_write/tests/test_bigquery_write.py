import datetime
import json
import os
from time import sleep
from unittest import TestCase, skipIf, mock
from unittest.mock import MagicMock

from google.cloud import bigquery

gcloud_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var
if gcloud_project == '':
    assert False, "GCP_PROJECT environment variable is not set"

with mock.patch('dsc_lib.gcloud.logging.setup_logging_and_trace'):
    from main import bigquery_write, DATASET_NAME

"""
Example JSON test:
{
    "image_blob_name": "imageSource/20201224/0734/cameraId.jpg",
    "model_blob_name": "model_blob_name",
    "model_results_json": "{ \"person\": 3, \"car\": 5 }"
}
"""


def create_mock_request(request_json):
    mock_request = MagicMock()
    mock_request.get_json = MagicMock(return_value=request_json)
    return mock_request


class TestBigQueryWrite(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bigquery_client = bigquery.Client()
        cls.gcloud_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var

    @classmethod
    def remove_table(cls, table_name):
        cls.bigquery_client.delete_table(cls.make_table_id(table_name), not_found_ok=True)

    @classmethod
    def make_table_id(cls, table_name):
        return ".".join([cls.gcloud_project, DATASET_NAME, table_name])

    def test_missing_image_blob_name(self):
        mock_request = create_mock_request({})

        response_json = bigquery_write(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "image_blob_name" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_missing_model_blob_name(self):
        mock_request = create_mock_request({
            'image_blob_name': 'test_image_bucket'
        })

        response_json = bigquery_write(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "model_blob_name" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_missing_model_results_json(self):
        mock_request = create_mock_request({
            'image_blob_name': 'test_image_bucket',
            'model_blob_name': 'example_model_blob'
        })

        response_json = bigquery_write(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "model_results_json" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_first_use_creates_table_adds_row(self):

        model_blob_name = 'test_first_use_creates_table_adds_row'
        expected_source = 'someplace'
        expected_camera_id = 'example_camera'
        expected_date = datetime.date.today()
        expected_time = datetime.time(4, 5)
        expected_person_count = 2
        expected_car_count = 0
        expected_fault_code = False
        mock_request = create_mock_request({
            'image_blob_name': f'{expected_source}/{expected_date:%Y%m%d}/{expected_time:%H%M}/{expected_camera_id}.jpg',
            'model_blob_name': model_blob_name,
            'model_results_json': '{ '
                                  f'"person": {expected_person_count}'
                                  f', "car": {expected_car_count}'
                                  f', "faulty": {"true" if expected_fault_code else "false"}'
                                  '}'
        })

        # Remove table if it exists, so we won't get a collision from a previous test
        self.remove_table(model_blob_name)
        try:
            result = bigquery_write(mock_request)

            self.assertEqual('{"STATUS": "Processed"}', result)

            sleep(15)

            table_id = self.make_table_id(model_blob_name)
            query_results = self.bigquery_client.query(
                f"SELECT * FROM `{table_id}` WHERE date='{expected_date:%Y-%m-%d}'").result()

            rows = list(query_results)

            self.assertEqual(1, len(rows))
            self.assertEqual(expected_source, rows[0]['source'])
            self.assertEqual(expected_camera_id, rows[0]['camera_id'])
            self.assertEqual(expected_date, rows[0]['date'])
            self.assertEqual(expected_time, rows[0]['time'])
            self.assertEqual(expected_person_count, rows[0]['person'])
            self.assertEqual(expected_car_count, rows[0]['car'])
            self.assertEqual(expected_fault_code, rows[0]['faulty'])

        finally:
            # Remove table if it exists, ensure we tidy up after ourselves and don't leave detritus...
            self.remove_table(model_blob_name)

    @skipIf(os.environ.get("HOME", "") == "/builder/home",
            "Skipping on google cloud as tests are unreliable with BigQuery showing inconsistent results due to delays")
    def test_second_use_with_same_data_does_not_add_new_row(self):

        model_blob_name = 'test_second_use_with_same_data_does_not_add_new_row'
        expected_source = 'someplace'
        expected_camera_id = 'example_camera'
        expected_date = datetime.date.today()
        expected_time = datetime.time(4, 5)
        expected_person_count = 2
        expected_car_count = 0
        mock_request = create_mock_request({
            'image_blob_name': f'{expected_source}/{expected_date:%Y%m%d}/{expected_time:%H%M}/{expected_camera_id}.jpg',
            'model_blob_name': model_blob_name,
            'model_results_json': f'{{ "person": {expected_person_count}, "car": {expected_car_count} }}'
        })

        # Remove table if it exists, so we won't get a collision from a previous test
        self.remove_table(model_blob_name)
        try:
            result = bigquery_write(mock_request)
            self.assertEqual('{"STATUS": "Processed"}', result)

            result = bigquery_write(mock_request)
            self.assertEqual('{"STATUS": "Processed"}', result)

            sleep(15)

            table_id = self.make_table_id(model_blob_name)
            query_results = self.bigquery_client.query(
                f"SELECT * FROM `{table_id}` WHERE date='{expected_date:%Y-%m-%d}'").result()

            rows = list(query_results)

            self.assertEqual(1, len(rows))
            self.assertEqual(expected_source, rows[0]['source'])
            self.assertEqual(expected_camera_id, rows[0]['camera_id'])
            self.assertEqual(expected_date, rows[0]['date'])
            self.assertEqual(expected_time, rows[0]['time'])
            self.assertEqual(expected_person_count, rows[0]['person'])
            self.assertEqual(expected_car_count, rows[0]['car'])

        finally:
            # Remove table if it exists, ensure we tidy up after ourselves and don't leave detritus...
            self.remove_table(model_blob_name)

    @skipIf(os.environ.get("HOME", "") == "/builder/home",
            "Skipping on google cloud as tests are unreliable with BigQuery showing inconsistent results due to delays")
    def test_second_use_different_data_adds_second_row(self):

        model_blob_name = 'test_second_use_different_data_adds_second_row'
        expected_source1 = 'someplace'
        expected_camera_id1 = 'example_camera'
        expected_date = datetime.date.today()
        expected_time1 = datetime.time(4, 5)
        expected_person_count1 = 2
        expected_car_count1 = 0
        mock_request1 = create_mock_request({
            'image_blob_name': f'{expected_source1}/{expected_date:%Y%m%d}/{expected_time1:%H%M}/{expected_camera_id1}.jpg',
            'model_blob_name': model_blob_name,
            'model_results_json': f'{{ "person": {expected_person_count1}, "car": {expected_car_count1} }}'
        })

        expected_source2 = 'someplace2'
        expected_camera_id2 = 'example_camera2'
        expected_time2 = datetime.time(12, 14)
        expected_person_count2 = 1
        expected_car_count2 = 3
        mock_request2 = create_mock_request({
            'image_blob_name': f'{expected_source2}/{expected_date:%Y%m%d}/{expected_time2:%H%M}/{expected_camera_id2}.jpg',
            'model_blob_name': model_blob_name,
            'model_results_json': f'{{ "person": {expected_person_count2}, "car": {expected_car_count2} }}'
        })

        # Remove table if it exists, so we won't get a collision from a previous test
        self.remove_table(model_blob_name)
        try:
            result = bigquery_write(mock_request1)
            self.assertEqual('{"STATUS": "Processed"}', result)

            result = bigquery_write(mock_request2)
            self.assertEqual('{"STATUS": "Processed"}', result)

            sleep(15)

            table_id = self.make_table_id(model_blob_name)
            query_results = self.bigquery_client.query(
                f"SELECT * FROM `{table_id}` WHERE date='{expected_date:%Y-%m-%d}'").result()

            rows = list(query_results)

            self.assertEqual(2, len(rows))

            self.assertEqual(expected_source1, rows[0]['source'])
            self.assertEqual(expected_camera_id1, rows[0]['camera_id'])
            self.assertEqual(expected_date, rows[0]['date'])
            self.assertEqual(expected_time1, rows[0]['time'])
            self.assertEqual(expected_person_count1, rows[0]['person'])
            self.assertEqual(expected_car_count1, rows[0]['car'])

            self.assertEqual(expected_source2, rows[1]['source'])
            self.assertEqual(expected_camera_id2, rows[1]['camera_id'])
            self.assertEqual(expected_date, rows[1]['date'])
            self.assertEqual(expected_time2, rows[1]['time'])
            self.assertEqual(expected_person_count2, rows[1]['person'])
            self.assertEqual(expected_car_count2, rows[1]['car'])

        finally:
            # Remove table if it exists, ensure we tidy up after ourselves and don't leave detritus...
            self.remove_table(model_blob_name)

    def test_table_name_is_model_name_with_non_alphanumeric_replaced_with_underscores(self):
        model_blob_name = 'abcdxyz AB_C#DXYZ-=!@£$%^&*()_+{}[]:"|;\'\\<>?,.`\'~1234#567890/fish/fish.bin'
        # This isn't an authentication token etc. just a wide test of characters so safe to permit at commit
        # by pre-commit hook secrets.
        expected_table_name = 'abcdxyzAB_CDXYZ_1234567890'  # pragma: allowlist secret
        expected_source = 'someplace'
        expected_camera_id = 'example_camera'
        expected_date = datetime.date.today()
        expected_time = datetime.time(4, 5)
        expected_person_count = 2
        expected_car_count = 0
        mock_request = create_mock_request({
            'image_blob_name': f'{expected_source}/{expected_date:%Y%m%d}/{expected_time:%H%M}/{expected_camera_id}.jpg',
            'model_blob_name': model_blob_name,
            'model_results_json': f'{{ "person": {expected_person_count}, "car": {expected_car_count} }}'
        })

        # Remove table if it exists, so we won't get a collision from a previous test
        self.remove_table(expected_table_name)
        try:
            result = bigquery_write(mock_request)
            self.assertEqual('{"STATUS": "Processed"}', result)

            sleep(15)

            tables = self.bigquery_client.list_tables(DATASET_NAME)
            match = False
            for table in tables:
                if table.project == self.gcloud_project and table.dataset_id == DATASET_NAME and table.table_id == expected_table_name:
                    match = True
                    break

            self.assertTrue(match, f'Failed to find table {expected_table_name}')

        finally:
            # Remove table if it exists, ensure we tidy up after ourselves and don't leave detritus...
            self.remove_table(expected_table_name)

    def test_second_use_different_schema_fails(self):

        model_blob_name = 'test_second_use_different_schema_fails'
        expected_source1 = 'someplace'
        expected_camera_id1 = 'example_camera'
        expected_date1 = datetime.date(2020, 4, 2)
        expected_time1 = datetime.time(4, 5)
        expected_person_count1 = 2
        expected_car_count1 = 0
        mock_request1 = create_mock_request({
            'image_blob_name': f'{expected_source1}/{expected_date1:%Y%m%d}/{expected_time1:%H%M}/{expected_camera_id1}.jpg',
            'model_blob_name': model_blob_name,
            'model_results_json': f'{{ "person": {expected_person_count1}, "car": {expected_car_count1} }}'
        })

        expected_source2 = 'someplace2'
        expected_camera_id2 = 'example_camera2'
        expected_date2 = datetime.date(2222, 1, 2)
        expected_time2 = datetime.time(12, 14)
        expected_biscuit_count = 1
        mock_request2 = create_mock_request({
            'image_blob_name': f'{expected_source2}/{expected_date2:%Y%m%d}/{expected_time2:%H%M}/{expected_camera_id2}.jpg',
            'model_blob_name': model_blob_name,
            'model_results_json': f'{{ "biscuit": {expected_biscuit_count} }}'
        })

        # Remove table if it exists, so we won't get a collision from a previous test
        self.remove_table(model_blob_name)
        try:
            response1_json = bigquery_write(mock_request1)
            response1 = json.loads(response1_json)
            self.assertEqual('Processed', response1['STATUS'])

            response2_json = bigquery_write(mock_request2)
            response2 = json.loads(response2_json)
            self.assertEqual('Errored', response2['STATUS'])
            self.assertEqual("RuntimeError: ERRORS:\nItem#0:\nReason:\"invalid; message=\"no such field.\"\n",
                             response2['Message'])

            table_id = self.make_table_id(model_blob_name)
            query_results = self.bigquery_client.query(
                f"SELECT * FROM `{table_id}` WHERE date='{expected_date1:%Y-%m-%d}'").result()

            rows = list(query_results)

            self.assertEqual(1, len(rows))

            self.assertEqual(expected_source1, rows[0]['source'])
            self.assertEqual(expected_camera_id1, rows[0]['camera_id'])
            self.assertEqual(expected_date1, rows[0]['date'])
            self.assertEqual(expected_time1, rows[0]['time'])
            self.assertEqual(expected_person_count1, rows[0]['person'])
            self.assertEqual(expected_car_count1, rows[0]['car'])

        finally:
            # Remove table if it exists, ensure we tidy up after ourselves and don't leave detritus...
            self.remove_table(model_blob_name)
