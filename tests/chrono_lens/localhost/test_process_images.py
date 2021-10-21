import datetime
import os

import pytest
from mock import patch
from pyfakefs.fake_filesystem_unittest import Patcher

from chrono_lens.localhost.process_images import process_scheduled


@patch('chrono_lens.localhost.process_images.datetime')
def test_no_cameras_no_entries(mock_datetime):
    with Patcher() as patcher:
        # access the fake_filesystem object via patcher.fs

        config_path = 'test-config'
        download_path = 'test-downloads'
        counts_path = 'test-counts'

        model_name = 'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'

        set_up_models_in_fake_fs(config_path, model_name, patcher.fs)

        expected_now = datetime.datetime(2000, 1, 2, 12, 30, 00)

        # No cameras listed

        mock_datetime.now.return_value = expected_now

        process_scheduled(config_path, download_path, counts_path)

        expected_filename = os.path.join(counts_path, model_name, f'{expected_now:%Y%m%d}.csv')
        with open(expected_filename, 'r') as camera_results_file:
            first_line = camera_results_file.readline()
            other_lines = camera_results_file.readlines()

        assert first_line == 'date,time,supplier,camera_id,bus,car,' \
                             'cyclist,faulty,missing,motorcyclist,person,truck,van\n'
        assert [] == other_lines


@pytest.mark.parametrize('_comment, model_name, image1_file_name, image2_file_name, image3_file_name, partial_results',
                         [
                             # results_tuple is bus,car,cyclist,faulty,missing,motorcyclist,person,truck,van
                             # Note that tuple is automatically prefixed with date,time,supplier,camera_id

                             # Missing image
                             ('Missing image', 'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0', None, None, None,
                              '0,0,0,False,True,0,0,0,0'),

                             # Isolated image = faulty
                             ('Isolated image = faulty', 'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0', None,
                              'TfL-images-20200501-0050-00001.08859.jpg', None,
                              '0,0,0,True,False,0,0,0,0'),

                             # Valid triplet, static objects removed
                             ('Valid triplet, static objects removed',
                              'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0',
                              'TfL-images-20200501-0040-00001.08859.jpg', 'TfL-images-20200501-0050-00001.08859.jpg',
                              'TfL-images-20200501-0100-00001.08859.jpg', '0,0,0,False,False,0,1,0,0'),

                             # Next missing, static objects removed
                             ('Next missing, static objects removed',
                              'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0',
                              'TfL-images-20200501-0040-00001.08859.jpg', 'TfL-images-20200501-0050-00001.08859.jpg',
                              None, '0,0,0,False,False,0,1,0,0'),

                             # Previous missing, static objects removed
                             ('Previous missing, static objects removed',
                              'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0',
                              None, 'TfL-images-20200501-0050-00001.08859.jpg',
                              'TfL-images-20200501-0100-00001.08859.jpg', '0,0,0,False,False,0,1,0,0'),

                             # All images the same, flagged as faulty
                             ('Previous missing, static objects removed',
                              'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0',
                              'TfL-images-20200501-0050-00001.08859.jpg', 'TfL-images-20200501-0050-00001.08859.jpg',
                              'TfL-images-20200501-0050-00001.08859.jpg', '0,0,0,True,False,0,0,0,0'),

                             # Previous and current images the same, flagged as faulty
                             ('Previous missing, static objects removed',
                              'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0',
                              'TfL-images-20200501-0050-00001.08859.jpg', 'TfL-images-20200501-0050-00001.08859.jpg',
                              'TfL-images-20200501-0100-00001.08859.jpg', '0,0,0,True,False,0,0,0,0'),
                         ])
@patch('chrono_lens.localhost.process_images.datetime')
def test_image_edge_cases(mock_datetime, _comment, model_name, image1_file_name, image2_file_name, image3_file_name,
                          partial_results):
    with Patcher() as patcher:
        # access the fake_filesystem object via patcher.fs

        config_path = 'test-config'
        download_path = 'test-downloads'
        counts_path = 'test-counts'

        set_up_models_in_fake_fs(config_path, model_name, patcher.fs)

        expected_now = datetime.datetime(2000, 1, 2, 12, 30, 00)
        expected_ten_minutes_ago = datetime.datetime(2000, 1, 2, 12, 20, 00)
        expected_twenty_minutes_ago = datetime.datetime(2000, 1, 2, 12, 10, 00)
        expected_thirty_minutes_ago = datetime.datetime(2000, 1, 2, 12, 00, 00)
        image_supplier = 'IMAGE_SUPPLIER'
        camera_name = 'test-camera'

        # add image
        time_series_folder = os.path.join('tests', 'test_data', 'time_series')

        image_thirty_minutes_ago_target_path = os.path.join(download_path, image_supplier,
                                                            f'{expected_thirty_minutes_ago:%Y%m%d}',
                                                            f'{expected_thirty_minutes_ago:%H%M}',
                                                            camera_name + '.jpg')
        if image1_file_name is not None:
            patcher.fs.add_real_file(source_path=os.path.join(time_series_folder, image1_file_name),
                                     target_path=image_thirty_minutes_ago_target_path)

        image_twenty_minutes_ago_target_path = os.path.join(download_path, image_supplier,
                                                            f'{expected_twenty_minutes_ago:%Y%m%d}',
                                                            f'{expected_twenty_minutes_ago:%H%M}',
                                                            camera_name + '.jpg')
        if image2_file_name is not None:
            patcher.fs.add_real_file(source_path=os.path.join(time_series_folder, image2_file_name),
                                     target_path=image_twenty_minutes_ago_target_path)

        image_ten_minutes_ago_target_path = os.path.join(download_path, image_supplier,
                                                         f'{expected_ten_minutes_ago:%Y%m%d}',
                                                         f'{expected_ten_minutes_ago:%H%M}',
                                                         camera_name + '.jpg')
        if image3_file_name is not None:
            patcher.fs.add_real_file(source_path=os.path.join(time_series_folder, image3_file_name),
                                     target_path=image_ten_minutes_ago_target_path)

        # Set up fake camera list
        patcher.fs.create_file(os.path.join(config_path, 'analyse', image_supplier + '.json'),
                               contents=f'["{camera_name}"]')

        mock_datetime.now.return_value = expected_now

        process_scheduled(config_path, download_path, counts_path)

        expected_filename = os.path.join(counts_path, model_name, f'{expected_now:%Y%m%d}.csv')
        with open(expected_filename, 'r') as camera_results_file:
            first_line = camera_results_file.readline()
            other_lines = camera_results_file.readlines()

    assert first_line == 'date,time,supplier,camera_id,bus,car,cyclist,faulty,missing,motorcyclist,person,truck,van\n'

    # Single result expected (image missing at appropriate time and date)
    assert 1 == len(other_lines)
    assert f'{expected_twenty_minutes_ago:%Y%m%d},{expected_twenty_minutes_ago:%H%M},' \
               f'IMAGE_SUPPLIER,test-camera,{partial_results}\n' == other_lines[0]


def set_up_models_in_fake_fs(config_path, model_name, fs):
    # Set up fake model config
    fs.create_file(os.path.join(config_path, 'analyse-configuration.json'),
                   contents=f'{{"model_blob_name": "{model_name}"}}')
    fs.create_file(os.path.join(config_path, 'models', 'FaultyImageFilterV0', 'configuration.json'),
                   contents=r'{"identical_area_proportion_threshold": 0.33,"row_similarity_threshold": 0.8,'
                            r'"consecutive_matching_rows_threshold": 0.2}')
    pb_filename = "test.pb"
    fs.create_file(os.path.join(config_path, 'models', 'NewcastleV0', 'configuration.json'),
                   contents=f'{{"serialized_graph_name": "{pb_filename}", "minimum_confidence": 0.33}}')
    fs.add_real_file(
        os.path.join('tests', 'test_data', 'test_detector_data', 'fig_frcnn_rebuscov-3.pb'),
        target_path=os.path.join(config_path, 'models', 'NewcastleV0', pb_filename)
    )
    fs.create_file(os.path.join(config_path, 'models', 'StaticObjectFilterV0', 'configuration.json'),
                   contents=r'{"scenecut_threshold": 0.4, "minimum_mask_proportion": 0.25, '
                            r'"minimum_mask_proportion_person": 0.10, "confidence_person": 0.80, '
                            r'"contour_area_threshold": 50}')
