import datetime
import unittest

import pytest
from mock import patch

from tests.chrono_lens.gcloud.filters import is_running_on_gcp

pytestmark = pytest.mark.skipif(is_running_on_gcp(), reason="Skipping as not running on GCP")

from chrono_lens.gcloud import process_images


class TestProcessImages(unittest.TestCase):

    @patch('chrono_lens.gcloud.process_images.google.oauth2.service_account')
    @patch('chrono_lens.gcloud.process_images.google.auth.transport.requests')
    @patch('chrono_lens.gcloud.process_images.run_cloud_function_async_with_parameter_list')
    def test_all_args_correct(self, mock_run_cloud, _mock_requests, _mock_service_account):
        number_of_days = 3
        start_date = datetime.date(year=2020, month=10, day=1)
        end_date = datetime.date(year=2020, month=10, day=number_of_days)
        model_blob_name = 'test-model'
        camera_ids_to_analyse = {
            'test': ['a', 'b']
        }
        json_key_path = 'local-key.json'
        gcloud_region = 'somewhere-safe'
        gcloud_project = 'our-project'

        total_num_images = 0
        for image_source in camera_ids_to_analyse:
            total_num_images += len(camera_ids_to_analyse[image_source])

        # This level of information isn't passed down - just 'OK', not the additional detail.
        # Design change to return the whole dictionary.
        # mock_run_cloud.side_effect = [
        # {'STATUS': 'OK', 'OK': 144 * total_num_images},
        # {'STATUS': 'OK', 'OK': 140 * total_num_images, 'Missing': 4 * total_num_images},
        # {'STATUS': 'OK', 'OK': 144 * total_num_images},
        # ]
        responses = [[{'STATUS': 'OK', 'Counts': {'Processed': 142, 'Faulty': 2}}] * (total_num_images - 1)
                     + [{'STATUS': 'Errored', 'Message': "Sorry about that"}]] * number_of_days
        mock_run_cloud.side_effect = responses

        results, errors = process_images.run_model_on_images(
            start_date=start_date,
            end_date=end_date,
            cameras_to_analyse=camera_ids_to_analyse,
            model_blob_name=model_blob_name,
            json_key_path=json_key_path,
            gcp_project=gcloud_project,
            gcp_region=gcloud_region
        )

        self.assertEqual(
            {
                'Processed': number_of_days * (total_num_images - 1) * 142,
                'Faulty': number_of_days * 1 * 2,
                'Errors': {'Errored': number_of_days},
                # 'STATUS': number_of_days * 1,
                # 'OK': total_num_images * (144 + 140 + 144),
                # 'Missing': 4 * total_num_images,
            },
            results
        )

        self.assertListEqual([{'STATUS': 'Errored', 'Message': "Sorry about that"}] * 3,
                             errors)
