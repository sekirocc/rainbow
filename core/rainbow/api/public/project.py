from densefog import web
import flask   # noqa
from rainbow.model.lcs import client as lcs_client
from rainbow.model.project import project as project_model

NETWORK_STATUS_PENDING = 'pending'
NETWORK_STATUS_ACTIVE = 'active'
NETWORK_STATUS_BUILDING = 'building'
NETWORK_STATUS_DISABLED = 'disabled'
NETWORK_STATUS_ERROR = 'error'
NETWORK_STATUS_DELETED = 'deleted'


def describe_quotas():
    project_id = flask.request.project['id']
    project = project_model.get(project_id)

    formated = {
        'total': project.format_total_quota(),
        'usage': project.format_usage_quota(),
    }

    return formated


def describe_networks():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'limit': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 100,
            },
            'offset': {'type': 'integer', 'minimum': 0},
            'reverse': {'type': 'boolean'},
            'verbose': {'type': 'boolean'},
            'status': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'enum': [
                        NETWORK_STATUS_PENDING,
                        NETWORK_STATUS_ACTIVE,
                        NETWORK_STATUS_BUILDING,
                        NETWORK_STATUS_DISABLED,
                        NETWORK_STATUS_ERROR,
                        NETWORK_STATUS_DELETED,
                    ]
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
            'searchWord': {'type': ['string', 'null']},
        }
    })

    project_id = flask.request.project['id']
    status = params.get('status', None)
    offset = params.get('offset', 0)
    limit = params.get('limit', 20)
    reverse = params.get('reverse', True)
    verbose = params.get('verbose', False)
    formated = lcs_client.get_networks(project_ids=[project_id],
                                       status=status,
                                       offset=offset,
                                       limit=limit,
                                       reverse=reverse,
                                       verbose=verbose)

    return formated
