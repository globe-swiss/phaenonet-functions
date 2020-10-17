export PROJECT=phaenonet-test

if [ "$1" = 'all' ] || [ -z "$1" ]; then
  gcloud functions delete process_observation_activity --project $PROJECT --region europe-west1 --quiet
  
  gcloud functions delete process_observation_create_analytics --project $PROJECT --region europe-west1 --quiet
  gcloud functions delete process_observation_update_analytics --project $PROJECT --region europe-west1 --quiet
  gcloud functions delete process_observation_delete_analytics --project $PROJECT --region europe-west1 --quiet

  gcloud functions delete process_user --project $PROJECT --region europe-west1 --quiet

  gcloud functions delete import_meteoswiss_data --project $PROJECT --region europe-west1 --quiet

  gcloud functions delete create_thumbnails --project $PROJECT --region europe-west1 --quiet

  gcloud functions delete rollover_phenoyear --project $PROJECT --region europe-west1 --quiet

  # only ever deployed to test instance
  if [ "$PROJECT" = 'phaenonet-test' ]; then
    gcloud functions delete e2e_clear_individuals --project $PROJECT --region europe-west1 --quiet
  fi
fi

if [ "$1" = 'all' ] || [ "$1" = 'ts' ]; then
  gcloud functions delete process_ts_user --project $PROJECT --region europe-west1 --quiet
  gcloud functions delete process_ts_observation --project $PROJECT --region europe-west1 --quiet
  gcloud functions delete process_ts_individual --project $PROJECT --region europe-west1 --quiet
fi