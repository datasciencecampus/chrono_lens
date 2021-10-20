import datetime
import os

from mock import patch
from pyfakefs.fake_filesystem_unittest import TestCase

from chrono_lens.localhost.process_images import process_scheduled


class TestProcessImages(TestCase):

    def setUp(self):
        self.setUpPyfakefs()

        self.supplier_name = 'IMAGE_PROVIDER'

        self.config_path = 'test-config'
        self.download_path = 'test-downloads'
        self.counts_path = 'test-counts'

        # Set up fake model config
        self.model_name = 'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        self.fs.create_file(os.path.join(self.config_path, 'analyse-configuration.json'),
                            contents=f'{{"model_blob_name": "{self.model_name}"}}')

        self.fs.create_file(os.path.join(self.config_path, 'models', 'FaultyImageFilterV0', 'configuration.json'),
                            contents=r'{"identical_area_proportion_threshold": 0.33,"row_similarity_threshold": 0.8,'
                                     r'"consecutive_matching_rows_threshold": 0.2}')

        pb_filename = "test.pb"
        self.fs.create_file(os.path.join(self.config_path, 'models', 'NewcastleV0', 'configuration.json'),
                            contents=f'{{"serialized_graph_name": "{pb_filename}", "minimum_confidence": 0.33}}')

        self.fs.add_real_file(
            os.path.join('tests', 'test_data', 'test_detector_data', 'fig_frcnn_rebuscov-3.pb'),
            target_path=os.path.join(self.config_path, 'models', 'NewcastleV0', pb_filename)
        )

        self.fs.create_file(os.path.join(self.config_path, 'models', 'StaticObjectFilterV0', 'configuration.json'),
                            contents=r'{"scenecut_threshold": 0.4, "minimum_mask_proportion": 0.25, '
                                     r'"minimum_mask_proportion_person": 0.10, "confidence_person": 0.80, '
                                     r'"contour_area_threshold": 50}')

    @patch('chrono_lens.localhost.process_images.datetime')
    def test_no_cameras_no_entries(self, mock_datetime):
        expected_now = datetime.datetime(2000, 1, 2, 12, 30, 00)

        # No cameras listed

        mock_datetime.now.return_value = expected_now

        process_scheduled(self.config_path, self.download_path, self.counts_path)

        expected_filename = os.path.join(self.counts_path, self.model_name, f'{expected_now:%Y%m%d}.csv')
        with open(expected_filename, 'r') as camera_results_file:
            first_line = camera_results_file.readline()
            other_lines = camera_results_file.readlines()

        self.assertEquals(
            first_line, 'date,time,supplier,camera_id,bus,car,cyclist,faulty,missing,motorcyclist,person,truck,van\n')
        self.assertEqual([], other_lines)

    @patch('chrono_lens.localhost.process_images.datetime')
    def test_reports_missing_images(self, mock_datetime):
        expected_now = datetime.datetime(2000, 1, 2, 12, 30, 00)
        expected_twenty_minutes_ago = datetime.datetime(2000, 1, 2, 12, 10, 00)
        image_supplier = 'IMAGE_SUPPLIER'
        camera_name = 'test-camera'

        # Set up fake camera list
        self.fs.create_file(os.path.join(self.config_path, 'analyse', image_supplier + '.json'),
                            contents=f'["{camera_name}"]')

        mock_datetime.now.return_value = expected_now

        process_scheduled(self.config_path, self.download_path, self.counts_path)

        expected_filename = os.path.join(self.counts_path, self.model_name, f'{expected_now:%Y%m%d}.csv')
        with open(expected_filename, 'r') as camera_results_file:
            first_line = camera_results_file.readline()
            other_lines = camera_results_file.readlines()

        self.assertEquals(
            first_line,
            'date,time,supplier,camera_id,bus,car,cyclist,faulty,missing,motorcyclist,person,truck,van\n')

        # Single result expected (image missing at appropriate time and date)
        self.assertEquals(1, len(other_lines))
        self.assertEquals(
            f'{expected_twenty_minutes_ago:%Y%m%d},{expected_twenty_minutes_ago:%H%M},'
            f'IMAGE_SUPPLIER,test-camera,0,0,0,False,True,0,0,0,0\n',
            other_lines[0])

    @patch('chrono_lens.localhost.process_images.datetime')
    def test_isolated_image_reports_faulty(self, mock_datetime):
        expected_now = datetime.datetime(2000, 1, 2, 12, 30, 00)
        expected_twenty_minutes_ago = datetime.datetime(2000, 1, 2, 12, 10, 00)
        image_supplier = 'IMAGE_SUPPLIER'
        camera_name = 'test-camera'

        # add image
        time_series_folder = os.path.join('tests', 'test_data', 'time_series')

        image_0040_filename = 'TfL-images-20200501-0040-00001.08859.jpg'
        image_0040_target_path = os.path.join(self.download_path, image_supplier,
                                              f'{expected_twenty_minutes_ago:%Y%m%d}',
                                              f'{expected_twenty_minutes_ago:%H%M}',
                                              camera_name + '.jpg')
        self.fs.add_real_file(source_path=os.path.join(time_series_folder, image_0040_filename),
                              target_path=image_0040_target_path)

        # Set up fake camera list
        self.fs.create_file(os.path.join(self.config_path, 'analyse', image_supplier + '.json'),
                            contents=f'["{camera_name}"]')

        mock_datetime.now.return_value = expected_now

        process_scheduled(self.config_path, self.download_path, self.counts_path)

        expected_filename = os.path.join(self.counts_path, self.model_name, f'{expected_now:%Y%m%d}.csv')
        with open(expected_filename, 'r') as camera_results_file:
            first_line = camera_results_file.readline()
            other_lines = camera_results_file.readlines()

        self.assertEquals(
            first_line,
            'date,time,supplier,camera_id,bus,car,cyclist,faulty,missing,motorcyclist,person,truck,van\n')

        # Single result expected (image missing at appropriate time and date)
        self.assertEquals(1, len(other_lines))
        self.assertEquals(
            f'{expected_twenty_minutes_ago:%Y%m%d},{expected_twenty_minutes_ago:%H%M},'
            f'IMAGE_SUPPLIER,test-camera,0,0,0,True,False,0,0,0,0\n',
            other_lines[0])
