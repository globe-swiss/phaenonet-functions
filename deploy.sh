export PROJECT=phaenonet-test

echo "Deploying $PROJECT"
pipenv lock --requirements > requirements.txt

if [ "$1" = 'all' ] || [ -z "$1" ]; then
  gcloud functions deploy process_observation_activity --project $PROJECT --entry-point process_observation_write_activity --runtime python38 --trigger-resource "projects/$PROJECT/databases/(default)/documents/observations/{observation_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2

  gcloud functions deploy process_observation_create_analytics --project $PROJECT --entry-point process_observation_create_analytics --runtime python38 --trigger-resource "projects/$PROJECT/databases/(default)/documents/observations/{observation_id}" --trigger-event providers/cloud.firestore/eventTypes/document.create --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2
  gcloud functions deploy process_observation_update_analytics --project $PROJECT --entry-point process_observation_update_analytics --runtime python38 --trigger-resource "projects/$PROJECT/databases/(default)/documents/observations/{observation_id}" --trigger-event providers/cloud.firestore/eventTypes/document.update --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2
  gcloud functions deploy process_observation_delete_analytics --project $PROJECT --entry-point process_observation_delete_analytics --runtime python38 --trigger-resource "projects/$PROJECT/databases/(default)/documents/observations/{observation_id}" --trigger-event providers/cloud.firestore/eventTypes/document.delete --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2

  gcloud functions deploy process_user --project $PROJECT --entry-point process_user_write --runtime python38 --trigger-resource "projects/$PROJECT/databases/(default)/documents/users/{user_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2

  gcloud functions deploy import_meteoswiss_data --project $PROJECT --entry-point import_meteoswiss_data_publish --runtime python38 --trigger-resource import_meteoswiss_data --trigger-event google.pubsub.topic.publish --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2
  gcloud scheduler jobs update pubsub import_meteoswiss_data --project $PROJECT --schedule="5 1 * * *" --topic="import_meteoswiss_data" --message-body="none" --time-zone="Europe/Zurich" --description="Trigger cloud function to import meteoswiss data" --quiet & sleep 2

  gcloud functions deploy create_thumbnails --project $PROJECT --entry-point create_thumbnail_finalize --runtime python38 --trigger-resource "$PROJECT.appspot.com" --trigger-event google.storage.object.finalize --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2

  gcloud functions deploy rollover_phenoyear --project $PROJECT --entry-point rollover_manual --runtime python38 --trigger-resource rollover_phenoyear --trigger-event google.pubsub.topic.publish --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2
fi

# these function MUST NOT be deployed when initially importing data
if [ "$1" = 'all' ] || [ "$1" = 'ts' ]; then
  gcloud functions deploy process_ts_user --project $PROJECT --entry-point process_document_ts_write --runtime python38 --trigger-resource "projects/$PROJECT/databases/(default)/documents/users/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1 --timeout 540s --quiet --env-vars-file env.$PROJECT.yaml & sleep 2
  gcloud functions deploy process_ts_observation --project $PROJECT --entry-point process_document_ts_write --runtime python38 --trigger-resource "projects/$PROJECT/databases/(default)/documents/observations/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2
  gcloud functions deploy process_ts_individual --project $PROJECT --entry-point process_document_ts_write --runtime python38 --trigger-resource "projects/$PROJECT/databases/(default)/documents/individuals/{document}" --trigger-event providers/cloud.firestore/eventTypes/document.write --timeout 540s --region europe-west1 --quiet --env-vars-file env.$PROJECT.yaml & sleep 2
fi
