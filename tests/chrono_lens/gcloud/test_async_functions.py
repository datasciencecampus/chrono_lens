import asyncio
from unittest import TestCase, mock

from aiohttp import ServerDisconnectedError
from testfixtures import LogCapture

from chrono_lens.gcloud.async_functions import run_cloud_function_async_with_parameter_list, MAXIMUM_NUMBER_OF_ATTEMPTS


class MockResponse:
    def __init__(self, status, response_text):
        self.status = status
        self.response_text = response_text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return

    async def text(self):
        return self.response_text


async def mock_sleep(delay, result=None, *, loop=None):
    """
    Masquerades as the real "sleep" function in asyncio,
    so we don't delay for real in tests...

    :param delay:
    :param result:
    :param loop:
    :return:
    """
    return result


class TestRunCloudFunctionAsyncWithParameterList(TestCase):

    def setUp(self):
        self.log_capture = LogCapture()

    def tearDown(self):
        self.log_capture.uninstall()

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_triggered_for_every_entry_no_failures(self, _mock_requests, mock_aiohttp):
        expected_end_point = f'https://fake-function.com/test'
        expected_json_key = 'iterated_key'
        expected_json_values = ['A', 'B']
        expected_partial_json = {'otherThings': 'stuff'}

        failures_to_trigger = 2
        success_text = "good"

        class MockSession:
            def __init__(self):
                self.calls_made = []
                self.failures_to_trigger = failures_to_trigger

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def post(self, url, json):
                self.calls_made.append((url, json))
                return MockResponse(200, f'{{"STATUS": "{success_text}"}}')

        mock_session = MockSession()
        mock_aiohttp.ClientSession.return_value = mock_session

        results = run_cloud_function_async_with_parameter_list(expected_json_key, expected_json_values,
                                                               expected_partial_json, expected_end_point)

        self.assertEqual(len(expected_json_values), len(results))

        for call_made in mock_session.calls_made:
            self.assertEqual(expected_end_point, call_made[0])

        self.log_capture.check_present(
            ('root', 'DEBUG', f"Processing: \"{expected_json_key}\": \"A\" with {{'otherThings': 'stuff'}}"),
            ('root', 'DEBUG',
             f"Completed attempt#0: \"{expected_json_key}\": \"A\"; response=\"{{'STATUS': 'good'}}\"; elapsed time 0.00s"),
            ('root', 'DEBUG', f"Processing: \"{expected_json_key}\": \"B\" with {{'otherThings': 'stuff'}}"),
            ('root', 'DEBUG',
             f"Completed attempt#0: \"{expected_json_key}\": \"B\"; response=\"{{'STATUS': 'good'}}\"; elapsed time 0.00s")
        )

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.async_functions.asyncio')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_triggered_for_every_entry_maximum_system_failures(self, _mock_requests, mock_asyncio,
                                                                        mock_aiohttp):
        mock_asyncio.run.side_effect = asyncio.run
        mock_asyncio.gather.side_effect = asyncio.gather
        mock_asyncio.sleep.side_effect = mock_sleep

        expected_end_point = f'https://fake-function.com/test'
        expected_json_key = 'iterated_key'
        expected_json_values = ['A', 'B']
        expected_partial_json = {'otherThings': 'stuff'}

        class MockSession:
            def __init__(self):
                self.calls_made = []
                self.initial_successes_to_trigger = 1
                self.failures_to_trigger = MAXIMUM_NUMBER_OF_ATTEMPTS

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def post(self, url, json):
                self.calls_made.append((url, json))
                if self.initial_successes_to_trigger > 0:
                    self.initial_successes_to_trigger -= 1
                    return MockResponse(200, '{"STATUS": "OK"}')
                elif self.failures_to_trigger > 0:
                    self.failures_to_trigger -= 1
                    return MockResponse(404, 'triggered error')
                else:
                    return MockResponse(200, '{"STATUS": "OK"}')

        mock_session = MockSession()
        mock_aiohttp.ClientSession.return_value = mock_session

        # json_key, json_values, partial_json, endpoint
        results = run_cloud_function_async_with_parameter_list(expected_json_key, expected_json_values,
                                                               expected_partial_json, expected_end_point)

        self.assertEqual(len(expected_json_values), len(results))
        self.assertEqual('OK', results[0]['STATUS'])
        self.assertEqual('Errored', results[1]['STATUS'])
        self.assertEqual(f'Failed after {MAXIMUM_NUMBER_OF_ATTEMPTS} attempts with "{expected_json_values[1]}"',
                         results[1]['Message'])
        # 1st call succeeded, 2nd call had MAXIMUM_NUMBER_OF_RETRIES failures...
        self.assertEqual(1 + MAXIMUM_NUMBER_OF_ATTEMPTS, len(mock_session.calls_made))

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.async_functions.asyncio')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_triggered_for_every_entry_do_not_retry_authorisation_failures(self, _mock_requests, mock_asyncio,
                                                                                    mock_aiohttp):
        mock_asyncio.run.side_effect = asyncio.run
        mock_asyncio.gather.side_effect = asyncio.gather
        mock_asyncio.sleep.side_effect = mock_sleep

        expected_end_point = f'https://fake-function.com/test'
        expected_json_key = 'iterated_key'
        expected_json_values = ['A', 'B']
        expected_partial_json = {'otherThings': 'stuff'}

        error_message = 'You are not authorized to access this resource'

        class MockSession:
            def __init__(self):
                self.calls_made = []
                self.initial_successes_to_trigger = 1

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def post(self, url, json):
                self.calls_made.append((url, json))
                return MockResponse(403, error_message)

        mock_session = MockSession()
        mock_aiohttp.ClientSession.return_value = mock_session

        results = run_cloud_function_async_with_parameter_list(expected_json_key, expected_json_values,
                                                               expected_partial_json, expected_end_point)

        self.assertEqual(len(expected_json_values), len(results))

        for index, json_value in enumerate(expected_json_values):
            self.assertEqual('Errored', results[index]['STATUS'])
            self.assertEqual(f'Forbidden - not authorised with "{json_value}"', results[index]['Message'])
            self.assertEqual(error_message, results[index]['TextResponse'])

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.async_functions.asyncio')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_triggered_for_every_entry_maximum_soft_errors(self, _mock_requests, mock_asyncio, mock_aiohttp):
        mock_asyncio.run.side_effect = asyncio.run
        mock_asyncio.gather.side_effect = asyncio.gather
        mock_asyncio.sleep.side_effect = mock_sleep

        expected_end_point = f'https://fake-function.com/test'
        expected_json_key = 'iterated_key'
        expected_json_values = ['A', 'B']
        expected_partial_json = {'otherThings': 'stuff'}

        class MockSession:
            def __init__(self):
                self.calls_made = []
                self.initial_successes_to_trigger = 1
                self.failures_to_trigger = MAXIMUM_NUMBER_OF_ATTEMPTS

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def post(self, url, json):
                self.calls_made.append((url, json))
                if self.initial_successes_to_trigger > 0:
                    self.initial_successes_to_trigger -= 1
                    return MockResponse(200, '{"STATUS": "OK"}')
                elif self.failures_to_trigger > 0:
                    self.failures_to_trigger -= 1
                    return MockResponse(200, '{"STATUS": "Errored", "Message": "Oops"}')
                else:
                    return MockResponse(200, '{"STATUS": "OK"}')

        mock_session = MockSession()
        mock_aiohttp.ClientSession.return_value = mock_session

        # json_key, json_values, partial_json, endpoint
        results = run_cloud_function_async_with_parameter_list(expected_json_key, expected_json_values,
                                                               expected_partial_json, expected_end_point)

        self.assertEqual(len(expected_json_values), len(results))
        self.assertEqual('OK', results[0]['STATUS'])
        self.assertEqual('Errored', results[1]['STATUS'])
        # 1st call succeeded, 2nd call did not retry as error was cleanly reported...
        self.assertEqual(2, len(mock_session.calls_made))

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.async_functions.asyncio')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_triggered_for_every_entry_less_than_maximum_soft_and_system_errors(self, _mock_requests,
                                                                                         mock_asyncio, mock_aiohttp):
        mock_asyncio.run.side_effect = asyncio.run
        mock_asyncio.gather.side_effect = asyncio.gather
        mock_asyncio.sleep.side_effect = mock_sleep

        expected_end_point = f'https://fake-function.com/test'
        expected_json_key = 'iterated_key'
        expected_json_values = ['A', 'B']
        expected_partial_json = {'otherThings': 'stuff'}

        class MockSession:
            def __init__(self):
                self.calls_made = []
                self.initial_successes_to_trigger = 1
                self.soft_failures_to_trigger = MAXIMUM_NUMBER_OF_ATTEMPTS - 3
                self.system_failures_to_trigger = 2

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def post(self, url, json):
                self.calls_made.append((url, json))
                if self.initial_successes_to_trigger > 0:
                    self.initial_successes_to_trigger -= 1
                    return MockResponse(200, '{"STATUS": "OK", "OtherGubbins": {"type": "initial success"} }')
                elif self.soft_failures_to_trigger > 0:
                    self.soft_failures_to_trigger -= 1
                    return MockResponse(408, '{"STATUS": "Errored"}')
                elif self.system_failures_to_trigger > 0:
                    self.system_failures_to_trigger -= 1
                    return MockResponse(404, 'system error')
                else:
                    return MockResponse(200, '{"STATUS": "OK", "OtherGubbins": {"type": "later success"} }')

        mock_session = MockSession()
        mock_aiohttp.ClientSession.return_value = mock_session

        # json_key, json_values, partial_json, endpoint
        results = run_cloud_function_async_with_parameter_list(expected_json_key, expected_json_values,
                                                               expected_partial_json, expected_end_point)

        self.assertEqual(len(expected_json_values), len(results))

        self.assertEqual('OK', results[0]['STATUS'])
        self.assertEqual('initial success', results[0]['OtherGubbins']['type'])

        self.assertEqual('OK', results[1]['STATUS'])
        self.assertEqual('later success', results[1]['OtherGubbins']['type'])

        # 1st call succeeded, 2nd call had MAXIMUM_NUMBER_OF_RETRIES-1 failures and then finally a success
        self.assertEqual(1 + MAXIMUM_NUMBER_OF_ATTEMPTS, len(mock_session.calls_made))

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.async_functions.asyncio')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_triggered_for_every_entry_less_than_maximum_retries_socket_errors(self, _mock_requests,
                                                                                        mock_asyncio, mock_aiohttp):
        mock_asyncio.run.side_effect = asyncio.run
        mock_asyncio.gather.side_effect = asyncio.gather
        mock_asyncio.sleep.side_effect = mock_sleep

        expected_end_point = f'https://fake-function.com/test'
        expected_json_key = 'iterated_key'
        expected_json_values = ['A', 'B']
        expected_partial_json = {'otherThings': 'stuff'}

        class MockSession:
            def __init__(self):
                self.calls_made = []
                self.initial_successes_to_trigger = 1
                self.soft_failures_to_trigger = MAXIMUM_NUMBER_OF_ATTEMPTS - 3
                self.system_failures_to_trigger = 2

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def post(self, url, json):
                self.calls_made.append((url, json))
                if self.initial_successes_to_trigger > 0:
                    self.initial_successes_to_trigger -= 1
                    return MockResponse(200, '{"STATUS": "OK", "OtherGubbins": {"type": "initial success"} }')
                elif self.soft_failures_to_trigger > 0:
                    self.soft_failures_to_trigger -= 1
                    return MockResponse(200, '{"STATUS": "Errored", "Message": "ConnectionError: ouch!"}')
                elif self.system_failures_to_trigger > 0:
                    self.system_failures_to_trigger -= 1
                    return MockResponse(404, 'system error')
                else:
                    return MockResponse(200, '{"STATUS": "OK", "OtherGubbins": {"type": "later success"} }')

        mock_session = MockSession()
        mock_aiohttp.ClientSession.return_value = mock_session

        # json_key, json_values, partial_json, endpoint
        results = run_cloud_function_async_with_parameter_list(expected_json_key, expected_json_values,
                                                               expected_partial_json, expected_end_point)

        self.assertEqual(len(expected_json_values), len(results))

        self.assertEqual('OK', results[0]['STATUS'])
        self.assertEqual('initial success', results[0]['OtherGubbins']['type'])

        self.assertEqual('OK', results[1]['STATUS'])
        self.assertEqual('later success', results[1]['OtherGubbins']['type'])

        # 1st call succeeded, 2nd call had MAXIMUM_NUMBER_OF_RETRIES-1 failures and then finally a success
        self.assertEqual(1 + MAXIMUM_NUMBER_OF_ATTEMPTS, len(mock_session.calls_made))

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.async_functions.asyncio')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_retries_if_request_raised_errors(self, _mock_requests,
                                                       mock_asyncio, mock_aiohttp):
        mock_asyncio.run.side_effect = asyncio.run
        mock_asyncio.gather.side_effect = asyncio.gather
        mock_asyncio.sleep.side_effect = mock_sleep

        expected_end_point = f'https://fake-function.com/test'
        expected_json_key = 'iterated_key'
        expected_json_values = ['A', 'B']
        expected_partial_json = {'otherThings': 'stuff'}

        class MockSession:
            def __init__(self):
                self.calls_made = []
                self.initial_successes_to_trigger = 1
                self.soft_failures_to_trigger = MAXIMUM_NUMBER_OF_ATTEMPTS - 3
                self.hard_failures_to_trigger = 2

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def post(self, url, json):
                self.calls_made.append((url, json))
                if self.initial_successes_to_trigger > 0:
                    self.initial_successes_to_trigger -= 1
                    return MockResponse(200, '{"STATUS": "OK", "OtherGubbins": {"type": "initial success"} }')
                elif self.soft_failures_to_trigger > 0:
                    self.soft_failures_to_trigger -= 1
                    return MockResponse(200, '{"STATUS": "Errored", "Message": "ConnectionError: ouch!"}')
                elif self.hard_failures_to_trigger > 0:
                    self.hard_failures_to_trigger -= 1
                    raise ServerDisconnectedError("Server disconnected")
                else:
                    return MockResponse(200, '{"STATUS": "OK", "OtherGubbins": {"type": "later success"} }')

        mock_session = MockSession()
        mock_aiohttp.ClientSession.return_value = mock_session

        # json_key, json_values, partial_json, endpoint
        results = run_cloud_function_async_with_parameter_list(expected_json_key, expected_json_values,
                                                               expected_partial_json, expected_end_point)

        self.assertEqual(len(expected_json_values), len(results))

        self.assertEqual('OK', results[0]['STATUS'])
        self.assertEqual('initial success', results[0]['OtherGubbins']['type'])

        self.assertEqual('OK', results[1]['STATUS'])
        self.assertEqual('later success', results[1]['OtherGubbins']['type'])

        # 1st call succeeded, 2nd call had MAXIMUM_NUMBER_OF_RETRIES-1 failures and then finally a success
        self.assertEqual(1 + MAXIMUM_NUMBER_OF_ATTEMPTS, len(mock_session.calls_made))
