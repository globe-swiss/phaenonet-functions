gcloud functions deploy process_activity --entry-point process_activity --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/activities/{activity_id}" --trigger-event providers/cloud.firestore/eventTypes/document.create --region europe-west1

gcloud functions deploy process_observation --entry-point process_observation --runtime python37 --trigger-resource "projects/phaenonet/databases/(default)/documents/observations/{observation_id}" --trigger-event providers/cloud.firestore/eventTypes/document.write --region europe-west1
