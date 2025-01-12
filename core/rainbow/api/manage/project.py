from densefog import web
import flask   # noqa
from rainbow.model.project import project as project_model
from rainbow.model.project import access_key as access_key_model
from rainbow.model.project import error as project_error


def create_access_keys():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'accessKeySet': {
                'type': 'array',
                'items': {
                    'projectId': {'type': 'string'},
                    'accessKey': {'type': 'string'},
                    'accessSecret': {'type': 'string'},
                    'expireAt': {
                        'type': ['string', 'null'],
                        'format': 'date-time'
                    },
                },
                'required': ['projectId', 'accessKey', 'accessSecret']
            }
        },
        'required': ['accessKeySet']
    })

    for access_key_params in params['accessKeySet']:
        project_id = access_key_params['projectId']
        access_key = access_key_params['accessKey']
        access_secret = access_key_params['accessSecret']
        expire_at = access_key_params.get('expireAt', None)

        access_key_model.create(
            project_id=project_id,
            key=access_key,
            secret=access_secret,
            expire_at=expire_at)

    return {}


def delete_access_keys():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'accessKeySet': {
                'type': 'array',
                'items': {
                    'projectId': {'type': 'string'},
                    'accessKey': {'type': 'string'},
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
        },
        'required': ['accessKeySet']
    })

    for access_key_params in params['accessKeySet']:
        project_id = access_key_params['projectId']
        access_key = access_key_params['accessKey']

        access_key_model.delete(
            project_id=project_id,
            keys=[access_key])

    return {}


def upsert_quota():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'quotaSet': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'projectId': {'type': 'string'},
                        'quota': {
                            'type': 'object',
                            'properties': {
                                'instances': {'type': 'integer'},
                                'vCPUs': {'type': 'integer'},
                                'memory': {'type': 'integer'},
                                'images': {'type': 'integer'},
                                'eIPs': {'type': 'integer'},
                                'networks': {'type': 'integer'},
                                'volumes': {'type': 'integer'},
                                'volumeSize': {'type': 'integer'},
                                'snapshots': {'type': 'integer'},
                                'keyPairs': {'type': 'integer'},
                                'loadBalancers': {'type': 'integer'},
                            },
                            'required': [
                                'instances',
                                'vCPUs',
                                'memory',
                                'images',
                                'eIPs',
                                'networks',
                                'volumes',
                                'volumeSize',
                                'snapshots',
                                'keyPairs',
                            ]
                        }
                    },
                    'required': [
                        'projectId',
                    ]
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            }
        },
        'required': [
            'quotaSet',
        ]
    })

    for quota_set in params['quotaSet']:
        project_id = quota_set['projectId']
        qt_load_balancers = quota_set['quota'].get('loadBalancers', 1)

        try:
            project_model.get(project_id)
            project_model.update(project_id,
                                 qt_load_balancers=qt_load_balancers)
        except project_error.ProjectNotFound:
            project_model.create(project_id,
                                 qt_load_balancers=qt_load_balancers)
    return {}
