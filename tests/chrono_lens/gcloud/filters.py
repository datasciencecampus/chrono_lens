import os


def is_running_on_gcp():
    # if GCP_PROJECT and BUILD_ID are defined, assume we're in GCP
    if os.environ.get('GCP_PROJECT') and os.environ.get('BUILD_ID'):
        return True
    else:
        return False
