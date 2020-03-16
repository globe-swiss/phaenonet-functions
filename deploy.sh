gcloud functions deploy process_activity --entry-point process_activity --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/activities/{activity_id}" --trigger-event providers/cloud.firestore/eventTypes/document.create --region europe-west1

gcloud functions deploy process_observation --entry-point process_observation --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/observations/{observation_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1

gcloud functions deploy process_user_nickname --entry-point process_user_nickname --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/users/{user_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1

gcloud functions deploy import_meteoswiss_data --entry-point import_meteoswiss_data --runtime python37 --trigger-resource import_meteoswiss_data --trigger-event google.pubsub.topic.publish --timeout 540s --region europe-west1
gcloud scheduler jobs update pubsub process_calendars --schedule="5 1 * * *" --topic="import_meteoswiss_data" --message-body="none" --time-zone="Europe/Zurich" --description="Trigger cloud function to import meteoswiss data"

# these function MUST NOT be deployed when initially importing data
gcloud functions deploy process_ts_user --entry-point process_document_ts --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/users/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1
gcloud functions deploy process_ts_observation --entry-point process_document_ts --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/observations/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1
gcloud functions deploy process_ts_individual --entry-point process_document_ts --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/individuals/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1
