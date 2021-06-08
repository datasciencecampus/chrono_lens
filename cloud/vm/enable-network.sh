#!/usr/bin/env bash
VM_NAME="impute-seats"
ZONE="europe-west2-a"  # europe-west2-a has T4 GPUs if needs be
gcloud compute instances add-access-config ${VM_NAME} --zone ${ZONE}
