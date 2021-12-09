from unittest import TestCase

from chrono_lens.gcloud.bigquery import convert_model_name_to_table_name


class TestBigQuery(TestCase):

    def test_alphanumeric_key_hashes_replaced_with_underscores(self):
        model_blob_name = 'abc_dxyz ABC#DXYZ-=!@£$%^&*()_+{}[]:"|;\'\\<>?,.`\'~1234#567890/fish/fish.bin'
        # This isn't an authentication token etc. just a wide test of characters so safe to permit at commit
        # by pre-commit hook secrets.
        expected_table_name = 'abc_dxyzABCDXYZ_1234567890'  # pragma: allowlist secret

        actual_table_name = convert_model_name_to_table_name(model_blob_name)

        self.assertEqual(expected_table_name, actual_table_name)

    def test_example_use_case(self):
        model_blob_name = 'NewcastleV0_StaticMaskFilterV0'
        expected_table_name = 'NewcastleV0_StaticMaskFilterV0'

        actual_table_name = convert_model_name_to_table_name(model_blob_name)

        self.assertEqual(expected_table_name, actual_table_name)
