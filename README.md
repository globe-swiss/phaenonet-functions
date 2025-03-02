# PhaenoNet Cloud Functions

[![Build Status](https://img.shields.io/github/actions/workflow/status/globe-swiss/phaenonet-functions/main.yml?branch=master)](https://github.com/globe-swiss/phaenonet-functions/actions/workflows/main.yml)
[![Codecov Coverage](https://codecov.io/gh/globe-swiss/phaenonet-functions/graph/badge.svg?token=K45OXCML80)](https://codecov.io/gh/globe-swiss/phaenonet-functions)

## Overview

PhaenoNet is a phenology observation platform developed by GLOBE Switzerland. This repository contains the cloud functions responsible for data processing, integration, and management within the PhaenoNet ecosystem.

### Data Processing Workflow

![PhaenoNet Processing Overview](/docs/processing_overview.svg)

*Created with [Excalidraw](https://excalidraw.com)*

### Data Model Documentation

For detailed information on the data structures and schemas used in PhaenoNet:

- [Data Model Documentation](./docs/datamodel.md)

## Development Environment

### GitHub Codespaces

To set up a development environment using GitHub Codespaces:

1. Launch a new Codespace based on the `codespace` branch.
2. The setup process will:
   - Checkout the `master` branch.
   - Initialize submodules.
   - Rebuild the development container.

*Note: Initialization may take several minutes.*

## Deployment

### Deploying Cloud Functions

Cloud functions are managed via GitHub Actions:

- **Deployment Workflow:** [deploy-function.yml](https://github.com/globe-swiss/phaenonet-functions/actions/workflows/deploy-function.yml)

### Setting Up the Export Scheduler

To schedule regular imports of MeteoSwiss data:

```bash
gcloud scheduler jobs update pubsub import_meteoswiss_data \
  --project $PROJECT \
  --schedule="5 1 * * *" \
  --topic="import_meteoswiss_data" \
  --message-body="none" \
  --time-zone="Europe/Zurich" \
  --description="Trigger cloud function to import MeteoSwiss data"
```

## Updating Test Data

### Production Copyback

To replicate the production environment in the test instance:

- Use the [copyback.yml](https://github.com/globe-swiss/phaenonet-functions/actions/workflows/copyback.yml) GitHub Action.

### Partial Data Copy

For selective data updates:

1. Determine if cloud functions need deployment based on the data being imported.
2. Alternatively, use the Firestore UI for data management.

Commands for exporting and importing specific collections:

```bash
# Export from production
gcloud --project=phaenonet \
  --account=firestore-backup@phaenonet.iam.gserviceaccount.com \
  firestore export gs://phaenonet-[backup-daily|backup-archive]/[backup-folder] \
  --collection-ids=[collection_ids]

# Import into test
gcloud --project=phaenonet-test \
  --account=firestore-backup@phaenonet-test.iam.gserviceaccount.com \
  firestore import gs://phaenonet-[backup-daily|backup-archive]/[backup-folder] \
  --collection-ids=[collection_ids]
```

## Maintenance

### Updating Python Version

To align with the latest supported Python versions:

1. Check for updates: [Google Cloud Python Runtime Support](https://cloud.google.com/functions/docs/runtime-support#python)
2. Upgrade environments:
   - Run: `./maintenance/upgrade-environment.sh`
3. Rebuild the development container.
4. Rebuild the Python environment.

#### Rebuilding the Python Environment

After updating `project.toml` with the new version:

```bash
rm -r .venv
uv sync --frozen
```

## Related Resources

- [PhaenoNet Client](https://github.com/globe-swiss/phaenonet-client)
