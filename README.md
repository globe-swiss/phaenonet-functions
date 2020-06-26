# Phaenonet Cloud Functions

## Deploy Cloud Functions
Use `deploy.sh` and `undeploy.sh`to install and remove cloud functions for the
_phaenonet-test_ project. For production deployment change the `PROJECT` 
environment variable within these scripts.

## Update Data for Testing/Development
Instructions to update data-sets in the Firestore test instance from production.

### Activate service accounts
List activated and active accounts: `gcloud auth list`

Service accounts need only to be activated once:
```commandline
gcloud --project=phaenonet-test auth activate-service-account firestore-backup@phaenonet-test.iam.gserviceaccount.com --key-file=[key_file]
gcloud --project=phaenonet auth activate-service-account firestore-backup@phaenonet.iam.gserviceaccount.com --key-file=[key_file]
```

### Copy data to test instance

```commandline
gcloud --project=phaenonet --account=firestore-backup@phaenonet.iam.gserviceaccount.com firestore export gs://staging.phaenonet-test.appspot.com --collection-ids=[collection_ids]
gcloud --project=phaenonet-test --account=firestore-backup@phaenonet-test.iam.gserviceaccount.com firestore import gs://staging.phaenonet-test.appspot.com/[folder] --collection-ids=[collection_ids]
```