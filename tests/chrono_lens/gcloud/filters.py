import os

import pytest


def is_running_on_gcp():
    # if GCP_PROJECT and BUILD_ID are defined, assume we're in GCP
    if os.environ.get('GCP_PROJECT') and os.environ.get('BUILD_ID'):
        return True
    else:
        return False


pytestmark = pytest.mark.skipif(is_running_on_gcp(), reason="Skipping as not running on GCP")
