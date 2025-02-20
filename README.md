# PhaenoNet Cloud Functions [![build](https://img.shields.io/github/actions/workflow/status/globe-swiss/phaenonet-functions/main.yml?branch=master)](undefined) [![codecov](https://codecov.io/gh/globe-swiss/phaenonet-functions/graph/badge.svg?token=K45OXCML80)](https://codecov.io/gh/globe-swiss/phaenonet-functions)

## Data Processing Overview

![Alt text](/docs/processing_overview.svg "PhaenoNet processing overview")

The image can be modified in [Excalidraw](https://excalidraw.com)/[Google Cloud Architecture Diagramming Tool](https://bit.ly/GCPArchitecture)

## Develop in GitHub Codespaces

Launch the Codespace in GitHub using the `codespace` branch. It will checkout the master branch, initialize the submodules, and rebuild the container. This process may take some minutes to finish.

## Deploy Cloud Functions

Use [Github Action](https://github.com/globe-swiss/phaenonet-functions/actions/workflows/deploy-function.yml) to manage cloud functions.

### Set export scheduler

```commandline
gcloud scheduler jobs update pubsub import_meteoswiss_data --project $PROJECT --schedule="5 1 * * *" --topic="import_meteoswiss_data" --message-body="none" --time-zone="Europe/Zurich" --description="Trigger cloud function to import meteoswiss data"
```

## Update phaenonet-test data

Instructions to update data-sets in the Firestore test instance from production.

### Production copyback

Use [Github Action](https://github.com/globe-swiss/phaenonet-functions/actions/workflows/copyback.yml) to create a clean test environment from the last production backup.

### Copy data partial

Check if cloud functions should be deployed or not depending on the use-case and what data is imported. Alternatively there is an UI available in Firestore.

```commandline
gcloud --project=phaenonet --account=firestore-backup@phaenonet.iam.gserviceaccount.com firestore export gs://phaenonet-[backup-daily|backup-archive]/[backup-folder] --collection-ids=[collection_ids]
gcloud --project=phaenonet-test --account=firestore-backup@phaenonet-test.iam.gserviceaccount.com firestore import gs://phaenonet-[backup-daily|backup-archive]/[backup-folder] --collection-ids=[collection_ids]
```

## Upgrade actions

### Update python version

1. check if new python version is suggested: <https://cloud.google.com/functions/docs/runtime-support#python>
1. Upgrade containers, workflows, Pipfile: `./maintenance/upgrade-environment.sh`
1. rebuild devcontainer
1. rebuild python environment

#### Rebuild python environement

Edit `project.toml` and set new version

```sh
rm -r .venv
uv sync --frozen
```

## Related resources

- [phaenonet-client](https://github.com/globe-swiss/phaenonet-client)
- [data model documentation](https://dbdocs.io/pgoellnitz/phaenonet)
