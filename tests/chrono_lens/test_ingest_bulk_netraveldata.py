import datetime
import json
import unittest
from unittest import mock
from urllib.error import HTTPError

from mock import MagicMock

with mock.patch('google.cloud.storage.Client'):
    from chrono_lens.gcloud.ingest_bulk_netraveldata import get_views_for_camera, get_camera_address_from_utmc, \
        round_time_up, get_images_from_archive


@mock.patch("chrono_lens.gcloud.ingest_bulk_netraveldata.urlopen")
@mock.patch("chrono_lens.gcloud.ingest_bulk_netraveldata.logging")
class TestIngestBulkNETravelData(unittest.TestCase):
    # Add tests if anything breaks - tricky to test as you need to substitute the requests library and pretend
    # data has been received - or that we failed twice and then got a result - did it cope?
    # Maybe highlight what tests to write - simple test per function to prove they work
    #
    # get_views_for_camera() can be simplified - but should only mod code once we've got tests in place to catch
    # introduced errors...

    def test_get_views_for_cameras_no_response_then_logs_and_returns_empty_list(self, mocked_logging, mocked_urlopen):
        test_camera_iri = 'http://somplace.org/web/end/point?args=none'
        test_uri_list = {}
        mocked_urlopen.side_effect = test_uri_list.get
        expected_feeds_views_links = []

        actual_feeds_views_links = get_views_for_camera(test_camera_iri)

        mocked_logging.warning.assert_called_with(f'Failed to open views for camera: "{test_camera_iri}"')
        self.assertListEqual(expected_feeds_views_links, actual_feeds_views_links)

    def test_get_views_for_cameras_parses_minimal_response_and_returns_list(self, _mocked_logging, mocked_urlopen):
        test_camera_iri = 'http://somplace.org/web/end/point?args=none'
        camera_name = 'Camera name'
        test_camera_data = {
            'feed': [
                {
                    'metric': camera_name,
                    'meta': {},
                    'links': [],
                    'timeseries': [{'links': []}]
                }
            ]
        }
        test_camera_data_json = json.dumps(test_camera_data)
        mock_http_response = MagicMock()
        mock_http_response.read.return_value = test_camera_data_json

        test_uri_list = {
            test_camera_iri: mock_http_response
        }
        mocked_urlopen.side_effect = test_uri_list.get
        expected_feeds_views_links = [
            {
                'name': camera_name,
                'view': -1,
                'default': test_camera_iri,
                'view_iri': False,
                'timeseries': False,
                'archiveIri': False
            }
        ]

        actual_feeds_views_links = get_views_for_camera(test_camera_iri)

        self.assertListEqual(expected_feeds_views_links, actual_feeds_views_links)

    @mock.patch("chrono_lens.gcloud.ingest_bulk_netraveldata.sleep")
    def test_get_views_for_cameras_retries_logs_sleeps_then_parses_minimal_response_and_returns_list(self, mocked_sleep,
                                                                                                     mocked_logging,
                                                                                                     mocked_urlopen):
        test_camera_iri = 'http://somplace.org/web/end/point?args=none'
        camera_name = 'Camera name'
        test_camera_data = {
            'feed': [
                {
                    'metric': camera_name,
                    'meta': {},
                    'links': [],
                    'timeseries': [{'links': []}]
                }
            ]
        }
        test_camera_data_json = json.dumps(test_camera_data)
        mock_http_response = MagicMock()
        mock_http_response.read.return_value = test_camera_data_json

        mocked_urlopen.side_effect = [
            HTTPError(test_camera_iri, 404, "panic", None, None),
            mock_http_response
        ]
        expected_feeds_views_links = [
            {
                'name': camera_name,
                'view': -1,
                'default': test_camera_iri,
                'view_iri': False,
                'timeseries': False,
                'archiveIri': False
            }
        ]

        actual_feeds_views_links = get_views_for_camera(test_camera_iri)

        mocked_logging.info.assert_called_once_with(f'Failed accessing "{test_camera_iri}"; retrying...')
        mocked_sleep.assert_called_once()
        self.assertListEqual(expected_feeds_views_links, actual_feeds_views_links)

    def test_get_camera_address_from_utmc_no_response_then_logs_and_returns_none(self, mocked_logging, mocked_urlopen):
        test_utmc_id = 'dummy'
        test_uri_list = {}
        mocked_urlopen.side_effect = test_uri_list.get
        expected_camera_address = None

        actual_camera_address = get_camera_address_from_utmc(test_utmc_id)

        mocked_logging.warning.assert_called_with(f'Failed to get camera address for UTMC ID {test_utmc_id}')
        self.assertEqual(expected_camera_address, actual_camera_address)

    def test_get_camera_address_from_utmc_simplest_response_returns_url(self, mocked_logging, mocked_urlopen):
        test_utmc_id = 'dummy'
        test_camera_iri = "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity" \
                          "?metric='Camera%20image'&brokerage:sourceId=dummy"
        test_camera_data = {
            'items': [
                {'links': [
                    {'rel': 'other'}
                ]
                }
            ]
        }
        test_camera_data_json = json.dumps(test_camera_data)
        mock_http_response = MagicMock()
        mock_http_response.read.return_value = test_camera_data_json

        test_uri_list = {
            test_camera_iri: mock_http_response
        }
        mocked_urlopen.side_effect = test_uri_list.get

        expected_camera_address = None

        actual_camera_address = get_camera_address_from_utmc(test_utmc_id)

        mocked_logging.warning.assert_not_called()
        self.assertEqual(expected_camera_address, actual_camera_address)

    def test_get_camera_address_from_utmc_given_href_response_returns_url(self, mocked_logging, mocked_urlopen):
        test_utmc_id = 'dummy'
        test_camera_iri = "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity" \
                          "?metric='Camera%20image'&brokerage:sourceId=dummy"
        expected_camera_address = 'http://not/here'
        test_camera_data = {
            'items': [
                {'links': [
                    {'rel': 'self.friendly',
                     'href': expected_camera_address}
                ]
                }
            ]
        }
        test_camera_data_json = json.dumps(test_camera_data)
        mock_http_response = MagicMock()
        mock_http_response.read.return_value = test_camera_data_json

        test_uri_list = {
            test_camera_iri: mock_http_response
        }
        mocked_urlopen.side_effect = test_uri_list.get

        actual_camera_address = get_camera_address_from_utmc(test_utmc_id)

        mocked_logging.warning.assert_not_called()
        self.assertEqual(expected_camera_address, actual_camera_address)

    @mock.patch("chrono_lens.gcloud.ingest_bulk_netraveldata.sleep")
    def test_get_camera_address_from_utmc_retries_logs_sleeps_then_given_href_response_returns_url(self, mocked_sleep,
                                                                                                   mocked_logging,
                                                                                                   mocked_urlopen):
        test_utmc_id = 'dummy'
        test_camera_iri = "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity" \
                          "?metric='Camera%20image'&brokerage:sourceId=dummy"
        expected_camera_address = 'http://not/here'
        test_camera_data = {
            'items': [
                {'links': [
                    {'rel': 'self.friendly',
                     'href': expected_camera_address}
                ]
                }
            ]
        }
        test_camera_data_json = json.dumps(test_camera_data)
        mock_http_response = MagicMock()
        mock_http_response.read.return_value = test_camera_data_json

        mocked_urlopen.side_effect = [
            HTTPError(test_camera_iri, 404, "panic", None, None),
            mock_http_response
        ]

        actual_camera_address = get_camera_address_from_utmc(test_utmc_id)

        mocked_logging.info.assert_called_once_with(f'Failed accessing UTMC "{test_camera_iri}"; retrying...')
        mocked_sleep.assert_called_once()
        self.assertEqual(expected_camera_address, actual_camera_address)

    def test_round_time_up_rounds_up_10_minutes_simple_case(self, _mocked_logging, _mocked_urlopen):
        input_dt = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=3, second=7)
        ten_minutes = datetime.timedelta(minutes=10)
        expected_rounded_datetime = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=10, second=0)

        actual_rounded_datetime = round_time_up(input_dt, date_delta=ten_minutes)

        self.assertEqual(expected_rounded_datetime, actual_rounded_datetime)

    def test_round_time_up_rounds_up_10_minutes_complex_case(self, _mocked_logging, _mocked_urlopen):
        input_dt = datetime.datetime(year=1999, month=12, day=31, hour=23, minute=50, second=1)
        ten_minutes = datetime.timedelta(minutes=10)
        expected_rounded_datetime = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0)

        actual_rounded_datetime = round_time_up(input_dt, date_delta=ten_minutes)

        self.assertEqual(expected_rounded_datetime, actual_rounded_datetime)

    def test_get_images_from_archive_all_present_returns_urls(self, _mocked_logging, mocked_urlopen):
        archive_uri = 'https://some.site.com/end/point'
        start_time = 'start'
        end_time = 'end'
        expected_image_1_url = 'http://test/image1.jpeg'
        expected_image_2_url = 'http://test/image2.jpeg'
        expected_image_urls = [expected_image_1_url, expected_image_2_url]
        archive_data = {
            'historic': {
                'values': [
                    {'time': '2020-09-26T18:32:38.000Z', 'duration': -19.999, 'value': expected_image_1_url},
                    {'time': '2020-09-26T04:01:30.000Z', 'duration': -20.074, 'value': expected_image_2_url}
                ]
            }
        }

        archive_data_json = json.dumps(archive_data)
        mock_http_response = MagicMock()
        mock_http_response.read.return_value = archive_data_json

        test_uri_list = {
            'https://some.site.com/end/point?startTime=start&endTime=end': mock_http_response
        }
        mocked_urlopen.side_effect = test_uri_list.get

        actual_image_urls = get_images_from_archive(archive_uri, start_time, end_time)

        self.assertListEqual(expected_image_urls, actual_image_urls)

    @mock.patch("chrono_lens.gcloud.ingest_bulk_netraveldata.sleep")
    def test_get_images_from_archive_initial_fail_causes_log_sleep_and_retry_returns_urls(self, mocked_sleep,
                                                                                          mocked_logging,
                                                                                          mocked_urlopen):
        archive_uri = 'https://some.site.com/end/point'
        start_time = 'start'
        end_time = 'end'
        expected_end_point = 'https://some.site.com/end/point?startTime=start&endTime=end'

        expected_image_url = 'http://test/image1.jpeg'
        expected_image_urls = [expected_image_url]
        archive_data = {
            'historic': {
                'values': [
                    {'time': '2020-09-26T18:32:38.000Z', 'duration': -19.999, 'value': expected_image_url},
                ]
            }
        }

        archive_data_json = json.dumps(archive_data)
        mock_http_response = MagicMock()
        mock_http_response.read.return_value = archive_data_json

        mocked_urlopen.side_effect = [
            HTTPError(expected_end_point, 404, "panic", None, None),
            mock_http_response
        ]

        actual_image_urls = get_images_from_archive(archive_uri, start_time, end_time)

        mocked_logging.info.assert_called_once_with(
            f'Failed accessing image archive end point "{expected_end_point}"; retrying...')
        mocked_sleep.assert_called_once()
        self.assertListEqual(expected_image_urls, actual_image_urls)

    def test_get_images_from_archive_no_response_then_logs_and_returns_empty_list(self, mocked_logging, mocked_urlopen):
        archive_uri = 'https://some.site.com/end/point'
        start_time = 'start'
        end_time = 'end'
        expected_end_point = 'https://some.site.com/end/point?startTime=start&endTime=end'
        test_uri_list = {}
        mocked_urlopen.side_effect = test_uri_list.get
        expected_image_urls = []

        actual_image_urls = get_images_from_archive(archive_uri, start_time, end_time)

        mocked_logging.warning.assert_called_with(f'Failed to open image archive end point: "{expected_end_point}"')
        self.assertListEqual(expected_image_urls, actual_image_urls)

    # Replace log_error!!!
