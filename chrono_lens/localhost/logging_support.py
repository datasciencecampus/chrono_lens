import logging
import os
import sys


def setup_logging():
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    handler = logging.StreamHandler(sys.stdout)
    # handler.setFormatter(StackDriverJsonFormattersonFormatter())
    logging.basicConfig(handlers=[handler], level=numeric_level)
