import json
import urllib.error
from datetime import datetime, timedelta
from io import StringIO
from os import environ
from unittest import TestCase, mock

import pytz

bogus_data_bucket_name = "rhubarb"

with mock.patch.dict(environ, {
    'DATA_BUCKET_NAME': bogus_data_bucket_name,
}):
    with mock.patch('google.cloud.storage.Client'):
        with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
            from main import sift_newcastle_cameras_latest_newer_than_datetime, distribute_ne_travel_data


class TestMain(TestCase):

    @mock.patch("main.urlopen")
    def test_sift_newcastle_cameras_latest_newer_than_datetime_filters_by_date(self, mock_urlopen):
        mock_urlopen.return_value = StringIO(json.dumps(self.fake_response_single_page))
        expected_name_url_tuples = [
            ("VAISALACCTV58",
             "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/VAISALACCTV58/20200714/145033.jpg"),
            ("GH_A167M1-View_01",
             "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/GH_A167M1/20200714/145319.jpg")
        ]

        name_url_tuples = sift_newcastle_cameras_latest_newer_than_datetime(self.ten_minutes_ago)

        self.assertSequenceEqual(expected_name_url_tuples, name_url_tuples)

    @mock.patch("main.urlopen")
    @mock.patch("main.sleep")
    def test_sift_newcastle_cameras_latest_newer_than_datetime_retries_if_server_error(self, _mock_sleep, mock_urlopen):
        # Handles "urllib.error.HTTPError: HTTP Error 500: Internal Server Error"
        self.failure_count = 0

        def single_failure(supplied_url):
            self.failure_count += 1

            if self.failure_count == 1:
                raise urllib.error.HTTPError(url=supplied_url, code=500, msg="Internal Server Error", hdrs=None,
                                             fp=None)

            return StringIO(json.dumps(self.fake_response_single_page))

        mock_urlopen.side_effect = single_failure

        expected_name_url_tuples = [
            ("VAISALACCTV58",
             "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/VAISALACCTV58/20200714/145033.jpg"),
            ("GH_A167M1",
             "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/GH_A167M1/20200714/130031.jpg"),
            ("GH_A167M1-View_01",
             "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/GH_A167M1/20200714/145319.jpg"),
            ("GH_A167M1-View_02",
             "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/GH_A167M1/20200714/145822.jpg")
        ]

        name_url_tuples = sift_newcastle_cameras_latest_newer_than_datetime(self.long_ago)

        self.assertSequenceEqual(expected_name_url_tuples, name_url_tuples)

    @mock.patch("main.urlopen")
    @mock.patch("main.sleep")
    def test_sift_newcastle_cameras_latest_newer_than_datetime_retries_if_server_error_max_5_times(self, _mock_sleep,
                                                                                                   mock_urlopen):
        # Handles "urllib.error.HTTPError: HTTP Error 500: Internal Server Error"
        self.failure_count = 0

        def single_failure(supplied_url):
            self.failure_count += 1
            raise urllib.error.HTTPError(url=supplied_url, code=500, msg="Internal Server Error", hdrs=None, fp=None)

        mock_urlopen.side_effect = single_failure

        expected_exception = urllib.error.HTTPError(
            url="https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity/?metric=%22Camera%20image%22&page=1",
            code=500, msg="Internal Server Error", hdrs=None, fp=None)

        try:
            _name_url_tuples = sift_newcastle_cameras_latest_newer_than_datetime(self.long_ago)
            self.fail("Didn't raise an exception after using all retries")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, expected_exception.code)
            self.assertEqual(e.filename, expected_exception.filename)
            self.assertEqual(e.msg, expected_exception.msg)
            self.assertEqual(e.reason, expected_exception.reason)
            self.assertEqual(5, self.failure_count)

    @mock.patch("main.urlopen")
    @mock.patch("main.sleep")
    @mock.patch("main.datetime")
    @mock.patch("main.run_async_downloads")
    @mock.patch("main.sift_newcastle_cameras_latest_newer_than_datetime")
    def test_sift_newcastle_cameras_latest_newer_than_datetime_rounds_down_to_nearest_10_mins(
            self, mock_sift_newcastle_cameras_latest_newer_than_datetime, mock_run_async_downloads,
            mock_datetime, _mock_sleep, mock_urlopen):

        expected_urls = ['dummy-url']
        expected_now = datetime(year=2000, month=1, day=1, hour=1, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC)
        expected_10_minutes_ago = datetime(year=2000, month=1, day=1, hour=0, minute=50, second=0, microsecond=0, tzinfo=pytz.UTC)

        mock_datetime.utcnow.return_value = datetime(year=2000, month=1, day=1, hour=1, minute=7)
        mock_sift_newcastle_cameras_latest_newer_than_datetime.return_value = expected_urls
        mock_urlopen.return_value = "hello"

        _response_json = distribute_ne_travel_data({}, None)

        mock_sift_newcastle_cameras_latest_newer_than_datetime.assert_called_with(expected_10_minutes_ago)
        mock_run_async_downloads.assert_called_with(expected_urls,
                                                    f'NETravelData-images/{expected_now:%Y%m%d}/{expected_now:%H%M}/')

    @mock.patch("main.urlopen")
    @mock.patch("main.sleep")
    @mock.patch("main.datetime")
    @mock.patch("main.run_async_downloads")
    @mock.patch("main.sift_newcastle_cameras_latest_newer_than_datetime")
    def test_sift_newcastle_cameras_latest_newer_than_datetime_rounds_down_to_nearest_10_mins_already_rounded(
            self, mock_sift_newcastle_cameras_latest_newer_than_datetime, mock_run_async_downloads,
            mock_datetime, _mock_sleep, mock_urlopen):

        expected_urls = ['dummy-url']
        expected_now = datetime(year=2000, month=1, day=1, hour=1, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC)
        expected_10_minutes_ago = datetime(year=2000, month=1, day=1, hour=0, minute=50, second=0, microsecond=0, tzinfo=pytz.UTC)

        mock_datetime.utcnow.return_value = datetime(year=2000, month=1, day=1, hour=1, minute=0)
        mock_sift_newcastle_cameras_latest_newer_than_datetime.return_value = expected_urls
        mock_urlopen.return_value = "hello"

        _response_json = distribute_ne_travel_data({}, None)

        mock_sift_newcastle_cameras_latest_newer_than_datetime.assert_called_with(expected_10_minutes_ago)
        mock_run_async_downloads.assert_called_with(expected_urls,
                                                    f'NETravelData-images/{expected_now:%Y%m%d}/{expected_now:%H%M}/')

    # def test_filter_image_urls(self):
    #     distribute_n_travel_data(None, None)

    ten_minutes_ago = datetime(year=1999, month=12, day=31, hour=1, minute=1, tzinfo=pytz.UTC)

    long_ago = datetime(year=1999, month=1, day=1, hour=1, minute=1, tzinfo=pytz.UTC)

    fake_response_single_page = {
        "pagination": {
            "pageNumber": 1,
            "pageSize": 10,
            "pageCount": 1,
            "total": 3
        },
        "items": [
            {
                "entityId": "f10f680a-84f2-4798-af66-d11224ec4167",
                "name": "Camera mounted at Durham - A689 Toronto - Addison Road / B1286",
                "meta": {
                    "area": "Durham",
                    "lookingAt": [
                        "A689 Toronto - Addison Road",
                        "B1286"
                    ]
                },
                "position": [],
                "feed": [
                    {
                        "feedId": "03590e8b-155d-4005-8986-d4416568c244",
                        "metric": "Camera image",
                        "hardwareId": None,
                        "meta": {},
                        "provider": None,
                        "hardware": None,
                        "technology": None,
                        "timeseries": [
                            {
                                "timeseriesId": "9dbeb13e-a28a-4f45-a56a-970e17c95ed2",
                                "unit": {
                                    "unitId": "a6aec035-0c4a-48a6-8150-5aa2cb3d0f12",
                                    "name": "JPEG Image"
                                },
                                "storage": {
                                    "storageId": 7,
                                    "name": "File",
                                    "suffix": None
                                },
                                "aggregation": [],
                                "derivatives": [],
                                "assessments": [],
                                "latest": {
                                    "time": (ten_minutes_ago + timedelta(minutes=9)).isoformat(),
                                    "duration": -20.025,
                                    "value": "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/VAISALACCTV58/20200714/145033.jpg"
                                },
                                "links": [
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/9dbeb13e-a28a-4f45-a56a-970e17c95ed2",
                                        "rel": "self"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/9dbeb13e-a28a-4f45-a56a-970e17c95ed2/historic",
                                        "rel": "archives"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/camera-mounted-at-durham-a689-toronto-addison-road-b1286/camera-image/raw",
                                        "rel": "self.friendly"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/camera-mounted-at-durham-a689-toronto-addison-road-b1286/camera-image/raw/historic",
                                        "rel": "archives.friendly"
                                    }
                                ]
                            }
                        ],
                        "brokerage": [
                            {
                                "brokerageId": "35f50048-5cf3-441c-a305-a18c99a04a93",
                                "sourceId": "VAISALACCTV58",
                                "meta": {},
                                "broker": {
                                    "brokerId": "87365c1c-a2ff-4376-8f27-4ba8613bcd38",
                                    "name": "UTMC Open Camera Feeds",
                                    "active": False,
                                    "meta": None
                                }
                            }
                        ],
                        "service": [],
                        "isRestricted": False,
                        "links": [
                            {
                                "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/feed/03590e8b-155d-4005-8986-d4416568c244",
                                "rel": "self"
                            },
                            {
                                "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/feed/camera-mounted-at-durham-a689-toronto-addison-road-b1286/camera-image",
                                "rel": "self.friendly"
                            }
                        ]
                    }
                ],
                "links": [
                    {
                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity/f10f680a-84f2-4798-af66-d11224ec4167",
                        "rel": "self"
                    },
                    {
                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity/camera-mounted-at-durham-a689-toronto-addison-road-b1286",
                        "rel": "self.friendly"
                    }
                ]
            },
            {
                "entityId": "7daf7f7e-60e0-47b5-bc9f-9448c18df5f4",
                "name": "Camera mounted at Gateshead - A167 Durham Road / A1 J66 Angel of the North (North)",
                "meta": {
                    "area": "Gateshead",
                    "lookingAt": [
                        "A167 Durham Road",
                        "A1 J66 Angel of the North (North)"
                    ]
                },
                "position": [],
                "feed": [
                    {
                        "feedId": "d1926390-7cc2-4ebc-9307-513e4aa79d70",
                        "metric": "Camera image",
                        "hardwareId": None,
                        "meta": {},
                        "provider": None,
                        "hardware": None,
                        "technology": None,
                        "timeseries": [
                            {
                                "timeseriesId": "e5836d10-3b34-4087-9812-508ca190cd09",
                                "unit": {
                                    "unitId": "a6aec035-0c4a-48a6-8150-5aa2cb3d0f12",
                                    "name": "JPEG Image"
                                },
                                "storage": {
                                    "storageId": 7,
                                    "name": "File",
                                    "suffix": None
                                },
                                "aggregation": [],
                                "derivatives": [],
                                "assessments": [],
                                "latest": {
                                    "time": (ten_minutes_ago - timedelta(minutes=1)).isoformat(),
                                    "duration": -20.016,
                                    "value": "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/GH_A167M1/20200714/130031.jpg"
                                },
                                "links": [
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/e5836d10-3b34-4087-9812-508ca190cd09",
                                        "rel": "self"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/e5836d10-3b34-4087-9812-508ca190cd09/historic",
                                        "rel": "archives"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image/raw",
                                        "rel": "self.friendly"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image/raw/historic",
                                        "rel": "archives.friendly"
                                    }
                                ]
                            }
                        ],
                        "brokerage": [
                            {
                                "brokerageId": "04d4d719-e41f-45cd-8c46-c9ec10a71ea8",
                                "sourceId": "GH_A167M1",
                                "meta": {},
                                "broker": {
                                    "brokerId": "87365c1c-a2ff-4376-8f27-4ba8613bcd38",
                                    "name": "UTMC Open Camera Feeds",
                                    "active": False,
                                    "meta": None
                                }
                            }
                        ],
                        "service": [],
                        "isRestricted": False,
                        "links": [
                            {
                                "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/feed/d1926390-7cc2-4ebc-9307-513e4aa79d70",
                                "rel": "self"
                            },
                            {
                                "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/feed/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image",
                                "rel": "self.friendly"
                            }
                        ]
                    },
                    {
                        "feedId": "191def60-3cd0-4dbb-a6d6-acd35c3467c6",
                        "metric": "Camera image: View 01",
                        "hardwareId": None,
                        "meta": {
                            "viewId": 0
                        },
                        "provider": None,
                        "hardware": None,
                        "technology": None,
                        "timeseries": [
                            {
                                "timeseriesId": "6d75a79d-bcfb-4e1f-91d1-0377a7557f6b",
                                "unit": {
                                    "unitId": "a6aec035-0c4a-48a6-8150-5aa2cb3d0f12",
                                    "name": "JPEG Image"
                                },
                                "storage": {
                                    "storageId": 7,
                                    "name": "File",
                                    "suffix": None
                                },
                                "aggregation": [],
                                "derivatives": [],
                                "assessments": [],
                                "latest": {
                                    "time": (ten_minutes_ago + timedelta(minutes=2)).isoformat(),
                                    "duration": -20.007,
                                    "value": "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/GH_A167M1/20200714/145319.jpg"
                                },
                                "links": [
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/6d75a79d-bcfb-4e1f-91d1-0377a7557f6b",
                                        "rel": "self"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/6d75a79d-bcfb-4e1f-91d1-0377a7557f6b/historic",
                                        "rel": "archives"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image-view-01/raw",
                                        "rel": "self.friendly"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image-view-01/raw/historic",
                                        "rel": "archives.friendly"
                                    }
                                ]
                            }
                        ],
                        "brokerage": [
                            {
                                "brokerageId": "74203c75-607d-46b9-accf-9d84556701e9",
                                "sourceId": "GH_A167M1:V01",
                                "meta": {},
                                "broker": {
                                    "brokerId": "87365c1c-a2ff-4376-8f27-4ba8613bcd38",
                                    "name": "UTMC Open Camera Feeds",
                                    "active": False,
                                    "meta": None
                                }
                            }
                        ],
                        "service": [],
                        "isRestricted": False,
                        "links": [
                            {
                                "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/feed/191def60-3cd0-4dbb-a6d6-acd35c3467c6",
                                "rel": "self"
                            },
                            {
                                "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/feed/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image-view-01",
                                "rel": "self.friendly"
                            }
                        ]
                    },
                    {
                        "feedId": "8b0440c0-1b74-4061-be98-e853c1039ab7",
                        "metric": "Camera image: View 02",
                        "hardwareId": None,
                        "meta": {
                            "viewId": 1
                        },
                        "provider": None,
                        "hardware": None,
                        "technology": None,
                        "timeseries": [
                            {
                                "timeseriesId": "b4c6ef9c-c9b5-43f7-b169-c4d0c571a72b",
                                "unit": {
                                    "unitId": "a6aec035-0c4a-48a6-8150-5aa2cb3d0f12",
                                    "name": "JPEG Image"
                                },
                                "storage": {
                                    "storageId": 7,
                                    "name": "File",
                                    "suffix": None
                                },
                                "aggregation": [],
                                "derivatives": [],
                                "assessments": [],
                                "latest": {
                                    "time": (ten_minutes_ago - timedelta(minutes=2)).isoformat(),
                                    "duration": -20.007,
                                    "value": "https://file.newcastle.urbanobservatory.ac.uk/camera-feeds/GH_A167M1/20200714/145822.jpg"
                                },
                                "links": [
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/b4c6ef9c-c9b5-43f7-b169-c4d0c571a72b",
                                        "rel": "self"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/b4c6ef9c-c9b5-43f7-b169-c4d0c571a72b/historic",
                                        "rel": "archives"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image-view-02/raw",
                                        "rel": "self.friendly"
                                    },
                                    {
                                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/timeseries/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image-view-02/raw/historic",
                                        "rel": "archives.friendly"
                                    }
                                ]
                            }
                        ],
                        "brokerage": [
                            {
                                "brokerageId": "e9a17779-45b5-4502-8016-acd7857161b5",
                                "sourceId": "GH_A167M1:V02",
                                "meta": {},
                                "broker": {
                                    "brokerId": "87365c1c-a2ff-4376-8f27-4ba8613bcd38",
                                    "name": "UTMC Open Camera Feeds",
                                    "active": False,
                                    "meta": None
                                }
                            }
                        ],
                        "service": [],
                        "isRestricted": False,
                        "links": [
                            {
                                "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/feed/8b0440c0-1b74-4061-be98-e853c1039ab7",
                                "rel": "self"
                            },
                            {
                                "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/feed/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)/camera-image-view-02",
                                "rel": "self.friendly"
                            }
                        ]
                    }
                ],
                "links": [
                    {
                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity/7daf7f7e-60e0-47b5-bc9f-9448c18df5f4",
                        "rel": "self"
                    },
                    {
                        "href": "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity/camera-mounted-at-gateshead-a167-durham-road-a1-j66-angel-of-the-north-(north)",
                        "rel": "self.friendly"
                    }
                ]
            },
        ]
    }
