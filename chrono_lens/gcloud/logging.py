import logging
import os
import sys

# https://google-cloud-opentelemetry.readthedocs.io/en/latest/examples/cloud_trace_exporter/README.html#cloud-trace-exporter-example
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
# todo BatchExportSpanProcessor collapses the span hierarchy - bug in OpenTelemetry or Google Cloud export library
# instead use SimpleExportSpanProcessor, which will retain the hierarchy. namely:
#
# from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
#
# NOTE however it will generate trace logs serially in the same thread - it'll block the code being timed as an
# overhead, and trigger metric quotas. You'll see log messages such as:
# google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded for quota metric 'Write requests (free)'... etc.
#
# Raised as bug in ticket #639
from pythonjsonlogger.jsonlogger import JsonFormatter


class StackDriverJsonFormatter(JsonFormatter, object):
    def __init__(self, fmt="%(levelname) %(message)", style='%', *args, **kwargs):
        JsonFormatter.__init__(self, fmt=fmt, *args, **kwargs)

    def format(self, record):
        record.arguments = record.args
        return super(StackDriverJsonFormatter, self).format(record)

    def process_log_record(self, log_record):
        log_record['severity'] = log_record['levelname']
        del log_record['levelname']
        if log_record['severity'] in {'ERROR', 'CRITICAL'}:
            log_record['@type'] = 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent'
        if 'exc_info' in log_record:
            log_record['message'] = log_record.get('message') + '\n' + log_record.get('exc_info')
            del log_record['exc_info']
        return super(StackDriverJsonFormatter, self).process_log_record(log_record)


def setup_logging_and_trace():
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StackDriverJsonFormatter())
    logging.basicConfig(handlers=[handler], level=numeric_level)
    logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)

    trace.set_tracer_provider(TracerProvider())
    cloud_trace_exporter = CloudTraceSpanExporter()
    # trace.get_tracer_provider().add_span_processor(SimpleExportSpanProcessor(cloud_trace_exporter))
    trace.get_tracer_provider().add_span_processor(BatchExportSpanProcessor(cloud_trace_exporter))
