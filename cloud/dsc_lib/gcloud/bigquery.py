import re


def convert_model_name_to_table_name(model_blob_name: str) -> str:
    """
    Removes disallowed characters, leaving A-Z, a-z, 0-9 and replaces `#` with `_`
    to create an acceptable table name.

    Strips out disallowed characters according to
    https://cloud.google.com/bigquery/docs/reference/rest/v2/datasets#datasetreference

    "The ID must contain only letters (a-z, A-Z), numbers (0-9), or underscores (_).
     The maximum length is 1,024 characters."

    :param model_blob_name:
    :return: model_blob_name with only a-z, A-Z, 0-9 and _ characters
    """
    unfiltered_model_name = model_blob_name.split('/')[0]
    table_name = re.sub(r'\W+', '', unfiltered_model_name)
    return table_name
