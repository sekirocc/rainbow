from densefog import web
import flask   # noqa
from rainbow import billing
from densefog.common import utils
from rainbow.api import guard
from rainbow.model.iaas import load_balancer as load_balancer_model
from rainbow.model.iaas import load_balancer_listener as load_balancer_listener_model  # noqa
from rainbow.model.iaas import load_balancer_backend as load_balancer_backend_model  # noqa


def describe_load_balancers():
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
                        load_balancer_model.LOAD_BALANCER_STATUS_PENDING,
                        load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE,
                        load_balancer_model.LOAD_BALANCER_STATUS_BUILDING,
                        load_balancer_model.LOAD_BALANCER_STATUS_ERROR,
                        load_balancer_model.LOAD_BALANCER_STATUS_DELETED,
                    ]
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
            'searchWord': {'type': ['string', 'null']},
            'loadBalancerIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            }
        }
    })

    project_id = flask.request.project['id']
    load_balancer_ids = params.get('loadBalancerIds', None)
    search_word = params.get('searchWord', None)
    status = params.get('status', None)
    offset = params.get('offset', 0)
    limit = params.get('limit', 20)
    reverse = params.get('reverse', True)
    verbose = params.get('verbose', False)

    page = load_balancer_model.limitation(
        load_balancer_ids=load_balancer_ids,
        project_ids=[project_id],
        status=status,
        offset=offset,
        limit=limit,
        search_word=search_word,
        reverse=reverse,
        verbose=verbose)

    formated = {
        'limit': page['limit'],
        'offset': page['offset'],
        'total': page['total'],
        'loadBalancerSet': []
    }
    for load_balancer in page['items']:
        load_balancer_formated = load_balancer.format()
        if verbose:
            # TODO
            pass

        formated['loadBalancerSet'].append(load_balancer_formated)

    return formated


@web.mark_user_operation('loadBalancer', 'loadBalancerId')
@guard.guard_project_quota
def create_load_balancer():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'name': {'type': 'string', 'maxLength': 50},
            'description': {'type': 'string', 'maxLength': 250},
            'subnetId': {'type': 'string'},
            'bandwidth': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 300,
            }
        },
        'required': ['subnetId'],
    })
    project_id = flask.request.project['id']
    name = params.get('name', '')
    description = params.get('description', '')
    subnet_id = params['subnetId']
    bandwidth = params.get('bandwidth', load_balancer_model.DEFAULT_BANDWIDTH)

    (job_id, load_balancer_id) = load_balancer_model.create(
        project_id,
        subnet_id=subnet_id,
        name=name,
        description=description,
        bandwidth=bandwidth)

    # call billing api. ignore exceptions.
    with utils.silent():
        billing.client.load_balancers.create_load_balancers(project_id,
                                                            [load_balancer_id])

    return {
        'jobId': job_id,
        'loadBalancerId': load_balancer_id,
    }


@web.mark_user_operation('loadBalancer', 'loadBalancerIds')
def delete_load_balancers():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
        },
        'required': ['loadBalancerIds']
    })

    project_id = flask.request.project['id']
    load_balancer_ids = params['loadBalancerIds']
    load_balancer_model.delete(project_id, load_balancer_ids)

    # call billing api. ignore exceptions.
    with utils.silent():
        billing.client.load_balancers.delete_load_balancers(project_id,
                                                            load_balancer_ids)

    return {
        'loadBalancerIds': load_balancer_ids
    }


@web.mark_user_operation('loadBalancer', 'loadBalancerId')
def modify_load_balancer_attributes():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerId': {'type': 'string'},
            'name': {'type': 'string', 'maxLength': 50},
            'description': {'type': 'string', 'maxLength': 250},
        },
        'required': ['loadBalancerId']
    })

    project_id = flask.request.project['id']
    load_balancer_id = params.get('loadBalancerId')
    name = params.get('name', None)
    description = params.get('description', None)

    load_balancer_model.modify(project_id, load_balancer_id, name, description)

    return {
        'loadBalancerId': load_balancer_id
    }


@web.mark_user_operation('loadBalancer', 'loadBalancerIds')
def update_load_balancer_bandwidth():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
            'bandwidth': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 300
            },
        },
        'required': ['loadBalancerIds', 'bandwidth']
    })

    project_id = flask.request.project['id']
    load_balancer_ids = params['loadBalancerIds']
    bandwidth = params['bandwidth']

    load_balancer_model.update(project_id, load_balancer_ids, bandwidth)

    # call billing api. ignore exceptions.
    with utils.silent():
        billing.client.load_balancers.update_bandwidth(project_id,
                                                       load_balancer_ids)

    return {
        'loadBalancerIds': load_balancer_ids
    }


def describe_load_balancer_listeners():
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
                        load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_PENDING,  # noqa
                        load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_DELETED,  # noqa
                        load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_ACTIVE,  # noqa
                        load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_BUILDING,  # noqa
                        load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_ERROR  # noqa
                    ]
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
            'searchWord': {'type': ['string', 'null']},
            'loadBalancerListenerIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
            'loadBalancerIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            }
        }
    })

    project_id = flask.request.project['id']
    load_balancer_ids = params.get('loadBalancerIds', None)
    load_balancer_listener_ids = params.get('loadBalancerListenerIds', None)
    search_word = params.get('searchWord', None)
    status = params.get('status', None)
    offset = params.get('offset', 0)
    limit = params.get('limit', 20)
    reverse = params.get('reverse', True)
    verbose = params.get('verbose', False)

    page = load_balancer_listener_model.limitation(
        load_balancer_listener_ids=load_balancer_listener_ids,
        load_balancer_ids=load_balancer_ids,
        project_ids=[project_id],
        status=status,
        offset=offset,
        limit=limit,
        search_word=search_word,
        reverse=reverse,
        verbose=verbose)

    formated = {
        'limit': page['limit'],
        'offset': page['offset'],
        'total': page['total'],
        'listenerSet': []
    }
    for listener in page['items']:
        listener_formated = listener.format()
        if verbose:
            # TODO
            pass

        formated['listenerSet'].append(listener_formated)

    return formated


@web.mark_user_operation('loadBalancerListener', 'loadBalancerListenerId')
@guard.guard_project_quota
def create_load_balancer_listener():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'name': {'type': 'string', 'maxLength': 50},
            'description': {'type': 'string', 'maxLength': 250},
            'loadBalancerId': {'type': 'string'},
            'port': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 65535,
            },
            'protocol': {
                'type': 'string',
                'enum': ['TCP']
            },
            'balanceMode': {
                'type': 'string',
                'enum': ['ROUND_ROBIN', 'WEIGHTED_ROUND_ROBIN',
                         'LEAST_CONNECTIONS', 'WEIGHTED_LEAST_CONNECTIONS',
                         'SOURCE_IP', 'DESTINATION_IP']
            },
            'connectionLimit': {
                'type': 'integer',
                'minimum': -1
            },
            'sessionPersistenceMode': {
                'type': 'string',
                'enum': ['SOURCE_IP', 'HTTP_COOKIE', 'APP_COOKIE']
            },
            'sessionPersistenceTimeout': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 3600
            },
            'sessionPersistenceKey': {
                'type': 'string'
            },
            'healthMonitorDelay': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 50
            },
            'healthMonitorTimeout': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 300
            },
            'healthMonitorExpectedCodes': {
                'type': 'string',
            },
            'healthMonitorMaxRetries': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 10
            },
            'healthMonitorHttpMethod': {
                'type': 'string',
                'enum': ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']
            },
            'healthMonitorUrlPath': {
                'type': 'string',
                'pattern':
                    "^(/([a-zA-Z0-9-._~!$&\'()*+,;=:@]|(%[a-fA-F0-9]{2}))*)+$"
            },
            'healthMonitorType': {
                'type': 'string',
                'enum': ['PING', 'TCP', 'HTTP', 'HTTPS']
            },
        },
        'required': ['loadBalancerId', 'port', 'protocol'],
    })
    project_id = flask.request.project['id']
    name = params.get('name', '')
    description = params.get('description', '')
    load_balancer_id = params['loadBalancerId']
    port = params['port']
    protocol = params['protocol']
    balance_mode = params.get('balanceMode', 'WEIGHTED_ROUND_ROBIN')
    connection_limit = params.get('connectionLimit', -1)
    session_persistence_mode = params.get('sessionPersistenceMode', None)
    session_persistence_timeout = params.get('sessionPersistenceTimeout', None)
    session_persistence_key = params.get('sessionPersistenceKey', None)
    health_monitor_delay = params.get('healthMonitorDelay', 10)
    health_monitor_timeout = params.get('healthMonitorTimeout', 10)
    health_monitor_expected_codes = params.get('healthMonitorExpectedCodes', '200')  # noqa
    health_monitor_max_retries = params.get('healthMonitorMaxRetries', 3)
    health_monitor_http_method = params.get('healthMonitorHttpMethod', None)
    health_monitor_url_path = params.get('healthMonitorUrlPath', None)
    health_monitor_type = params.get('healthMonitorType', 'TCP')

    (job_id, load_balancer_listener_id) = load_balancer_listener_model.create(
        project_id,
        load_balancer_id=load_balancer_id,
        port=port,
        protocol=protocol,
        balance_mode=balance_mode,
        connection_limit=connection_limit,
        session_persistence_mode=session_persistence_mode,
        session_persistence_timeout=session_persistence_timeout,
        session_persistence_key=session_persistence_key,
        health_monitor_delay=health_monitor_delay,
        health_monitor_timeout=health_monitor_timeout,
        health_monitor_expected_codes=health_monitor_expected_codes,
        health_monitor_max_retries=health_monitor_max_retries,
        health_monitor_http_method=health_monitor_http_method,
        health_monitor_url_path=health_monitor_url_path,
        health_monitor_type=health_monitor_type,
        name=name,
        description=description)

    return {
        'jobId': job_id,
        'loadBalancerListenerId': load_balancer_listener_id,
    }


@web.mark_user_operation('loadBalancerListener', 'loadBalancerListenerIds')
def delete_load_balancer_listeners():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerListenerIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
        },
        'required': ['loadBalancerListenerIds']
    })

    project_id = flask.request.project['id']
    load_balancer_listener_ids = params['loadBalancerListenerIds']
    load_balancer_listener_model.delete(project_id, load_balancer_listener_ids)

    return {
        'loadBalancerListenerIds': load_balancer_listener_ids
    }


@web.mark_user_operation('loadBalancerListener', 'loadBalancerListenerId')
def modify_load_balancer_listener_attributes():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerListenerId': {'type': 'string'},
            'name': {'type': 'string', 'maxLength': 50},
            'description': {'type': 'string', 'maxLength': 250},
        },
        'required': ['loadBalancerListenerId']
    })

    project_id = flask.request.project['id']
    load_balancer_listener_id = params.get('loadBalancerListenerId')
    name = params.get('name', None)
    description = params.get('description', None)

    load_balancer_listener_model.modify(
        project_id,
        load_balancer_listener_id,
        name,
        description)

    return {
        'loadBalancerListenerId': load_balancer_listener_id
    }


@web.mark_user_operation('loadBalancerListener', 'loadBalancerListenerIds')
def update_load_balancer_listener():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerListenerId': {'type': 'string'},
            'balanceMode': {
                'type': 'string',
                'enum': ['ROUND_ROBIN', 'WEIGHTED_ROUND_ROBIN',
                         'LEAST_CONNECTIONS', 'WEIGHTED_LEAST_CONNECTIONS',
                         'SOURCE_IP', 'DESTINATION_IP']
            },
            'connectionLimit': {
                'type': 'integer',
                'minimum': -1
            },
            'sessionPersistenceMode': {
                'type': 'string',
                'enum': ['SOURCE_IP', 'HTTP_COOKIE', 'APP_COOKIE']
            },
            'sessionPersistenceTimeout': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 3600
            },
            'sessionPersistenceKey': {
                'type': 'string',
            },
            'healthMonitorDelay': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 50
            },
            'healthMonitorTimeout': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 300
            },
            'healthMonitorExpectedCodes': {
                'type': 'string',
            },
            'healthMonitorMaxRetries': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 10
            },
            'healthMonitorHttpMethod': {
                'type': 'string',
                'enum': ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']
            },
            'healthMonitorUrlPath': {
                'type': 'string',
                'pattern':
                    "^(/([a-zA-Z0-9-._~!$&\'()*+,;=:@]|(%[a-fA-F0-9]{2}))*)+$"
            },
        },
        'required': ['loadBalancerListenerId']
    })

    project_id = flask.request.project['id']
    load_balancer_listener_id = params['loadBalancerListenerId']
    balance_mode = params.get('balanceMode', None)
    connection_limit = params.get('connectionLimit', None)
    session_persistence_mode = params.get('sessionPersistenceMode', None)
    session_persistence_timeout = params.get('sessionPersistenceTimeout', None)
    session_persistence_key = params.get('sessionPersistenceKey', None)
    health_monitor_delay = params.get('healthMonitorDelay', None)
    health_monitor_timeout = params.get('healthMonitorTimeout', None)
    health_monitor_expected_codes = params.get('healthMonitorExpectedCodes', None)  # noqa
    health_monitor_max_retries = params.get('healthMonitorMaxRetries', None)
    health_monitor_http_method = params.get('healthMonitorHttpMethod', None)
    health_monitor_url_path = params.get('healthMonitorUrlPath', None)

    job_id = load_balancer_listener_model.update(
        project_id,
        load_balancer_listener_id,
        balance_mode=balance_mode,
        connection_limit=connection_limit,
        session_persistence_mode=session_persistence_mode,
        session_persistence_timeout=session_persistence_timeout,
        session_persistence_key=session_persistence_key,
        health_monitor_delay=health_monitor_delay,
        health_monitor_timeout=health_monitor_timeout,
        health_monitor_expected_codes=health_monitor_expected_codes,
        health_monitor_max_retries=health_monitor_max_retries,
        health_monitor_http_method=health_monitor_http_method,
        health_monitor_url_path=health_monitor_url_path)

    return {
        'jobId': job_id,
        'loadBalancerListenerId': load_balancer_listener_id,
    }


def describe_load_balancer_backends():
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
                        load_balancer_backend_model.LOAD_BALANCER_BACKEND_STATUS_ACTIVE,  # noqa
                        load_balancer_backend_model.LOAD_BALANCER_BACKEND_STATUS_DELETED,  # noqa
                    ]
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
            'searchWord': {'type': ['string', 'null']},
            'loadBalancerBackendIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
            'loadBalancerListenerIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            }
        }
    })

    project_id = flask.request.project['id']
    load_balancer_backend_ids = params.get('loadBalancerBackendIds', None)
    load_balancer_listener_ids = params.get('loadBalancerListenerIds', None)
    search_word = params.get('searchWord', None)
    status = params.get('status', None)
    offset = params.get('offset', 0)
    limit = params.get('limit', 20)
    reverse = params.get('reverse', True)
    verbose = params.get('verbose', False)

    page = load_balancer_backend_model.limitation(
        load_balancer_listener_ids=load_balancer_listener_ids,
        load_balancer_backend_ids=load_balancer_backend_ids,
        project_ids=[project_id],
        status=status,
        offset=offset,
        limit=limit,
        search_word=search_word,
        reverse=reverse,
        verbose=verbose)

    formated = {
        'limit': page['limit'],
        'offset': page['offset'],
        'total': page['total'],
        'backendSet': []
    }
    for backend in page['items']:
        backend_formated = backend.format()
        formated['backendSet'].append(backend_formated)

    return formated


@web.mark_user_operation('loadBalancerBackend', 'loadBalancerBackendId')
@guard.guard_project_quota
def create_load_balancer_backend():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'name': {'type': 'string', 'maxLength': 50},
            'description': {'type': 'string', 'maxLength': 250},
            'loadBalancerListenerId': {'type': 'string'},
            'port': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 65535,
            },
            'address': {
                'type': 'string',
                'pattern':
                    "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"  # noqa
            },
            'weight': {
                'type': 'integer',
                'minimum': 0,
                'maximum': 256,
            },
        },
        'required': ['loadBalancerListenerId', 'port', 'address'],
    })
    project_id = flask.request.project['id']
    name = params.get('name', '')
    description = params.get('description', '')
    load_balancer_listener_id = params['loadBalancerListenerId']
    port = params['port']
    address = params['address']
    weight = params.get('weight', 1)

    (job_id, load_balancer_backend_id) = load_balancer_backend_model.create(
        project_id,
        load_balancer_listener_id=load_balancer_listener_id,
        port=port,
        address=address,
        weight=weight,
        name=name,
        description=description)

    return {
        'jobId': job_id,
        'loadBalancerBackendId': load_balancer_backend_id,
    }


@web.mark_user_operation('loadBalancerBackend', 'loadBalancerBackendIds')
def delete_load_balancer_backends():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerBackendIds': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'minItems': 0,
                'maxItems': 20,
                'uniqueItems': True
            },
        },
        'required': ['loadBalancerBackendIds']
    })

    project_id = flask.request.project['id']
    load_balancer_backend_ids = params['loadBalancerBackendIds']
    load_balancer_backend_model.delete(project_id, load_balancer_backend_ids)

    return {
        'loadBalancerBackendIds': load_balancer_backend_ids
    }


@web.mark_user_operation('loadBalancerBackend', 'loadBalancerBackendId')
def modify_load_balancer_backend_attributes():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerBackendId': {'type': 'string'},
            'name': {'type': 'string', 'maxLength': 50},
            'description': {'type': 'string', 'maxLength': 250},
        },
        'required': ['loadBalancerBackendId']
    })

    project_id = flask.request.project['id']
    load_balancer_backend_id = params.get('loadBalancerBackendId')
    name = params.get('name', None)
    description = params.get('description', None)

    load_balancer_backend_model.modify(
        project_id,
        load_balancer_backend_id,
        name,
        description)

    return {
        'loadBalancerBackendId': load_balancer_backend_id
    }


@web.mark_user_operation('loadBalancerBackend', 'loadBalancerBackendId')
def update_load_balancer_backend():
    params = web.validate_request({
        'type': 'object',
        'properties': {
            'loadBalancerBackendId': {'type': 'string'},
            'weight': {
                'type': 'integer',
                'minimum': 0,
                'maximum': 256,
            },
        },
        'required': ['loadBalancerBackendId']
    })

    project_id = flask.request.project['id']
    load_balancer_backend_id = params['loadBalancerBackendId']
    weight = params.get('weight', None)

    job_id = load_balancer_backend_model.update(
        project_id,
        load_balancer_backend_id,
        weight=weight)

    return {
        'jobId': job_id,
        'loadBalancerBackendId': load_balancer_backend_id,
    }
