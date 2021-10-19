import datetime
import os

from mock import patch, MagicMock
from pyfakefs.fake_filesystem_unittest import TestCase

from chrono_lens.localhost.image_downloads import download_all_images


# def download_all_images(config_folder_name, download_folder_name, maximum_number_of_download_attempts):


class TestRemoveImages(TestCase):

    def setUp(self):
        self.setUpPyfakefs()

        self.download_folder_name = 'test'
        self.supplier_name = 'IMAGE_PROVIDER'

    @patch('chrono_lens.localhost.image_downloads.datetime')
    @patch('chrono_lens.localhost.image_downloads.requests')
    def test_small_images_unmodified(self, mock_requests, mock_datetime):
        config_folder_name = 'test/config'
        image_supplier_name = 'IMAGE_SUPPLIER'
        image_base_name = 'image.jpg'
        image_url = 'http://dummy.com/some/folder/' + image_base_name
        maximum_number_of_download_attempts = 5
        expected_now = datetime.datetime(2000, 1, 2, 12, 30, 00)

        self.fs.create_file(os.path.join(config_folder_name, 'ingest', image_supplier_name + '.json'),
                            contents=f'''[ "{image_url}" ]''')

        small_image_filename = os.path.join('tests', 'test_data', 'time_series',
                                            'TfL-images-20200501-0040-00001.08859.jpg')
        self.fs.add_real_file(small_image_filename)

        with open(small_image_filename, 'rb') as image_data:
            small_image_raw_jpeg = image_data.read()

        mock_request_response = MagicMock()
        mock_request_response.status_code = 200
        mock_request_response.content = small_image_raw_jpeg
        mock_requests.get.return_value = mock_request_response

        mock_datetime.now.return_value = expected_now

        download_all_images(config_folder_name, self.download_folder_name, maximum_number_of_download_attempts)

        expected_filename = os.path.join(self.download_folder_name, image_supplier_name, f'{expected_now:%Y%m%d}',
                                         f'{expected_now:%H%M}', image_base_name)
        with open(expected_filename, 'rb') as actual_image_data:
            actual_small_image_raw_jpeg = actual_image_data.read()

        self.assertEquals(small_image_raw_jpeg, actual_small_image_raw_jpeg)

    @patch('chrono_lens.localhost.image_downloads.datetime')
    @patch('chrono_lens.localhost.image_downloads.requests')
    def test_file_extensions_replaced(self, mock_requests, mock_datetime):
        config_folder_name = 'test/config'
        image_supplier_name = 'IMAGE_SUPPLIER'
        image_base_name = 'images-etc.'
        image_url = 'http://dummy.com/some/other/folder/' + image_base_name + "extension"
        maximum_number_of_download_attempts = 5
        expected_now = datetime.datetime(2010, 9, 7, 00, 00, 00)

        self.fs.create_file(os.path.join(config_folder_name, 'ingest', image_supplier_name + '.json'),
                            contents=f'''[ "{image_url}" ]''')

        small_image_filename = os.path.join('tests', 'test_data', 'time_series',
                                            'TfL-images-20200501-0040-00001.08859.jpg')
        self.fs.add_real_file(small_image_filename)

        with open(small_image_filename, 'rb') as image_data:
            small_image_raw_jpeg = image_data.read()

        mock_request_response = MagicMock()
        mock_request_response.status_code = 200
        mock_request_response.content = small_image_raw_jpeg
        mock_requests.get.return_value = mock_request_response

        mock_datetime.now.return_value = expected_now

        download_all_images(config_folder_name, self.download_folder_name, maximum_number_of_download_attempts)

        expected_filename = os.path.join(self.download_folder_name, image_supplier_name, f'{expected_now:%Y%m%d}',
                                         f'{expected_now:%H%M}', image_base_name + 'jpg')
        with open(expected_filename, 'rb') as actual_image_data:
            actual_small_image_raw_jpeg = actual_image_data.read()

        self.assertEquals(small_image_raw_jpeg, actual_small_image_raw_jpeg)

    @patch('chrono_lens.localhost.image_downloads.datetime')
    @patch('chrono_lens.localhost.image_downloads.requests')
    def test_now_clamped_by_10mins_in_filename(self, mock_requests, mock_datetime):
        config_folder_name = 'test/config'
        image_supplier_name = 'IMAGE_SUPPLIER'
        image_base_name = 'image.jpg'
        image_url = 'http://dummy.com/some/folder/' + image_base_name
        maximum_number_of_download_attempts = 5
        fake_now = datetime.datetime(2000, 1, 2, 12, 34, 56)
        expected_now = datetime.datetime(2000, 1, 2, 12, 30, 00)

        self.fs.create_file(os.path.join(config_folder_name, 'ingest', image_supplier_name + '.json'),
                            contents=f'''[ "{image_url}" ]''')

        small_image_filename = os.path.join('tests', 'test_data', 'time_series',
                                            'TfL-images-20200501-0040-00001.08859.jpg')
        self.fs.add_real_file(small_image_filename)

        with open(small_image_filename, 'rb') as image_data:
            small_image_raw_jpeg = image_data.read()

        mock_request_response = MagicMock()
        mock_request_response.status_code = 200
        mock_request_response.content = small_image_raw_jpeg
        mock_requests.get.return_value = mock_request_response

        mock_datetime.now.return_value = fake_now

        download_all_images(config_folder_name, self.download_folder_name, maximum_number_of_download_attempts)

        expected_filename = os.path.join(self.download_folder_name, image_supplier_name, f'{expected_now:%Y%m%d}',
                                         f'{expected_now:%H%M}', image_base_name)
        with open(expected_filename, 'rb') as actual_image_data:
            actual_small_image_raw_jpeg = actual_image_data.read()

        self.assertEquals(small_image_raw_jpeg, actual_small_image_raw_jpeg)
