# Phaenonet Cloud Functions

## Deploy Cloud Functions
Use `deploy.sh` and `undeploy.sh` to install and remove cloud functions for the
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

### Clear test instance firestore
**Remove all functions** before proceeding to limit unnecessary executions. Be careful to specify the correct project as it will wipe all data!
```commandline
undeploy.sh all
firebase firestore:delete --all-collections --project phaenonet-test
```

### Restore production backup to test instance
Make sure `phaenonet-test@appspot.gserviceaccount.com` has following permissions on the bucket with the backup data:
* `Storage Legacy Bucket Reader`
* `Storage Object Viewer`

Also make sure that the **cloud functions are not deployed** when importing the data.

```commandline
undeploy.sh all
gcloud --project=phaenonet-test --account=firestore-backup@phaenonet-test.iam.gserviceaccount.com firestore import gs://[backup-daily|backup-weekly]/[backup-folder]
deploy.sh all
```

### Copy data partial to test instance
Check if cloud functions should be deployed or not depending on the use-case and what data is imported.
```commandline
gcloud --project=phaenonet --account=firestore-backup@phaenonet.iam.gserviceaccount.com firestore export gs://staging.phaenonet-test.appspot.com --collection-ids=[collection_ids]
gcloud --project=phaenonet-test --account=firestore-backup@phaenonet-test.iam.gserviceaccount.com firestore import gs://staging.phaenonet-test.appspot.com/[folder] --collection-ids=[collection_ids]
```
