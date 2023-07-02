# PhaenoNet Cloud Functions [![build](https://img.shields.io/github/actions/workflow/status/globe-swiss/phaenonet-functions/main.yml?branch=master)](undefined) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/7b5dbeaf574e431290a40c35c8c25207)](https://www.codacy.com/gh/globe-swiss/phaenonet-functions/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=globe-swiss/phaenonet-functions&amp;utm_campaign=Badge_Grade) [![Codacy Badge](https://app.codacy.com/project/badge/Coverage/7b5dbeaf574e431290a40c35c8c25207)](https://www.codacy.com/gh/globe-swiss/phaenonet-functions/dashboard?utm_source=github.com&utm_medium=referral&utm_content=globe-swiss/phaenonet-functions&utm_campaign=Badge_Coverage)

## Data Processing Overview

![Alt text](/docs/processing_overview.svg "PhaenoNet processing overview")

The image can be modified in [Google Cloud Architecture Diagramming Tool](https://bit.ly/GCPArchitecture)

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

Or use a personal account that has access on both projects.

Also make sure that the **cloud functions are not deployed** when importing the data!

```commandline
gcloud --project=phaenonet-test [--account=firestore-backup@phaenonet-test.iam.gserviceaccount.com] firestore import gs://phaenonet_[backup_daily|backup_weekly]/[backup-folder]
```

### Copy data partial to test instance

Check if cloud functions should be deployed or not depending on the use-case and what data is imported. Alternatively there is an UI available in Firestore.

```commandline
gcloud --project=phaenonet --account=firestore-backup@phaenonet.iam.gserviceaccount.com firestore export gs://phaenonet_[backup_daily|backup_weekly]/[backup-folder] --collection-ids=[collection_ids]
gcloud --project=phaenonet-test --account=firestore-backup@phaenonet-test.iam.gserviceaccount.com firestore import gs://phaenonet_[backup_daily|backup_weekly]/[backup-folder] --collection-ids=[collection_ids]
```

## Execute GitHub actions localy

Use `act -j <job>`

## Related resources

- [phaenonet-client](https://github.com/globe-swiss/phaenonet-client)
- [data model documentation](https://dbdocs.io/pgoellnitz/phaenonet)
