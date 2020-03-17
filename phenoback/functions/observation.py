from datetime import datetime, timezone

from phenoback.gcloud.utils import get_client


def update_last_observation(individual_id: str, phase: str, observation_date: datetime) -> None:
    individual_ref = get_client().document('individuals/%s' % individual_id)
    individual = individual_ref.get().to_dict()
    old_observation_date = individual.get('last_observation_date', datetime.min.replace(tzinfo=timezone.utc))
    if observation_date > old_observation_date:
        data = {'last_observation_date': observation_date}
        if individual.get('type') == 'individual':
            data['last_phenophase'] = phase

        individual_ref.update(data)
        print('INFO: updated last observation for %s (%s -> %s)'
              % (individual_id, old_observation_date, observation_date))
    else:
        print('DEBUG: no update for last observation for %s (%s > %s)'
              % (individual_id, old_observation_date, observation_date))
