# Phaenonet Cloud Functions [![build](https://img.shields.io/github/workflow/status/globe-swiss/phaenonet-functions/Build%20and%20test)](undefined) [![codecov](https://codecov.io/gh/globe-swiss/phaenonet-functions/branch/master/graph/badge.svg?token=K45OXCML80)](undefined)

## Deploy Cloud Functions

Use [Github Actions](https://github.com/globe-swiss/phaenonet-functions/actions?query=workflow%3A%22deploy+cloud+functions%22) to manage cloud functions. Deployment actions are configured in `.github/workflows/deploy.yml`.

### Set export scheduer

```commandline
gcloud scheduler jobs update pubsub import_meteoswiss_data --project $PROJECT --schedule="5 1 * * *" --topic="import_meteoswiss_data" --message-body="none" --time-zone="Europe/Zurich" --description="Trigger cloud function to import meteoswiss data"
```

## Update Data for Testing/Development

Instructions to update data-sets in the Firestore test instance from production.

### Activate service accounts

List activated and active accounts: `gcloud auth list`

Service accounts need only to be activated once:

```commandline
gcloud --project=phaenonet-test auth activate-service-account firestore-backup@phaenonet-test.iam.gserviceaccount.com --key-file=[key_file]
gcloud --project=phaenonet auth activate-service-account firestore-backup@phaenonet.iam.gserviceaccount.com --key-file=[key_file]
```

### Clear test instance firestore

**Remove all functions** before proceeding to limit unnecessary executions. Be careful to specify the correct project as it will wipe all data!

```commandline
firebase firestore:delete --all-collections --project phaenonet-test
```

### Restore production backup to test instance

Make sure `phaenonet-test@appspot.gserviceaccount.com` has following permissions on the bucket with the backup data:

- `Storage Legacy Bucket Reader`
- `Storage Object Viewer`

Also make sure that the **cloud functions are not deployed** when importing the data!

```commandline
gcloud --project=phaenonet-test --account=firestore-backup@phaenonet-test.iam.gserviceaccount.com firestore import gs://[backup-daily|backup-weekly]/[backup-folder]
```

### Copy data partial to test instance

Check if cloud functions should be deployed or not depending on the use-case and what data is imported.

```commandline
gcloud --project=phaenonet --account=firestore-backup@phaenonet.iam.gserviceaccount.com firestore export gs://staging.phaenonet-test.appspot.com --collection-ids=[collection_ids]
gcloud --project=phaenonet-test --account=firestore-backup@phaenonet-test.iam.gserviceaccount.com firestore import gs://staging.phaenonet-test.appspot.com/[folder] --collection-ids=[collection_ids]
```

## Related resources

- [phaenonet-client](https://github.com/globe-swiss/phaenonet-client)
- [data model documentation](https://dbdocs.io/pgoellnitz/phaenonet)
