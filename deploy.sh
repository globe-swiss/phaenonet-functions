export PROJECT=phaenonet-test

if [ "$1" = 'all' ] || [ -z "$1" ]; then
  gcloud functions deploy process_activity --project $PROJECT --entry-point process_activity_create --runtime python37 --trigger-resource "projects/$PROJECT/databases/(default)/documents/activities/{activity_id}" --trigger-event providers/cloud.firestore/eventTypes/document.create --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml
  gcloud functions deploy process_observation --project $PROJECT --entry-point process_observation_write --runtime python37 --trigger-resource "projects/$PROJECT/databases/(default)/documents/observations/{observation_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml
  gcloud functions deploy process_user --project $PROJECT --entry-point process_user_write --runtime python37 --trigger-resource "projects/$PROJECT/databases/(default)/documents/users/{user_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml

  gcloud functions deploy import_meteoswiss_data --project $PROJECT --entry-point import_meteoswiss_data_publish --runtime python37 --trigger-resource import_meteoswiss_data --trigger-event google.pubsub.topic.publish --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml
  gcloud scheduler jobs update pubsub import_meteoswiss_data --project $PROJECT --schedule="5 1 * * *" --topic="import_meteoswiss_data" --message-body="none" --time-zone="Europe/Zurich" --description="Trigger cloud function to import meteoswiss data" --quiet --env-vars-file env.$PROJECT.yaml

  gcloud functions deploy create_thumbnails --project $PROJECT --entry-point create_thumbnail_finalize --runtime python37 --trigger-resource "$PROJECT.appspot.com" --trigger-event google.storage.object.finalize --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml
fi

# these function MUST NOT be deployed when initially importing data
if [ "$1" = 'all' ] || [ "$1" = 'ts' ]; then
  gcloud functions deploy process_ts_user --project $PROJECT --entry-point process_document_ts_write --runtime python37 --trigger-resource "projects/$PROJECT/databases/(default)/documents/users/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml
  gcloud functions deploy process_ts_observation --project $PROJECT --entry-point process_document_ts_write --runtime python37 --trigger-resource "projects/$PROJECT/databases/(default)/documents/observations/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml
  gcloud functions deploy process_ts_individual --project $PROJECT --entry-point process_document_ts_write --runtime python37 --trigger-resource "projects/$PROJECT/databases/(default)/documents/individuals/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml
fi