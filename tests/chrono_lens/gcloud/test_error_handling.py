import json
from unittest import TestCase
from urllib.error import URLError

from chrono_lens.gcloud.error_handling import report_exception


class TestReportException(TestCase):

    def test_wraps_simple_exception(self):
        e = Exception('test')
        variable_names_and_state = {'test': 'some text'}

        json_response = report_exception(e, variable_names_and_state, request=None, event=None, context=None)

        json_dict = json.loads(json_response)
        self.assertEqual('Errored', json_dict['STATUS'])
        self.assertEqual('Exception: test', json_dict['Message'])
        self.assertDictEqual(variable_names_and_state, json_dict['Arguments'])

    def test_wraps_simple_exception_with_int_argument(self):
        e = Exception(42)
        variable_names_and_state = {'test': 'some text'}

        json_response = report_exception(e, variable_names_and_state, request=None, event=None, context=None)

        json_dict = json.loads(json_response)
        self.assertEqual('Errored', json_dict['STATUS'])
        self.assertEqual('Exception: 42', json_dict['Message'])
        self.assertDictEqual(variable_names_and_state, json_dict['Arguments'])

    def test_wraps_simple_exception_with_float_argument(self):
        e = Exception(1.23)
        variable_names_and_state = {'test': 'some text'}

        json_response = report_exception(e, variable_names_and_state, request=None, event=None, context=None)

        json_dict = json.loads(json_response)
        self.assertEqual('Errored', json_dict['STATUS'])
        self.assertEqual('Exception: 1.23', json_dict['Message'])
        self.assertDictEqual(variable_names_and_state, json_dict['Arguments'])

    def test_wraps_url_error_wrapping_timeout_exception(self):
        e = URLError(TimeoutError())
        variable_names_and_state = {'test': 'some text'}

        json_response = report_exception(e, variable_names_and_state, request=None, event=None, context=None)

        json_dict = json.loads(json_response)
        self.assertEqual('Errored', json_dict['STATUS'])
        self.assertEqual('URLError: TimeoutError', json_dict['Message'])
        self.assertDictEqual(variable_names_and_state, json_dict['Arguments'])

    def test_reports_multiple_args(self):
        e = Exception('test', 12, 3.4, TimeoutError())
        variable_names_and_state = {'test': 'some text'}

        json_response = report_exception(e, variable_names_and_state, request=None, event=None, context=None)

        json_dict = json.loads(json_response)
        self.assertEqual('Errored', json_dict['STATUS'])
        self.assertEqual('Exception: test,12,3.4,TimeoutError', json_dict['Message'])
        self.assertDictEqual(variable_names_and_state, json_dict['Arguments'])
