import datetime
import traceback
from sqlalchemy.sql import and_

from densefog import db
from densefog.common import utils
from densefog.model import base
from densefog.model import filters
from densefog.model.job import job as job_model

from rainbow import config
from rainbow.model.iaas import error as iaas_error
from rainbow.model.iaas import load_balancer as load_balancer_model
from rainbow.model.iaas.openstack import error as op_error
from rainbow.model.iaas.openstack import network as network_provider

from densefog import logger
logger = logger.getChild(__file__)

LOAD_BALANCER_LISTENER_STATUS_PENDING = 'pending'
LOAD_BALANCER_LISTENER_STATUS_ACTIVE = 'active'
LOAD_BALANCER_LISTENER_STATUS_BUILDING = 'building'
LOAD_BALANCER_LISTENER_STATUS_DELETED = 'deleted'
LOAD_BALANCER_LISTENER_STATUS_ERROR = 'error'


class LoadBalancerListener(base.ResourceModel):

    @classmethod
    def db(cls):
        return db.DB.load_balancer_listener

    def status_deletable(self):
        return self['status'] in [
            LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
            LOAD_BALANCER_LISTENER_STATUS_ERROR
        ]

    def format(self):
        formated = {
            'loadBalancerListenerId': self['id'],
            'projectId': self['project_id'],
            'loadBalancerId': self['load_balancer_id'],
            'name': self['name'],
            'description': self['description'],
            'protocol': self['protocol'],
            'port': self['port'],
            'balanceMode': self['balance_mode'],
            'connectionLimit': self['connection_limit'],
            'sessionPersistenceMode': self['sp_mode'],
            'sessionPersistenceTimeout': self['sp_timeout'],
            'sessionPersistenceKey': self['sp_key'],
            'healthMonitorDelay': self['hm_delay'],
            'healthMonitorTimeout': self['hm_timeout'],
            'healthMonitorExpectedCodes': self['hm_expected_codes'],  # noqa
            'healthMonitorMaxRetries': self['hm_max_retries'],
            'healthMonitorHttpMethod': self['hm_http_method'],
            'healthMonitorUrlPath': self['hm_url_path'],
            'healthMonitorType': self['hm_type'],
            'status': self['status'],
            'updated': self['updated'],
            'created': self['created'],
            'deleted': self['deleted'],
            'ceased': self['ceased']
        }
        return formated


def check_loadbalancerlistener_port(load_balancer_id, port):
    """
    check whether the port in used by loadbalancerlistener.
    """

    def where(t):
        _where = True
        _where = and_(_where, t.load_balancer_id == load_balancer_id)
        _where = and_(_where, t.port == port)
        _where = and_(_where,
                      t.status.in_([
                          LOAD_BALANCER_LISTENER_STATUS_PENDING,
                          LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
                          LOAD_BALANCER_LISTENER_STATUS_BUILDING])
                      )

        return _where

    count = LoadBalancerListener.count(where)
    if count > 0:
        return True
    else:
        return False


@base.transaction
def create(project_id,
           load_balancer_id,
           port,
           protocol,
           balance_mode,
           connection_limit=-1,
           session_persistence_mode=None,
           session_persistence_timeout=None,
           session_persistence_key=None,
           health_monitor_delay=10,
           health_monitor_timeout=10,
           health_monitor_expected_codes='200',
           health_monitor_max_retries=3,
           health_monitor_http_method=None,
           health_monitor_url_path=None,
           health_monitor_type='tcp',
           name='',
           description=''):
    logger.info('.create() begin')
    with base.lock_for_update():
        load_balancer = load_balancer_model.get(load_balancer_id)

    load_balancer.must_belongs_project(project_id)

    # check loadbalancer status
    if load_balancer['status'] \
       != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        raise iaas_error.LoadBalancerListenerCanNotCreate(
            load_balancer_id)
    # check listeners whether is over limit
    count = count_listeners_of_loadbancer(load_balancer_id)
    if count >= config.CONF.loadbalancer_listener_limit:
        raise iaas_error.CreateLoadBalancerListenerOverLimit(
            config.CONF.loadbalancer_listener_limit)
    # check whether is used
    if check_loadbalancerlistener_port(load_balancer_id, port):
        raise iaas_error.CreateLoadBalancerListenerWhenPortInUse(port)

    # check session_persistence the format
    if session_persistence_mode is not None \
       and session_persistence_timeout is None:
        raise iaas_error.SessionPersistenceTimeoutFormatInvalid()
    if session_persistence_mode == 'APP_COOKIE' \
       and session_persistence_key is None:
        raise iaas_error.SessionPersistenceKeyFormatInvalid()

    protocol = protocol.upper()
    health_monitor_type = health_monitor_type.upper()
    if session_persistence_mode is None:
        session_persistence_timeout = session_persistence_key = None

    key = utils.generate_key(8)
    load_balancer_listener_id = 'lbl-%s' % key

    load_balancer_listener_id = LoadBalancerListener.insert(**{
        'id': load_balancer_listener_id,
        'project_id': project_id,
        'load_balancer_id': load_balancer_id,
        'name': name,
        'description': description,
        'protocol': protocol,
        'port': port,
        'balance_mode': balance_mode,
        'connection_limit': connection_limit,
        'sp_mode': session_persistence_mode,
        'sp_timeout': session_persistence_timeout,
        'sp_key': session_persistence_key,
        'hm_delay': health_monitor_delay,
        'hm_timeout': health_monitor_timeout,
        'hm_expected_codes': health_monitor_expected_codes,
        'hm_max_retries': health_monitor_max_retries,
        'hm_http_method': health_monitor_http_method,
        'hm_url_path': health_monitor_url_path,
        'hm_type': health_monitor_type,
        'status': LOAD_BALANCER_LISTENER_STATUS_PENDING,
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })

    params = {
        'project_id': project_id,
        'load_balancer_id': load_balancer_id,
        'load_balancer_listener_id': load_balancer_listener_id,
        'port': port,
        'protocol': protocol,
        'balance_mode': balance_mode,
        'connection_limit': connection_limit,
        'session_persistence_mode': session_persistence_mode,
        'session_persistence_timeout': session_persistence_timeout,
        'session_persistence_key': session_persistence_key,
        'health_monitor_delay': health_monitor_delay,
        'health_monitor_timeout': health_monitor_timeout,
        'health_monitor_expected_codes': health_monitor_expected_codes,
        'health_monitor_max_retries': health_monitor_max_retries,
        'health_monitor_http_method': health_monitor_http_method,
        'health_monitor_url_path': health_monitor_url_path,
        'health_monitor_type': health_monitor_type,
        'name': name,
        'description': description,
    }

    load_balancer_model.update_status(
        project_id=project_id,
        load_balancer_id=load_balancer_id,
        status=load_balancer_model.LOAD_BALANCER_STATUS_BUILDING
    )

    logger.info('.create() OK.')

    return (job_model.create(
            action='CreateLoadBalancerFrontEnd',
            project_id=project_id,
            params=params,
            try_period=10),
            load_balancer_listener_id)


def get(load_balancer_listener_id):
    logger.info('.get() begin. load_balancer_listener_id: %s' % load_balancer_listener_id)  # noqa

    load_balancer_listener = LoadBalancerListener.get_as_model(
        load_balancer_listener_id)
    if load_balancer_listener is None:
        raise iaas_error.LoadBalancerListenerNotFound(
            load_balancer_listener_id)
    logger.info('.get() OK.')
    return load_balancer_listener


def modify(project_id, load_balancer_listener_id, name=None, description=None):
    logger.info('.modify() begin, load_balancer_listener: %s' %
                load_balancer_listener_id)

    load_balancer_listener = get(load_balancer_listener_id)
    load_balancer_listener.must_belongs_project(project_id)

    if name is None:
        name = load_balancer_listener['name']

    if description is None:
        description = load_balancer_listener['description']

    LoadBalancerListener.update(load_balancer_listener_id, **{
        'name': name,
        'description': description,
        'updated': datetime.datetime.utcnow(),
    })

    logger.info('.modify() OK.')

    load_balancer_listener = get(load_balancer_listener_id)
    return load_balancer_listener


@base.transaction
def update_status(project_id, load_balancer_listener_id, status):
    with base.lock_for_update():
        listener = get(load_balancer_listener_id)

    listener.must_belongs_project(project_id)
    LoadBalancerListener.update(load_balancer_listener_id, **{
        'status': status,
        'updated': datetime.datetime.utcnow(),
    })


@base.transaction
def update(project_id,
           load_balancer_listener_id,
           balance_mode=None,
           connection_limit=None,
           session_persistence_mode=None,
           session_persistence_timeout=None,
           session_persistence_key=None,
           health_monitor_delay=None,
           health_monitor_timeout=None,
           health_monitor_expected_codes=None,
           health_monitor_max_retries=None,
           health_monitor_http_method=None,
           health_monitor_url_path=None):
    logger.info('.update() begin')
    listener = get(load_balancer_listener_id)
    listener.must_belongs_project(project_id)
    load_balancer_id = listener['load_balancer_id']
    with base.lock_for_update():
        load_balancer = load_balancer_model.get(load_balancer_id)

    if (load_balancer['status'] !=
        load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE) \
       or (listener['status'] != LOAD_BALANCER_LISTENER_STATUS_ACTIVE):
        raise iaas_error.LoadBalancerListenerCanNotUpdate(
            load_balancer_listener_id)
    # check session_persistence the format
    if session_persistence_mode is not None \
       and session_persistence_timeout is None \
       and listener.sp_timeout is None:
        raise iaas_error.SessionPersistenceTimeoutFormatInvalid()
    if session_persistence_mode == 'APP_COOKIE' \
       and session_persistence_key is None \
       and listener.sp_key is None:
        raise iaas_error.SessionPersistenceKeyFormatInvalid()

    if session_persistence_mode is None:
        session_persistence_timeout = session_persistence_key = None

    params = {
        'project_id': project_id,
        'load_balancer_id': load_balancer_id,
        'load_balancer_listener_id': load_balancer_listener_id,
        'balance_mode': balance_mode,
        'connection_limit': connection_limit,
        'sp_mode': session_persistence_mode,
        'sp_timeout': session_persistence_timeout,
        'sp_key': session_persistence_key,
        'hm_delay': health_monitor_delay,
        'hm_timeout': health_monitor_timeout,
        'hm_expected_codes': health_monitor_expected_codes,
        'hm_max_retries': health_monitor_max_retries,
        'hm_http_method': health_monitor_http_method,
        'hm_url_path': health_monitor_url_path
    }

    LoadBalancerListener.update(load_balancer_listener_id, **{
        'updated': datetime.datetime.utcnow(),
        'status': LOAD_BALANCER_LISTENER_STATUS_BUILDING
    })
    load_balancer_model.update_status(
        project_id=project_id,
        load_balancer_id=listener['load_balancer_id'],
        status=load_balancer_model.LOAD_BALANCER_STATUS_BUILDING
    )
    logger.info('.update() OK.')

    return job_model.create(
        action='UpdateLoadBalancerFrontEnd',
        project_id=project_id,
        params=params,
        try_period=10,
        try_max=1)


def limitation(load_balancer_listener_ids=None, load_balancer_ids=None,
               project_ids=None, verbose=False, status=None,
               search_word=None, offset=0, limit=10, reverse=True):
    def where(t):
        _where = True
        _where = filters.filter_ids(_where, t, load_balancer_listener_ids)
        _where = filters.filter_project_ids(_where, t, project_ids)
        _where = filters.filter_search_word(_where, t, search_word)
        _where = filters.filter_status(_where, t, status)

        if load_balancer_ids is None:
            pass
        elif len(load_balancer_ids) == 0:
            _where = False
        else:
            _where = and_(
                t.load_balancer_id.in_(load_balancer_ids), _where)
        return _where

    logger.info('.limitation() begin.')
    page = LoadBalancerListener.limitation_as_model(
        where,
        limit=limit,
        offset=offset,
        order_by=filters.order_by(reverse))
    if verbose:
        # TODO:
        pass

    logger.info('.limitation() OK.')

    return page


def count_listeners_of_loadbancer(load_balancer_id):
    """
    count the listener number of the loadbalancer.
    """

    def where(t):
        _where = True
        _where = and_(_where, t.load_balancer_id == load_balancer_id)
        _where = and_(_where,
                      t.status.in_([
                          LOAD_BALANCER_LISTENER_STATUS_PENDING,
                          LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
                          LOAD_BALANCER_LISTENER_STATUS_BUILDING])
                      )

        return _where

    count = LoadBalancerListener.count(where)
    return count


def _pre_delete(project_id, load_balancer_listener_ids):
    from rainbow.model.iaas import load_balancer_backend as lbb_model
    load_balancer_listeners = []
    for load_balancer_listener_id in load_balancer_listener_ids:
        load_balancer_listener = get(load_balancer_listener_id)
        load_balancer_id = load_balancer_listener['load_balancer_id']
        with base.lock_for_update():
            load_balancer = load_balancer_model.get(load_balancer_id)

        load_balancer_listener.must_belongs_project(project_id)
        # check loadbalancer status
        if (load_balancer['status'] !=
            load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE) \
           and (load_balancer['status'] !=
                load_balancer_model.LOAD_BALANCER_STATUS_ERROR):
            raise iaas_error.LoadBalancerListenerCanNotDelete(
                load_balancer_listener_id)
        if not load_balancer_listener.status_deletable():
            raise iaas_error.LoadBalancerListenerCanNotDelete(
                load_balancer_listener_id)

        check_backend = lbb_model.count_backends_of_listener(
            load_balancer_listener_id)
        if check_backend != 0:
            raise iaas_error.LoadBalancerListenerInUse(
                load_balancer_listener_id)

        load_balancer_listeners.append(load_balancer_listener)
    return load_balancer_listeners


@base.transaction
def delete(project_id,
           load_balancer_listener_ids):
    logger.info('.delete() begin, '
                'total count: %s, load_balancer_listener_ids: %s' %
                (len(load_balancer_listener_ids), load_balancer_listener_ids))
    load_balancer_listeners = _pre_delete(project_id,
                                          load_balancer_listener_ids)

    load_balancers = {}
    for load_balancer_listener in load_balancer_listeners:
        lb_id = load_balancer_listener['load_balancer_id']
        lbl_id = load_balancer_listener['id']
        if lb_id not in load_balancers.keys():
            load_balancers[lb_id] = []
        load_balancers[lb_id].append(lbl_id)

        LoadBalancerListener.update(lbl_id, **{
            'status': LOAD_BALANCER_LISTENER_STATUS_DELETED,
            'deleted': datetime.datetime.utcnow(),
        })

        load_balancer_model.update_status(
            project_id=project_id,
            load_balancer_id=lb_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_BUILDING
        )

    logger.info('.delete() OK.')
    for lbls in load_balancers.values():
        job_model.create(
            action='EraseLoadBalancerFrontEnd',
            params={
                'resource_ids': lbls
            },
            try_period=10,
            try_max=1)


def sync_create_loadbalancer_listener(params={}):
    load_balancer_id = params['load_balancer_id']
    logger.info('.sync_create_loadbalancer_listener() begin.\
                load_balancer_id: %s' % load_balancer_id)

    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        return False

    try:
        op_listener = network_provider.create_loadbalancer_listener(
            loadbalancer_id=load_balancer['op_loadbalancer_id'],
            name=params['load_balancer_listener_id'],
            protocol=params['protocol'],
            connection_limit=params['connection_limit'],
            port=params['port'])
    except Exception as e:
        LoadBalancerListener.update(params['load_balancer_listener_id'], **{
            'status': LOAD_BALANCER_LISTENER_STATUS_ERROR,
        })
        load_balancer_model.LoadBalancer.update(load_balancer_id, **{
            'status': load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE,
        })
        stack = traceback.format_exc()
        raise iaas_error.ProviderCreateLoadBalancerListenerError(e, stack)

    params['op_listener_id'] = op_listener['id']

    logger.info('.sync_create_loadbalancer_listener() OK.')

    job_model.create(
        action='CreateLoadBalancerListener',
        params=params,
        try_period=10,
        try_max=1)
    return True


def sync_update_loadbalancer_listener(params={}):
    load_balancer_listener_id = params['load_balancer_listener_id']
    logger.info('.sync_update_loadbalancer_listener() begin.\
                load_balancer_listener_id: %s' % load_balancer_listener_id)

    listener = get(load_balancer_listener_id)
    load_balancer_id = listener['load_balancer_id']
    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        return False

    try:
        network_provider.update_loadbalancer_listener(
            loadbalancer_listener_id=listener['op_listener_id'],
            connection_limit=params['connection_limit'])
    except Exception as e:
        LoadBalancerListener.update(load_balancer_listener_id, **{
            'updated': datetime.datetime.utcnow(),
            'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE
        })
        load_balancer_model.LoadBalancer.update(load_balancer_id, **{
            'status': load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE,
        })
        stack = traceback.format_exc()
        raise iaas_error.ProviderUpdateLoadBalancerListenerError(e, stack)

    logger.info('.sync_update_loadbalancer_listener() OK.')

    job_model.create(
        action='UpdateLoadBalancerListener',
        params=params,
        try_period=10,
        try_max=1)
    return True


def erase_load_balancer_listener(load_balancer_listener_id, try_time=0,
                                 lbl_ids=None):
    logger.info('.erase() begin. load_balancer_listener_id: %s' %
                load_balancer_listener_id)  # noqa
    listener = get(load_balancer_listener_id)
    if listener['ceased']:
        logger.info('.erase() pass. already ceased.')
        return True

    load_balancer_id = listener['load_balancer_id']
    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        if try_time == 3:
            LoadBalancerListener.update(load_balancer_listener_id, **{
                'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
            })
            if lbl_ids is not None:
                load_balancer_model.LoadBalancer.update(
                    load_balancer_id,
                    **{'status':
                       load_balancer_model.LOAD_BALANCER_STATUS_ERROR})
        return False

    if listener['status'] == LOAD_BALANCER_LISTENER_STATUS_DELETED:
        try:
            network_provider.delete_loadbalancer_healthmonitor(
                listener['op_healthmonitor_id'])
        except Exception as ex:
            if op_error.is_notfound(ex):
                pass
            else:
                if try_time == 3:
                    LoadBalancerListener.update(load_balancer_listener_id, **{
                        'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
                    })
                    load_balancer_model.LoadBalancer.update(
                        load_balancer_id,
                        **{'status':
                           load_balancer_model.LOAD_BALANCER_STATUS_ERROR})
                trace = traceback.format_exc()
                raise iaas_error.ProviderDeleteLoadBalancerListenerError(
                    ex, trace)

        logger.info('.erase load_balancer_listener_id: %s OK.',
                    load_balancer_listener_id)
        if lbl_ids is not None:
            lbl_ids.append(load_balancer_listener_id)
            job_model.create(
                action='EraseLoadBalancerListener',
                params={
                    'resource_ids': lbl_ids
                },
                try_period=10,
                try_max=1)
    else:
        logger.warn('listener status is not DELETED, can not be ceased!')
        logger.warn('STRANGE, it should not enter .erase method!')

    return True


def delete_load_balancer_listener(params={}):
    load_balancer_id = params['load_balancer_id']
    logger.info('.delete() begin. openstack listener: %s' %
                params['op_listener_id'])  # noqa

    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        return False

    try:
        network_provider.delete_loadbalancer_listener(
            params['op_listener_id'])
    except Exception as ex:
        if op_error.is_notfound(ex):
            pass
        else:
            load_balancer_model.LoadBalancer.update(load_balancer_id, **{
                'status': load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE,
            })
            trace = traceback.format_exc()
            raise iaas_error.ProviderDeleteLoadBalancerListenerError(
                ex, trace)

    logger.info('.delete openstack listener: %s OK.', params['op_listener_id'])
    job_model.create(
        action='EraseLoadBalancerHealthmonitor',
        params={
            'resource_ids': [load_balancer_id]
        },
        try_period=10)

    return True


def sync_create_loadbalancer_pool(params={}):
    load_balancer_id = params['load_balancer_id']
    logger.info('.sync_create_loadbalancer_pool() begin.load_balancer_id: %s' %
                load_balancer_id)

    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        return False

    try:
        op_pool = network_provider.create_loadbalancer_pool(
            loadbalancer_listener_id=params['op_listener_id'],
            name=params['load_balancer_listener_id'],
            protocol=params['protocol'],
            balance_mode=params['balance_mode'],
            session_persistence_mode=params['session_persistence_mode'],
            session_persistence_timeout=params['session_persistence_timeout'],
            session_persistence_key=params['session_persistence_key'])
    except Exception as e:
        LoadBalancerListener.update(params['load_balancer_listener_id'], **{
            'status': LOAD_BALANCER_LISTENER_STATUS_ERROR,
        })
        # Delete loadbalancer listener when create pool fail
        job_model.create(
            action='DeleteLoadBalancerListener',
            params=params,
            try_period=10)
        stack = traceback.format_exc()
        raise iaas_error.ProviderCreateLoadBalancerListenerError(e, stack)

    params['op_pool_id'] = op_pool['id']

    logger.info('.sync_create_loadbalancer_pool() OK.')
    job_model.create(
        action='CreateLoadBalancerPool',
        params=params,
        try_period=10,
        try_max=1)
    return True


def sync_update_loadbalancer_pool(params={}):
    load_balancer_listener_id = params['load_balancer_listener_id']
    logger.info('.sync_update_loadbalancer_pool() begin.\
                load_balancer_listener_id: %s' % load_balancer_listener_id)

    listener = get(load_balancer_listener_id)
    load_balancer_id = listener['load_balancer_id']
    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        return False

    try:
        network_provider.update_loadbalancer_pool(
            loadbalancer_pool_id=listener['op_pool_id'],
            balance_mode=params['balance_mode'],
            session_persistence_mode=params['sp_mode'],
            session_persistence_timeout=params['sp_timeout'],
            session_persistence_key=params['sp_key'])
    except Exception as e:
        LoadBalancerListener.update(load_balancer_listener_id, **{
            'updated': datetime.datetime.utcnow(),
            'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE
        })
        load_balancer_model.LoadBalancer.update(load_balancer_id, **{
            'status': load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE,
        })
        stack = traceback.format_exc()
        raise iaas_error.ProviderUpdateLoadBalancerListenerError(e, stack)

    logger.info('.sync_update_loadbalancer_pool() OK.')
    job_model.create(
        action='UpdateLoadBalancerPool',
        params=params,
        try_period=10,
        try_max=1)
    return True


def erase_load_balancer_pool(load_balancer_listener_id, try_time=0,
                             lbl_ids=None):
    logger.info('.erase() begin. load_balancer_pool for listener: %s' % load_balancer_listener_id)  # noqa
    listener = get(load_balancer_listener_id)
    if listener['ceased']:
        logger.info('.erase() pass. already ceased.')
        return True

    load_balancer_id = listener['load_balancer_id']
    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        if try_time == 3:
            LoadBalancerListener.update(load_balancer_listener_id, **{
                'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
            })
            if lbl_ids is not None:
                load_balancer_model.LoadBalancer.update(
                    load_balancer_id,
                    **{'status':
                       load_balancer_model.LOAD_BALANCER_STATUS_ERROR})
        return False

    if listener['status'] == LOAD_BALANCER_LISTENER_STATUS_DELETED:
        try:
            network_provider.delete_loadbalancer_pool(listener['op_pool_id'])
        except Exception as ex:
            if op_error.is_notfound(ex):
                pass
            else:
                if try_time == 3:
                    LoadBalancerListener.update(load_balancer_listener_id, **{
                        'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
                    })
                    load_balancer_model.LoadBalancer.update(
                        load_balancer_id,
                        **{'status':
                           load_balancer_model.LOAD_BALANCER_STATUS_ERROR})
                trace = traceback.format_exc()
                raise iaas_error.ProviderDeleteLoadBalancerListenerError(
                    ex, trace)

        logger.info('.erase load_balancer_pool for listener: %s OK.',
                    load_balancer_listener_id)

        if lbl_ids is not None:
            lbl_ids.append(load_balancer_listener_id)
            job_model.create(
                action='EraseLoadBalancerPool',
                params={
                    'resource_ids': lbl_ids
                },
                try_period=10,
                try_max=1)
    else:
        logger.warn('listener status is not DELETED, can not be ceased!')
        logger.warn('STRANGE, it should not enter .erase method!')

    return True


def delete_load_balancer_pool(params={}):
    load_balancer_id = params['load_balancer_id']
    logger.info('.delete() begin. openstack pool: %s' %
                params['op_pool_id'])  # noqa

    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        return False

    try:
        network_provider.delete_loadbalancer_pool(
            params['op_pool_id'])
    except Exception as ex:
        if op_error.is_notfound(ex):
            pass
        else:
            load_balancer_model.LoadBalancer.update(load_balancer_id, **{
                'status': load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE,
            })
            trace = traceback.format_exc()
            raise iaas_error.ProviderDeleteLoadBalancerPoolError(
                ex, trace)

    logger.info('.delete openstack pool: %s OK.', params['op_pool_id'])
    job_model.create(
        action='DeleteLoadBalancerListener',
        params=params,
        try_period=10)

    return True


def sync_create_loadbalancer_healthmonitor(params={}):
    load_balancer_id = params['load_balancer_id']
    logger.info('.sync_create_loadbalancer_healthmonitor() begin.\
                load_balancer_id: %s' % load_balancer_id)

    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        return False

    try:
        op_health_monitor = \
            network_provider.create_loadbalancer_healthmonitor(
                loadbalancer_pool_id=params['op_pool_id'],
                name=params['load_balancer_listener_id'],
                delay=params['health_monitor_delay'],
                timeout=params['health_monitor_timeout'],
                expected_codes=params['health_monitor_expected_codes'],  # noqa
                max_retries=params['health_monitor_max_retries'],
                http_method=params['health_monitor_http_method'],
                url_path=params['health_monitor_url_path'],
                type=params['health_monitor_type'])
    except Exception as e:
        LoadBalancerListener.update(params['load_balancer_listener_id'], **{
            'status': LOAD_BALANCER_LISTENER_STATUS_ERROR,
        })
        # Delete loadbalancer listener and pool
        # when create healthmonitor fail
        job_model.create(
            action='DeleteLoadBalancerPool',
            params=params,
            try_period=10)

        stack = traceback.format_exc()
        raise iaas_error.ProviderCreateLoadBalancerListenerError(e, stack)

    LoadBalancerListener.update(params['load_balancer_listener_id'], **{
        'op_listener_id': params['op_listener_id'],
        'op_pool_id': params['op_pool_id'],
        'op_healthmonitor_id': op_health_monitor['id'],
        'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
        'updated': datetime.datetime.utcnow(),
    })

    logger.info('.sync_create_loadbalancer_healthmonitor() OK.')
    return True


def sync_update_loadbalancer_healthmonitor(params={}):
    load_balancer_listener_id = params['load_balancer_listener_id']
    logger.info('.sync_update_loadbalancer_healthmonitor() begin.\
                load_balancer_listener_id: %s' % load_balancer_listener_id)

    listener = get(load_balancer_listener_id)
    load_balancer_id = listener['load_balancer_id']
    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        return False

    try:
        network_provider.update_loadbalancer_healthmonitor(
            loadbalancer_healthmonitor_id=listener['op_healthmonitor_id'],
            delay=params['hm_delay'],
            timeout=params['hm_timeout'],
            expected_codes=params['hm_expected_codes'],  # noqa
            max_retries=params['hm_max_retries'],
            http_method=params['hm_http_method'],
            url_path=params['hm_url_path'])
    except Exception as e:
        LoadBalancerListener.update(load_balancer_listener_id, **{
            'updated': datetime.datetime.utcnow(),
            'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE
        })
        load_balancer_model.LoadBalancer.update(load_balancer_id, **{
            'status': load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE,
        })
        stack = traceback.format_exc()
        raise iaas_error.ProviderUpdateLoadBalancerListenerError(e, stack)

    # sp_mode has value means enable session_persistence, otherwise means
    # disable session_persistence
    for key in params.keys():
        if (key != 'sp_mode') and (params[key] is None):
            params.pop(key)
    del params['load_balancer_id']
    del params['load_balancer_listener_id']
    params['updated'] = datetime.datetime.utcnow()
    params['status'] = LOAD_BALANCER_LISTENER_STATUS_ACTIVE
    LoadBalancerListener.update(load_balancer_listener_id, **params)

    logger.info('.sync_update_loadbalancer_healthmonitor() OK.')
    return True


def erase_load_balancer_healthmonitor(load_balancer_listener_id, try_time=0,
                                      lbl_ids=None):
    logger.info('.erase() begin. load_balancer_healthmonitor for \
                listener: %s' % load_balancer_listener_id)  # noqa
    listener = get(load_balancer_listener_id)
    if listener['ceased']:
        logger.info('.erase() pass. already ceased.')
        return True

    load_balancer_id = listener['load_balancer_id']
    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        if try_time == 3:
            LoadBalancerListener.update(load_balancer_listener_id, **{
                'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
            })
            if lbl_ids is not None:
                load_balancer_model.LoadBalancer.update(
                    load_balancer_id,
                    **{'status':
                       load_balancer_model.LOAD_BALANCER_STATUS_ERROR})
        return False

    if listener['status'] == LOAD_BALANCER_LISTENER_STATUS_DELETED:
        try:
            network_provider.delete_loadbalancer_listener(
                listener['op_listener_id'])
        except Exception as ex:
            if op_error.is_notfound(ex):
                pass
            else:
                if try_time == 3:
                    LoadBalancerListener.update(load_balancer_listener_id, **{
                        'status': LOAD_BALANCER_LISTENER_STATUS_ACTIVE,
                    })
                    load_balancer_model.LoadBalancer.update(
                        load_balancer_id,
                        **{'status':
                           load_balancer_model.LOAD_BALANCER_STATUS_ERROR})
                trace = traceback.format_exc()
                raise iaas_error.ProviderDeleteLoadBalancerListenerError(
                    ex, trace)
        LoadBalancerListener.update(load_balancer_listener_id, **{
            'ceased': datetime.datetime.utcnow(),
        })
        logger.info('.erase load_balancer_healthmonitor for listener: %s OK.',
                    load_balancer_listener_id)
        if lbl_ids is not None:
            job_model.create(
                action='EraseLoadBalancerHealthmonitor',
                params={
                    'resource_ids': [load_balancer_id]
                },
                try_period=10)
    else:
        logger.warn('listener status is not DELETED, can not be ceased!')
        logger.warn('STRANGE, it should not enter .erase method!')

    return True


def sync(load_balancer_id, load_balancer_listener_id):
    logger.info('.sync() begin. load_balancer_id: %s' % load_balancer_id)

    listener = get(load_balancer_listener_id)
    if listener.is_busy():
        return listener

    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    logger.info('load_balancer status: (%s) => (%s) .' %
                (load_balancer['status'], status))  # noqa

    load_balancer_model.LoadBalancer.update(load_balancer_id, **{
        'status': status,
        'updated': datetime.datetime.utcnow(),
    })

    logger.info('.sync() OK.')

    load_balancer = load_balancer_model.get(load_balancer_id)
    return load_balancer
