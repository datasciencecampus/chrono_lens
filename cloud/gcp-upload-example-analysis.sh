#!/bin/bash
set -e

if [[ $# -ne 2 ]] ; then
    echo 'You must provide "[project id]" "[branch id]" as two arguments'
    exit 0
fi

# RCNN state is currently stored in test folder, as it is required to executed the unit tests
#echo "Downloading serialised Newcastle RCNN model ready to upload to bucket..."
#wget https://github.com/TomKomar/uo-object_counting/raw/26c9f29b46ba7afa6294934ab8326fd4d5f3418d/app/fig_frcnn_rebuscov-3.pb
#mv fig_frcnn_rebuscov-3.pb functions/count_objects/example-fig_frcnn_rebuscov-3.pb

echo "Populating models in GCP bucket 'gs://models-$1-$2/'"
gsutil cp functions/count_objects/example_faulty_image_detector_configuration.json gs://models-$1-$2/FaultyImageFilterV0/configuration.json
gsutil cp functions/count_objects/example_newcastle_model_configuration.json gs://models-$1-$2/NewcastleV0/configuration.json
#gsutil cp functions/count_objects/example-fig_frcnn_rebuscov-3.pb gs://models-$1-$2/NewcastleV0/fig_frcnn_rebuscov-3.pb
gsutil cp ../tests/test_data/test_detector_data/fig_frcnn_rebuscov-3.pb gs://models-$1-$2/NewcastleV0/fig_frcnn_rebuscov-3.pb
gsutil cp functions/count_objects/example_static_model_configuration.json gs://models-$1-$2/StaticObjectFilterV0/configuration.json

echo "Populating analysis configuration in GCP bucket 'gs://sources-$1-$2'"
gsutil cp functions/process_scheduled/exampleJSON/analyse-configuration.json gs://sources-$1-$2/analyse-configuration.json

echo "Populating analysis camera selection in GCP bucket 'gs://sources-$1-$2/analyse'"
gsutil cp functions/process_scheduled/exampleJSON/NETravelData-images.json gs://sources-$1-$2/analyse/NETravelData-images.json
gsutil cp functions/process_scheduled/exampleJSON/TfL-images.json gs://sources-$1-$2/analyse/TfL-images.json
