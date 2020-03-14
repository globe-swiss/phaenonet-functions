from phenoback.functions import activity, analytics, users, meteoswiss
import firebase_admin
from phenoback.gcloud.utils import get_id, get_field

firebase_admin.initialize_app()


def process_activity(data, context):
    print('DEBUG: cotext: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))
    activity.process_activity(get_id(context), get_field(data, 'individual'), get_field(data, 'user'))


def process_observation(data, context):
    print('DEBUG: cotext: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))
    if len(data['value']) > 0:
        if get_field(data, 'phenophase') in ('BEA', 'BLA', 'BFA', 'BVS'):
            analytics.process_observation(get_id(context), get_field(data, 'date'), get_field(data, 'individual_id'),
                                          get_field(data, 'source'), get_field(data, 'year'),
                                          get_field(data, 'species'), get_field(data, 'phenophase'))
        else:
            print('INFO: No analytic values processed for phenophase %s' % get_field(data, 'phenophase'))
    else:
        analytics.remove_observation(get_id(context))


def process_user_nickname(data, context):
    print('DEBUG: cotext: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))
    user_id = get_id(context)
    old_nickname = get_field(data, 'nickname', old_value=True)
    new_nickname = get_field(data, 'nickname', old_value=False)
    if (old_nickname and new_nickname) and (old_nickname != new_nickname):
        users.process_update_nickname(user_id, old_nickname, new_nickname)
    elif old_nickname and not new_nickname:
        users.process_delete_nickname(old_nickname)
    elif not old_nickname and new_nickname:
        users.process_new_nickname(user_id, new_nickname)


def import_meteoswiss_data(data, context):
    print('DEBUG: cotext: (%s)' % str(context))
    print('DEBUG: data: (%s)' % str(data))
    meteoswiss.process_stations()
    meteoswiss.process_observations()
