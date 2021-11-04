import json
import os
from unittest import TestCase, mock

import cv2
import numpy as np
from requests.exceptions import ConnectionError

with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
    import main

mocked_requests_get_call_count = 0

test_detector_folder = os.path.join('..', '..', '..', '..', 'tests', 'test_data', 'test_detector_data')
time_series_folder = os.path.join('..', '..', '..', '..', 'tests', 'test_data', 'time_series')

valid_url = 'http://site.com/some/file.ext'
valid_url_content_filename = 'TfL-images-20200501-0040-00001.08859.jpg'
with open(os.path.join(time_series_folder, valid_url_content_filename), 'rb') as fp:
    valid_url_content = fp.read()

valid_url_large_image_url = 'http://site.com/some/large-file.jpg'
valid_url_large_image_content_filename = 'NETravelData-images_20200508_1040_CM_A69A1-View_02.jpg'
with open(os.path.join(time_series_folder, valid_url_large_image_content_filename), 'rb') as fp:
    valid_url_large_image_content = fp.read()

valid_url_broken_image_url = 'http://site.com/some/broken-file.jpg'
valid_url_broken_image_content = b'I am not a JPEG'

fifth_time_lucky_url = 'http://busy-web-site.com/some/file.ext'
fifth_time_lucky_url_content = valid_url_content

fifth_time_lucky_otherwise_exceptions_url = 'http://faulty-web-site.com/some/anotherfile.ext'
fifth_time_lucky_otherwise_exceptions_content = valid_url_content

missing_resource_url = 'http://another.site.com/missing_file.ext'

data_bucket_name = 'mybucket'
environment_variables = {'DATA_BUCKET_NAME': data_bucket_name}


class MockResponse:
    def __init__(self, status_code, json_result, content, content_type=None):
        self.status_code = status_code
        self.json_result = json_result
        self.ok = status_code <= 200
        self.text = json.dumps(json_result)
        self.content = content
        self.headers = {}
        if content_type is not None:
            self.headers['Content-type'] = content_type

    def status_code(self):
        return self.status_code

    def json(self):
        return self.json_result


# This method will be used by the mock to replace requests.get
def mocked_requests_get(*args, **kwargs):
    global mocked_requests_get_call_count
    mocked_requests_get_call_count += 1
    if args[0] == valid_url:
        return MockResponse(200, 'image', valid_url_content)
    elif args[0] == valid_url_large_image_url:
        return MockResponse(200, 'image', valid_url_large_image_content)
    elif args[0] == valid_url_broken_image_url:
        return MockResponse(200, 'image', valid_url_broken_image_content)
    elif args[0] == fifth_time_lucky_url:
        if mocked_requests_get_call_count >= 5:
            return MockResponse(200, 'image', fifth_time_lucky_url_content)
        else:
            return MockResponse(408, 'busy, try again', 'still busy')
    elif args[0] == fifth_time_lucky_otherwise_exceptions_url:
        if mocked_requests_get_call_count >= 5:
            return MockResponse(200, 'image', fifth_time_lucky_otherwise_exceptions_content)
        else:
            raise ConnectionError(104, 'Connection reset by peer')
    elif args[0] == missing_resource_url:
        return MockResponse(404, None, None)
    else:  # everything else including invalid url AND invalid params
        return MockResponse(500, None, None)


def create_mock_request(request_json):
    mock_request = mock.MagicMock()
    mock_request.get_json = mock.MagicMock(return_value=request_json)
    return mock_request


@mock.patch('main.os.environ.get', side_effect=environment_variables.get)
@mock.patch('main.requests.get', side_effect=mocked_requests_get)
@mock.patch('main.write_to_bucket')
class TestMain(TestCase):

    def test_missing_file_url_raises_error(self, _mocked_write_to_bucket, _mocked_requests_get, _mocked_os_environ_get):
        mock_request = create_mock_request({})

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "file_url" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_missing_destination_blob_name_raises_error(self, _mocked_write_to_bucket, _mocked_requests_get,
                                                        _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': valid_url
        })

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "destination_blob_name" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_request_succeeds_sends_to_bucket_and_reports_ok(self, mocked_write_to_bucket, _mocked_requests_get,
                                                             _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': valid_url,
            'destination_blob_name': 'afolder'
        })

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        mocked_write_to_bucket.assert_called_with(data_bucket_name, 'afolder/file.ext', valid_url_content,
                                                  content_type='image/jpeg')
        self.assertEqual('OK', response['STATUS'])

    def test_request_with_large_image_succeeds_sends_resize_image_to_bucket_and_reports_ok(
            self, mocked_write_to_bucket, _mocked_requests_get, _mocked_os_environ_get):

        mock_request = create_mock_request({
            'file_url': valid_url_large_image_url,
            'destination_blob_name': 'afolder'
        })

        response_json = main.download_file(mock_request)

        response = json.loads(response_json)

        (actual_data_bucket_name, actual_blob_name, actual_raw_image_data), keyword_args \
            = mocked_write_to_bucket.call_args_list[0]
        actual_content_type = keyword_args["content_type"]

        actual_image_bytes = np.asarray(bytearray(actual_raw_image_data), dtype="uint8")

        # Decode actual_raw_image_data and check it has been resized...
        actual_image = cv2.imdecode(actual_image_bytes, cv2.IMREAD_COLOR)

        # Set max thresholds
        image_max_axis_threshold = 440  # North East modal image width

        self.assertEqual(data_bucket_name, actual_data_bucket_name)
        self.assertEqual('afolder/large-file.jpg', actual_blob_name)
        self.assertEqual('image/jpeg', actual_content_type)
        self.assertEqual('OK', response['STATUS'])
        self.assertEqual(actual_image.shape[1], image_max_axis_threshold)
        self.assertEqual(actual_image.shape[0], int(480 / 640 * image_max_axis_threshold))

    def test_request_succeeds_with_url_ending_in_jpg_ignores_content_type_sends_to_bucket_as_jpeg_and_reports_ok(
            self, mocked_write_to_bucket, local_mocked_requests_get, _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': 'http://site.com/some/file.jpg',
            'destination_blob_name': 'afolder'
        })

        local_mocked_requests_get.side_effect = None
        local_mocked_requests_get.return_value = MockResponse(200, 'image', valid_url_content,
                                                              'application/octet-stream')

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        mocked_write_to_bucket.assert_called_with(data_bucket_name, 'afolder/file.jpg', valid_url_content,
                                                  content_type='image/jpeg')
        self.assertEqual('OK', response['STATUS'])

    def test_request_succeeds_with_content_type_sends_to_bucket_and_reports_ok(self, mocked_write_to_bucket,
                                                                               mocked_requests_get,
                                                                               _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': valid_url,
            'destination_blob_name': 'afolder'
        })

        mocked_requests_get.side_effect = None
        mocked_requests_get.return_value = MockResponse(200, 'image', valid_url_content, 'image/jpeg')

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        mocked_write_to_bucket.assert_called_with(data_bucket_name, 'afolder/file.ext', valid_url_content,
                                                  content_type='image/jpeg')
        self.assertEqual('OK', response['STATUS'])

    @mock.patch('main.sleep')
    def test_request_fails_retries_4_times_with_sleep_and_reports_error_but_does_not_use_bucket(self, mocked_sleep,
                                                                                                mocked_write_to_bucket,
                                                                                                _mocked_requests_get,
                                                                                                _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': 'http://site.com/some/missing-file.ext',
            'destination_blob_name': 'afolder'
        })
        global mocked_requests_get_call_count
        mocked_requests_get_call_count = 0

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        self.assertEqual(4, mocked_sleep.call_count)
        self.assertEqual(5, mocked_requests_get_call_count)
        self.assertEqual('Errored', response['STATUS'])
        mocked_write_to_bucket.assert_not_called()

    @mock.patch('main.sleep')
    def test_request_fails_with_missing_file_reports_error_but_does_not_use_bucket_or_retry(self, mocked_sleep,
                                                                                            mocked_write_to_bucket,
                                                                                            _mocked_requests_get,
                                                                                            _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': missing_resource_url,
            'destination_blob_name': 'afolder'
        })
        global mocked_requests_get_call_count
        mocked_requests_get_call_count = 0

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        mocked_write_to_bucket.assert_not_called()
        self.assertEqual(0, mocked_sleep.call_count)
        self.assertEqual(1, mocked_requests_get_call_count)

    @mock.patch('main.sleep')
    @mock.patch('logging.warning')
    def test_request_succeeds_but_faulty_file_reports_error_but_does_not_use_bucket_or_retry(self, mocked_warning,
                                                                                             mocked_sleep,
                                                                                             mocked_write_to_bucket,
                                                                                             _mocked_requests_get,
                                                                                             _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': valid_url_broken_image_url,
            'destination_blob_name': 'afolder'
        })
        global mocked_requests_get_call_count
        mocked_requests_get_call_count = 0

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        mocked_warning.assert_called_with(
            f'Failed to decode URL="{valid_url_broken_image_url}"  - empty bitmap generated')
        self.assertEqual('Errored', response['STATUS'])
        mocked_write_to_bucket.assert_not_called()
        self.assertEqual(0, mocked_sleep.call_count)
        self.assertEqual(1, mocked_requests_get_call_count)

    @mock.patch('main.sleep')
    def test_request_succeeds_on_fifth_attempt_sends_to_bucket_and_reports_ok(self, mocked_sleep,
                                                                               mocked_write_to_bucket,
                                                                               _mocked_requests_get,
                                                                               _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': fifth_time_lucky_url,
            'destination_blob_name': 'afolder'
        })
        global mocked_requests_get_call_count
        mocked_requests_get_call_count = 0

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        mocked_write_to_bucket.assert_called_with(data_bucket_name, 'afolder/file.ext', fifth_time_lucky_url_content,
                                                  content_type='image/jpeg')
        self.assertEqual(4, mocked_sleep.call_count)
        self.assertEqual(5, mocked_requests_get_call_count)
        self.assertEqual('OK', response['STATUS'])

    @mock.patch('main.sleep')
    def test_request_succeeds_on_fifth_attempt_after_exceptions_raised_sends_to_bucket_and_reports_ok(
            self, mocked_sleep, mocked_write_to_bucket, _mocked_requests_get, _mocked_os_environ_get):
        mock_request = create_mock_request({
            'file_url': fifth_time_lucky_otherwise_exceptions_url,
            'destination_blob_name': 'somefolder'
        })
        global mocked_requests_get_call_count
        mocked_requests_get_call_count = 0

        response_json = main.download_file(mock_request)
        response = json.loads(response_json)

        mocked_write_to_bucket.assert_called_with(data_bucket_name, 'somefolder/anotherfile.ext',
                                                  fifth_time_lucky_otherwise_exceptions_content,
                                                  content_type='image/jpeg')
        self.assertEqual(4, mocked_sleep.call_count)
        self.assertEqual(5, mocked_requests_get_call_count)
        self.assertEqual('OK', response['STATUS'])
