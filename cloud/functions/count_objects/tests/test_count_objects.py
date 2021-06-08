import json
import os
from unittest import TestCase, mock
from unittest.mock import MagicMock

import google

data_bucket_name = 'data_bucket'
models_bucket_name = 'model_bucket'
with mock.patch.dict(os.environ, {
    'DATA_BUCKET_NAME': data_bucket_name,
    'MODELS_BUCKET_NAME': models_bucket_name
}):
    with mock.patch('google.cloud.storage.Client'):
        with mock.patch('dsc_lib.gcloud.logging.setup_logging_and_trace'):
            import main


def create_mock_request(request_json):
    mock_request = MagicMock()
    mock_request.get_json = MagicMock(return_value=request_json)
    return mock_request


def create_mock_bucket(bucket_blob_data_maps):
    blob_name_to_blob = {}

    for blob_name, blob_data in bucket_blob_data_maps:
        mock_blob = MagicMock()
        if blob_data is None:
            mock_blob.download_as_string.side_effect = google.api_core.exceptions.NotFound('')
        else:
            mock_blob.download_as_string.return_value = blob_data

        blob_name_to_blob[blob_name] = mock_blob

    mock_bucket = MagicMock()
    mock_bucket.blob.side_effect = blob_name_to_blob.get

    return mock_bucket


class TestCountObjects(TestCase):
    """
    NOTE:

    Tests should use unique names for models, otherwise count_objects will cache the models - and not create new ones;
    hence one test may request a different configuration but this will not be created if a previous test requested
    a configuration with the same name - it'll reuse it... and cause confusion / accidental test failure or (worse)
    accidental test success
    """
    @classmethod
    def setUpClass(cls):
        test_detector_folder = os.path.join('..', 'dsc_lib_tests', 'test_data', 'test_detector_data')
        time_series_folder = os.path.join('..', 'dsc_lib_tests', 'test_data', 'time_series')

        static_object_test_image_0040_filename = 'TfL-images-20200501-0040-00001.08859.jpg'
        with open(os.path.join(time_series_folder, static_object_test_image_0040_filename), 'rb') as fp:
            cls.raw_static_object_test_image_0040 = fp.read()

        static_object_test_image_0050_filename = 'TfL-images-20200501-0050-00001.08859.jpg'
        with open(os.path.join(time_series_folder, static_object_test_image_0050_filename), 'rb') as fp:
            cls.raw_static_object_test_image_0050 = fp.read()

        static_object_test_image_0100_filename = 'TfL-images-20200501-0100-00001.08859.jpg'
        with open(os.path.join(time_series_folder, static_object_test_image_0100_filename), 'rb') as fp:
            cls.raw_static_object_test_image_0100 = fp.read()

        small_sample_image_filename = 'TfL-images-20200501-1340-00001.04542.jpg'  # 352x288
        with open(os.path.join(time_series_folder, small_sample_image_filename), 'rb') as fp:
            cls.raw_small_sample_image = fp.read()

        large_sample_image_filename = 'NETravelData-images_20200508_1110_NT_A191E1.jpg'  # 640x480
        with open(os.path.join(time_series_folder, large_sample_image_filename), 'rb') as fp:
            cls.raw_large_sample_image = fp.read()

        rcnn_serialised_model_filename = 'fig_frcnn_rebuscov-3.pb'
        with open(os.path.join(test_detector_folder, rcnn_serialised_model_filename), 'rb') as fp:
            cls.rcnn_serialised_model = fp.read()

    def test_missing_image_blob_name(self):
        mock_request = create_mock_request({
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "image_blob_name" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_missing_model_blob_name(self):
        mock_request = create_mock_request({
            'image_blob_name': 'test_image_blob',
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "model_blob_name" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_incorrect_format_image_blob_name(self):
        mock_request = create_mock_request({
            'image_blob_name': 'test_image_blob',
            'model_blob_name': 'test_model_blob'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('ValueError: blob name not in format "source/YYYYMMDD/HHMM/camera_id.ext";'
                         ' instead received "test_image_blob"',
                         response['Message'])

    def test_identifies_items_in_small_image(self):

        image_blob_name = 'TfL-images/20200501/0040/00001.08859.jpg'

        model_blob_name = 'Newcastle-v99'
        model_serialised_graph_name = 'magic-3.pb'

        model_configuration_json = f"""
        {{
            "serialized_graph_name": "{model_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_name, self.raw_small_sample_image)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{model_blob_name}/configuration.json', model_configuration_json),
            (f'{model_blob_name}/{model_serialised_graph_name}', self.rcnn_serialised_model)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_name,
            'model_blob_name': model_blob_name,
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        self.assertEqual(2, results['person'])  # correct - but difficult to confirm
        self.assertEqual(12, results['car'])  # possibly 18 when you look into the blurry distance
        self.assertEqual(0, results['truck'])  # correct
        self.assertEqual(0, results['bus'])  # correct
        self.assertEqual(0, results['cyclist'])  # 1 cyclist
        self.assertEqual(0, results['motorcyclist'])  # correct
        self.assertEqual(1, results['van'])  # correct - can't tell whats in the distance, may be more
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    def test_identifies_objects_in_different_size_images(self):
        small_image_blob_name = 'test/20200501/0040/small.jpg'
        large_image_blob_name = 'test/20200501/0040/large.jpg'

        model_blob_name = 'Newcastle-test'
        model_serialised_graph_name = 'magic-3.pb'

        model_configuration_json = f"""
        {{
            "serialized_graph_name": "{model_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        main.data_bucket = create_mock_bucket([
            (small_image_blob_name, self.raw_small_sample_image),
            (large_image_blob_name, self.raw_large_sample_image)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{model_blob_name}/configuration.json', model_configuration_json),
            (f'{model_blob_name}/{model_serialised_graph_name}', self.rcnn_serialised_model)
        ])

        mock_request = create_mock_request({
            'image_blob_name': small_image_blob_name,
            'model_blob_name': model_blob_name,
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        self.assertEqual(2, results['person'])  # correct - but difficult to confirm
        self.assertEqual(12, results['car'])  # possibly 18 when you look into the blurry distance
        self.assertEqual(0, results['truck'])  # correct
        self.assertEqual(0, results['bus'])  # correct
        self.assertEqual(0, results['cyclist'])  # 1 cyclist
        self.assertEqual(0, results['motorcyclist'])  # correct
        self.assertEqual(1, results['van'])  # correct - can't tell whats in the distance, may be more
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

        mock_request = create_mock_request({
            'image_blob_name': large_image_blob_name,
            'model_blob_name': model_blob_name,
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # large_sample_image_filename = 'NETravelData-images_20200508_1110_NT_A191E1.jpg'  # 640x480
        # 4 cyclists/pedestrians, 5 cars

        self.assertEqual(1, results['person'])  # expected 4 cyclists/pedestrians but very blurry
        self.assertEqual(5, results['car'])  # correct
        self.assertEqual(0, results['truck'])  # correct
        self.assertEqual(0, results['bus'])  # correct
        self.assertEqual(0, results['cyclist'])  # correct
        self.assertEqual(0, results['motorcyclist'])  # correct
        self.assertEqual(0, results['van'])  # correct
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    def test_static_filter_removes_items(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        model_blob_name = 'Newcastle-test2'
        model_serialised_graph_name = 'magic-3.pb'

        model_configuration_json = f"""
        {{
            "serialized_graph_name": "{model_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test2'

        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_0040_name, self.raw_static_object_test_image_0040),
            (image_blob_0050_name, self.raw_static_object_test_image_0050),
            (image_blob_0100_name, self.raw_static_object_test_image_0100)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{model_blob_name}/configuration.json', model_configuration_json),
            (f'{model_blob_name}/{model_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{model_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # reference "TfL-images-20200501-0050-00001.08859_filtered.png"
        self.assertEqual(1, results['person'])  # correct
        self.assertEqual(0, results['car'])  # correct (static objects removed)
        self.assertEqual(0, results['truck'])  # correct (static objects removed)
        self.assertEqual(0, results['bus'])  # correct (static objects removed)
        self.assertEqual(0, results['cyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['motorcyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['van'])  # correct (static objects removed)
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    def test_raises_error_on_unknown_post_process(self):
        image_blob_name = 'test/10660109/0040/andallthat.jpg'

        model_blob_name = 'Newcastle-test3'
        model_serialised_graph_name = 'magic-3.pb'

        model_configuration_json = f"""
        {{
            "serialized_graph_name": "{model_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        fake_post_process_name = 'rhubarb'

        main.data_bucket = create_mock_bucket([
            (image_blob_name, self.raw_small_sample_image)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{model_blob_name}/configuration.json', model_configuration_json),
            (f'{model_blob_name}/{model_serialised_graph_name}', self.rcnn_serialised_model),
            (model_blob_name + '/fig_frcnn_rebuscov-3.pb', self.rcnn_serialised_model)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_name,
            'model_blob_name': f'{model_blob_name}_{fake_post_process_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual(f'ValueError: Model post-process stage is unknown: "{fake_post_process_name}"',
                         response['Message'])

    def test_raises_error_on_unknown_object_detector(self):
        image_blob_name = 'test/19990101/0040/fish.jpg'
        fake_object_detector_name = 'rhubarb'

        main.data_bucket = create_mock_bucket([
            (image_blob_name, self.raw_small_sample_image)
        ])

        main.model_bucket = create_mock_bucket([
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_name,
            'model_blob_name': f'{fake_object_detector_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual(f'ValueError: Model object detector stage is unknown: "{fake_object_detector_name}"',
                         response['Message'])

    def test_rejects_missing_image(self):
        image_blob_name = 'TfL-images/20200501/0040/00001.08859.jpg'

        object_detector_blob_name = 'Newcastle-test4'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_name, None)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_name,
            'model_blob_name': f'{object_detector_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        self.assertEqual(0, results['person'])
        self.assertEqual(0, results['car'])
        self.assertEqual(0, results['truck'])
        self.assertEqual(0, results['bus'])
        self.assertEqual(0, results['cyclist'])
        self.assertEqual(0, results['motorcyclist'])
        self.assertEqual(0, results['van'])
        self.assertEqual(True, results['missing'])
        self.assertEqual(False, results['faulty'])

    def test_rejects_zero_length_image_as_faulty(self):
        image_blob_name = 'TfL-images/20200501/0040/00001.08859.jpg'

        object_detector_blob_name = 'Newcastle-test5'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_name, b'')
        ])

        main.model_bucket = create_mock_bucket([
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_name,
            'model_blob_name': f'{object_detector_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        self.assertEqual(0, results['person'])
        self.assertEqual(0, results['car'])
        self.assertEqual(0, results['truck'])
        self.assertEqual(0, results['bus'])
        self.assertEqual(0, results['cyclist'])
        self.assertEqual(0, results['motorcyclist'])
        self.assertEqual(0, results['van'])
        self.assertEqual(False, results['missing'])
        self.assertEqual(True, results['faulty'])

    def test_preprocess_rejects_faulty_image(self):
        image_blob_name = 'TfL-images/20200501/0040/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test6'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test6'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        main.data_bucket = create_mock_bucket([
            # same physical image to trigger rejection
            ('TfL-images/20200501/0030/00001.08859.jpg', self.raw_static_object_test_image_0040),
            (image_blob_name, self.raw_static_object_test_image_0040),
            ('TfL-images/20200501/0050/00001.08859.jpg', self.raw_static_object_test_image_0040),
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        self.assertEqual(0, results['person'])
        self.assertEqual(0, results['car'])
        self.assertEqual(0, results['truck'])
        self.assertEqual(0, results['bus'])
        self.assertEqual(0, results['cyclist'])
        self.assertEqual(0, results['motorcyclist'])
        self.assertEqual(0, results['van'])
        self.assertEqual(False, results['missing'])
        self.assertEqual(True, results['faulty'])

    def test_preprocess_skipped_if_previous_image_faulty(self):
        image_blob_name = 'TfL-images/20200501/0040/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test7'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test7'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        main.data_bucket = create_mock_bucket([
            # same physical image to trigger rejection
            ('TfL-images/20200501/0030/00001.08859.jpg', b'faulty image'),
            (image_blob_name, self.raw_static_object_test_image_0040),
            ('TfL-images/20200501/0050/00001.08859.jpg', self.raw_static_object_test_image_0050),
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # Reminder: static object filter not requested, main image is 0040 time slot
        self.assertEqual(0, results['person'])  # correct
        self.assertEqual(3, results['car'])  # can only identify 1 small van
        self.assertEqual(0, results['truck'])  # correct
        self.assertEqual(0, results['bus'])  # correct
        self.assertEqual(0, results['cyclist'])  # correct
        self.assertEqual(0, results['motorcyclist'])  # correct
        self.assertEqual(3, results['van'])  # correct (3 large vans)
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    def test_preprocess_skipped_if_next_image_faulty(self):
        image_blob_name = 'TfL-images/20200501/0040/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test8'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test8'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        main.data_bucket = create_mock_bucket([
            # same physical image to trigger rejection
            ('TfL-images/20200501/0030/00001.08859.jpg', self.raw_static_object_test_image_0040),
            (image_blob_name, self.raw_static_object_test_image_0050),
            ('TfL-images/20200501/0050/00001.08859.jpg', b'faulty image'),
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # Reminder: static object filter not requested, main image is 0050 time slot
        self.assertEqual(1, results['person'])  # correct
        self.assertEqual(2, results['car'])  # can only identify 1 small van
        self.assertEqual(0, results['truck'])  # correct
        self.assertEqual(0, results['bus'])  # correct
        self.assertEqual(0, results['cyclist'])  # correct
        self.assertEqual(0, results['motorcyclist'])  # correct
        self.assertEqual(3, results['van'])  # correct (3 large vans)
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    # previous, current, next images: A,B,C
    def test_preprocess_and_object_count_and_postprocess(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test9'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test9'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test9'
        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_0040_name, self.raw_static_object_test_image_0040),
            (image_blob_0050_name, self.raw_static_object_test_image_0050),
            (image_blob_0100_name, self.raw_static_object_test_image_0100)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # reference "TfL-images-20200501-0050-00001.08859_filtered.png"
        self.assertEqual(1, results['person'])  # correct
        self.assertEqual(0, results['car'])  # correct (static objects removed)
        self.assertEqual(0, results['truck'])  # correct (static objects removed)
        self.assertEqual(0, results['bus'])  # correct (static objects removed)
        self.assertEqual(0, results['cyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['motorcyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['van'])  # correct (static objects removed)
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    def test_preprocess_and_object_count_and_postprocess_copes_with_faulty_previous_image(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test10'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test10'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test10'
        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_0040_name, b'faulty image'),
            (image_blob_0050_name, self.raw_static_object_test_image_0050),
            (image_blob_0100_name, self.raw_static_object_test_image_0100)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # reference "TfL-images-20200501-0050-00001.08859_filtered.png"
        self.assertEqual(1, results['person'])  # correct
        self.assertEqual(0, results['car'])  # correct (static objects removed)
        self.assertEqual(0, results['truck'])  # correct (static objects removed)
        self.assertEqual(0, results['bus'])  # correct (static objects removed)
        self.assertEqual(0, results['cyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['motorcyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['van'])  # correct (static objects removed)
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    def test_preprocess_and_object_count_and_postprocess_copes_with_faulty_next_image(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test11'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test11'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test11'
        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_0040_name, self.raw_static_object_test_image_0040),
            (image_blob_0050_name, self.raw_static_object_test_image_0050),
            (image_blob_0100_name, b'faulty')
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # reference "TfL-images-20200501-0050-00001.08859_filtered.png"
        self.assertEqual(1, results['person'])  # correct
        self.assertEqual(0, results['car'])  # correct (static objects removed)
        self.assertEqual(0, results['truck'])  # correct (static objects removed)
        self.assertEqual(0, results['bus'])  # correct (static objects removed)
        self.assertEqual(0, results['cyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['motorcyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['van'])  # correct (static objects removed)
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    # previous, current, next images: A,B,B
    def test_preprocess_and_object_count_and_postprocess_copes_with_current_matches_next_image(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test12'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test12'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test12'
        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_0040_name, self.raw_static_object_test_image_0040),
            (image_blob_0050_name, self.raw_static_object_test_image_0050),
            # NOTE rudely reusing same image data to generate a "duplicate" condition (ABB)
            (image_blob_0100_name, self.raw_static_object_test_image_0050)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        self.assertEqual(1, results['person'])  # correct (only non-static item)
        self.assertEqual(0, results['car'])  # correct
        self.assertEqual(0, results['truck'])  # correct
        self.assertEqual(0, results['bus'])  # correct
        self.assertEqual(0, results['cyclist'])  # correct
        self.assertEqual(0, results['motorcyclist'])  # correct
        self.assertEqual(0, results['van'])  # correct
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    # previous, current, next images: A,A,B
    def test_preprocess_and_object_count_and_postprocess_copes_with_current_matches_previous_image(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test13'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test13'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test13'
        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_0040_name, self.raw_static_object_test_image_0040),
            # NOTE rudely reusing same image data to generate a "duplicate" condition (AAB)
            (image_blob_0050_name, self.raw_static_object_test_image_0040),
            (image_blob_0100_name, self.raw_static_object_test_image_0050)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        self.assertEqual(0, results['person'])
        self.assertEqual(0, results['car'])
        self.assertEqual(0, results['truck'])
        self.assertEqual(0, results['bus'])
        self.assertEqual(0, results['cyclist'])
        self.assertEqual(0, results['motorcyclist'])
        self.assertEqual(0, results['van'])
        self.assertEqual(False, results['missing'])
        self.assertEqual(True, results['faulty'])

    # previous, current, next images: A,A,A
    def test_preprocess_and_object_count_and_postprocess_copes_with_current_matches_previous_and_next_images(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test14'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test14'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test14'
        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            # NOTE rudely reusing same image data to generate a "duplicate" condition (AAA)
            (image_blob_0040_name, self.raw_static_object_test_image_0040),
            (image_blob_0050_name, self.raw_static_object_test_image_0040),
            (image_blob_0100_name, self.raw_static_object_test_image_0040)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        self.assertEqual(0, results['person'])
        self.assertEqual(0, results['car'])
        self.assertEqual(0, results['truck'])
        self.assertEqual(0, results['bus'])
        self.assertEqual(0, results['cyclist'])
        self.assertEqual(0, results['motorcyclist'])
        self.assertEqual(0, results['van'])
        self.assertEqual(False, results['missing'])
        self.assertEqual(True, results['faulty'])

    def test_preprocess_and_object_count_and_postprocess_copes_with_missing_previous_image(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test15'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test15'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test15'
        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_0040_name, None),
            (image_blob_0050_name, self.raw_static_object_test_image_0050),
            (image_blob_0100_name, self.raw_static_object_test_image_0100)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # reference "TfL-images-20200501-0050-00001.08859_filtered.png"
        self.assertEqual(1, results['person'])  # correct
        self.assertEqual(0, results['car'])  # correct (static objects removed)
        self.assertEqual(0, results['truck'])  # correct (static objects removed)
        self.assertEqual(0, results['bus'])  # correct (static objects removed)
        self.assertEqual(0, results['cyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['motorcyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['van'])  # correct (static objects removed)
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])

    def test_preprocess_and_object_count_and_postprocess_copes_with_missing_next_image(self):
        image_blob_0040_name = 'TfL-images/20200501/0040/00001.08859.jpg'
        image_blob_0050_name = 'TfL-images/20200501/0050/00001.08859.jpg'
        image_blob_0100_name = 'TfL-images/20200501/0100/00001.08859.jpg'

        fault_filter_blob_name = 'FaultyImageFilter-test16'
        fault_filter_configuration_json = f"""
        {{
            "identical_area_proportion_threshold": 0.33,
            "row_similarity_threshold": 0.8,
            "consecutive_matching_rows_threshold": 0.2,
            "stuff to ignore": "warned you"
        }}
        """

        object_detector_blob_name = 'Newcastle-test16'
        object_detector_serialised_graph_name = 'magic-3.pb'
        object_detector_configuration_json = f"""
        {{
            "serialized_graph_name": "{object_detector_serialised_graph_name}",
            "minimum_confidence": 0.33,
            "stuff to ignore": "warned you"
        }}
        """

        filter_blob_name = 'StaticObjectFilter-test16'
        static_filter_configuration_json = """
        {
            "scenecut_threshold": 0.4,
            "minimum_mask_proportion": 0.25,
            "minimum_mask_proportion_person": 0.10,
            "confidence_person": 0.80,
            "contour_area_threshold": 50
        }
        """

        main.data_bucket = create_mock_bucket([
            (image_blob_0040_name, self.raw_static_object_test_image_0040),
            (image_blob_0050_name, self.raw_static_object_test_image_0050),
            (image_blob_0100_name, None)
        ])

        main.model_bucket = create_mock_bucket([
            (f'{fault_filter_blob_name}/configuration.json', fault_filter_configuration_json),
            (f'{object_detector_blob_name}/configuration.json', object_detector_configuration_json),
            (f'{object_detector_blob_name}/{object_detector_serialised_graph_name}', self.rcnn_serialised_model),
            (filter_blob_name + '/configuration.json', static_filter_configuration_json)
        ])

        mock_request = create_mock_request({
            'image_blob_name': image_blob_0050_name,
            'model_blob_name': f'{fault_filter_blob_name}_{object_detector_blob_name}_{filter_blob_name}'
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)
        results = response['results']

        # reference "TfL-images-20200501-0050-00001.08859_filtered.png"
        self.assertEqual(1, results['person'])  # correct
        self.assertEqual(0, results['car'])  # correct (static objects removed)
        self.assertEqual(0, results['truck'])  # correct (static objects removed)
        self.assertEqual(0, results['bus'])  # correct (static objects removed)
        self.assertEqual(0, results['cyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['motorcyclist'])  # correct (static objects removed)
        self.assertEqual(0, results['van'])  # correct (static objects removed)
        self.assertEqual(False, results['missing'])
        self.assertEqual(False, results['faulty'])
