import json
import os.path

from pprint import pprint

from googleapiclient import discovery
import google.auth

from dsc_lib.error_handling import report_exception

gcloud_region = os.environ.get('FUNCTION_REGION', '')  # Built-in env var
gcloud_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var


def start_vm(event, context):
    """Background Cloud Function to be triggered by Pub/Sub.
    Args:
         event (dict):  The dictionary with data specific to this type of
         event. The `data` field contains the PubsubMessage message. The
         `attributes` field will contain custom attributes if there are any.

         context (google.cloud.functions.Context): The Cloud Functions event
         metadata. The `event_id` field contains the Pub/Sub message ID. The
         `timestamp` field contains the publish time.
    """
    vm_instance_name = None
    vm_zone_name = None

    try:
        vm_instance_name = os.environ.get('VM_INSTANCE_NAME')
        vm_zone_name = os.environ.get('VM_ZONE_NAME')

        credentials, project = google.auth.default()

        service = discovery.build('compute', 'v1', credentials=credentials)

        request = service.instances().start(project=gcloud_project, zone=vm_zone_name, instance=vm_instance_name)
        response = request.execute()

        pprint(response)

        return json.dumps({'STATUS': 'OK'})

    except Exception as e:
        return report_exception(e,
                                {'vm_instance_name': vm_instance_name,
                                 'vm_zone_name': vm_zone_name},
                                event=event, context=context)
