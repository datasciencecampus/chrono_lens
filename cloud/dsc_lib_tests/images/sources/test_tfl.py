from unittest import TestCase

from dsc_lib.images.sources.tfl import filter_image_urls


class TestTfL(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data = [
            {"$type": "ignored", "id": "JamCams_00000.00000",
             "url": "/Place/JamCams_00002.00865", "commonName": "Main Road East", "placeType": "JamCam",
             "additionalProperties": [
                 {"$type": "ignored",
                  "category": "payload", "key": "stuff", "sourceSystemKey": "JamCams", "value": "true",
                  "modified": "2020-03-29T17:48:29.367Z"},
                 {"$type": "ignored",
                  "category": "payload", "key": "imageUrl", "sourceSystemKey": "JamCams",
                  "value": "https://url.of.object/folder/00000.00000.jpg",
                  "modified": "2020-03-29T17:48:29.367Z"},
                 {"$type": "ignored",
                  "category": "payload", "key": "videoUrl", "sourceSystemKey": "JamCams",
                  "value": "https://url.of.object/folder/00000.00000.mp4",
                  "modified": "2020-03-29T17:48:29.367Z"},
                 {"$type": "ignored",
                  "category": "cameraView", "key": "view", "sourceSystemKey": "JamCams", "value": "West Facing",
                  "modified": "2020-03-29T17:48:29.367Z"}], "children": [], "childrenUrls": [], "lat": 1.2,
             "lon": 2.3},
            {"$type": "ignored", "id": "JamCams_00000.00001",
             "url": "/Place/JamCams_00002.00865", "commonName": "Some Other Avenue", "placeType": "JamCam",
             "additionalProperties": [
                 {"$type": "ignored",
                  "category": "payload", "key": "stuff", "sourceSystemKey": "JamCams", "value": "true",
                  "modified": "2020-03-29T17:48:29.367Z"},
                 {"$type": "ignored",
                  "category": "payload", "key": "imageUrl", "sourceSystemKey": "JamCams",
                  "value": "https://url.of.object/folder/00000.00001.test.jpg",
                  "modified": "2020-03-29T17:48:29.367Z"},
                 {"$type": "ignored",
                  "category": "payload", "key": "videoUrl", "sourceSystemKey": "JamCams",
                  "value": "https://url.of.object/folder/00000.00001.test.mp4",
                  "modified": "2020-03-29T17:48:29.367Z"},
                 {"$type": "ignored",
                  "category": "cameraView", "key": "view", "sourceSystemKey": "JamCams", "value": "West Facing",
                  "modified": "2020-03-29T17:48:29.367Z"}], "children": [], "childrenUrls": [], "lat": -70.1,
             "lon": 23.4}]

    def test_filter_image_urls(self):
        expected_results = [
            "https://url.of.object/folder/00000.00000.jpg",
            "https://url.of.object/folder/00000.00001.test.jpg",
        ]
        actual_results = filter_image_urls(self.test_data)

        self.assertListEqual(expected_results, actual_results)
