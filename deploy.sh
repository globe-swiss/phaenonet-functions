gcloud functions deploy process_activity --project phaenonet --entry-point process_activity_create --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/activities/{activity_id}" --trigger-event providers/cloud.firestore/eventTypes/document.create --region europe-west1

gcloud functions deploy process_observation --project phaenonet --entry-point process_observation_write --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/observations/{observation_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1

gcloud functions deploy process_user --project phaenonet --entry-point process_user_write --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/users/{user_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1

gcloud functions deploy import_meteoswiss_data --project phaenonet --entry-point import_meteoswiss_data_publish --runtime python37 --trigger-resource import_meteoswiss_data --trigger-event google.pubsub.topic.publish --timeout 540s --region europe-west1
gcloud scheduler jobs update pubsub import_meteoswiss_data --project phaenonet --schedule="5 1 * * *" --topic="import_meteoswiss_data" --message-body="none" --time-zone="Europe/Zurich" --description="Trigger cloud function to import meteoswiss data"

gcloud functions deploy create_thumbnails --project phaenonet --entry-point create_thumbnail_finalize --runtime python37 --trigger-resource "phaenonet.appspot.com" --trigger-event google.storage.object.finalize --timeout 540s --region europe-west1

# these function MUST NOT be deployed when initially importing data
gcloud functions deploy process_ts_user --project phaenonet --entry-point process_document_ts_write --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/users/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1
gcloud functions deploy process_ts_observation --project phaenonet --entry-point process_document_ts_write --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/observations/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1
gcloud functions deploy process_ts_individual --project phaenonet --entry-point process_document_ts_write --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/individuals/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1
