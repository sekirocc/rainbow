from rainbow import model
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
from rainbow.model.iaas import load_balancer_listener as load_balancer_listener_model  # noqa
from rainbow.model.iaas.openstack import error as op_error
from rainbow.model.iaas.openstack import network as network_provider
from rainbow.model.lcs import client as lcs_client

from densefog import logger
logger = logger.getChild(__file__)


LOAD_BALANCER_BACKEND_STATUS_ACTIVE = 'active'
LOAD_BALANCER_BACKEND_STATUS_DELETED = 'deleted'


class LoadBalancerBackend(base.ResourceModel):

    @classmethod
    def db(cls):
        return db.DB.load_balancer_backend

    def status_deletable(self):
        return self['status'] in [
            LOAD_BALANCER_BACKEND_STATUS_ACTIVE,
        ]

    def format(self):
        formated = {
            'loadBalancerBackendId': self['id'],
            'projectId': self['project_id'],
            'name': self['name'],
            'description': self['description'],
            'loadBalancerId': self['load_balancer_id'],
            'loadBalancerListenerId': self['load_balancer_listener_id'],
            'address': self['address'],
            'port': self['port'],
            'weight': self['weight'],
            'status': self['status'],
            'updated': self['updated'],
            'created': self['created'],
            'deleted': self['deleted'],
            'ceased': self['ceased']
        }
        return formated


@base.transaction
def create(project_id,
           load_balancer_listener_id,
           address,
           port,
           weight=1,
           name='',
           description=''):
    logger.info('.create() begin')
    load_balancer_listener = load_balancer_listener_model.get(
        load_balancer_listener_id)
    load_balancer_id = load_balancer_listener['load_balancer_id']
    load_balancer_listener.must_belongs_project(project_id)
    with base.lock_for_update():
        load_balancer = load_balancer_model.get(load_balancer_id)

    # check loadbalancer status
    if (load_balancer_listener['status'] !=
        load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_ACTIVE) \
       or (load_balancer['status'] !=
           load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE):
        raise iaas_error.LoadBalancerBackendCanNotCreate()
    # check backends whether is over limit
    count = count_backends_of_listener(load_balancer_listener_id)
    if count >= config.CONF.loadbalancer_backend_limit:
        raise iaas_error.LoadBalancerBackendOverLimit(
            config.CONF.loadbalancer_backend_limit)
    # check address and port whether is used
    page = limitation(load_balancer_listener_ids=[load_balancer_listener_id],
                      project_ids=[project_id],
                      status=LOAD_BALANCER_BACKEND_STATUS_ACTIVE,
                      limit=0)
    for backend in page['items']:
        if backend['address'] == address and backend['port'] == port:
            raise iaas_error.LoadBalancerBackendInUse()

    subnet_id = load_balancer['subnet_id']
    subnet = lcs_client.get_subnet(project_id, subnet_id)
    op_subnet_id = subnet['opSubnetId']
    op_loadbalancer_pool_id = load_balancer_listener['op_pool_id']

    key = utils.generate_key(8)
    load_balancer_backend_id = 'lbb-%s' % key

    try:
        op_backend = network_provider.create_loadbalancer_member(
            loadbalancer_pool_id=op_loadbalancer_pool_id,
            subnet_id=op_subnet_id,
            name=load_balancer_backend_id,
            address=address,
            port=port,
            weight=weight)
    except Exception as e:
        stack = traceback.format_exc()
        raise iaas_error.ProviderCreateLoadBalancerBackendError(e, stack)

    load_balancer_backend_id = LoadBalancerBackend.insert(**{
        'id': load_balancer_backend_id,
        'project_id': project_id,
        'load_balancer_id': load_balancer_id,
        'load_balancer_listener_id': load_balancer_listener_id,
        'name': name,
        'description': description,
        'address': address,
        'port': port,
        'weight': weight,
        'status': LOAD_BALANCER_BACKEND_STATUS_ACTIVE,
        'op_pool_id': op_loadbalancer_pool_id,
        'op_member_id': op_backend['id'],
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })

    load_balancer_model.update_status(
        project_id=project_id,
        load_balancer_id=load_balancer_id,
        status=load_balancer_model.LOAD_BALANCER_STATUS_BUILDING
    )

    logger.info('.create() OK.')

    return (model.actions_job('CreateLoadBalancerBackend',
                              project_id,
                              [load_balancer_id],
                              []),
            load_balancer_backend_id)


def limitation(load_balancer_backend_ids=None,
               load_balancer_listener_ids=None, project_ids=None,
               verbose=False, status=None,
               search_word=None, offset=0, limit=10, reverse=True):
    def where(t):
        _where = True
        _where = filters.filter_ids(_where, t, load_balancer_backend_ids)
        _where = filters.filter_project_ids(_where, t, project_ids)
        _where = filters.filter_search_word(_where, t, search_word)
        _where = filters.filter_status(_where, t, status)

        if load_balancer_listener_ids is None:
            pass
        elif len(load_balancer_listener_ids) == 0:
            _where = False
        else:
            _where = and_(
                t.load_balancer_listener_id.in_(load_balancer_listener_ids),
                _where)
        return _where

    logger.info('.limitation() begin.')
    page = LoadBalancerBackend.limitation_as_model(
        where,
        limit=limit,
        offset=offset,
        order_by=filters.order_by(reverse))
    logger.info('.limitation() OK.')

    return page


def get(load_balancer_backend_id):
    logger.info('.get() begin. load_balancer_backend_id: %s' %
                load_balancer_backend_id)  # noqa

    load_balancer_backend = LoadBalancerBackend.get_as_model(
        load_balancer_backend_id)
    if load_balancer_backend is None:
        raise iaas_error.LoadBalancerBackendNotFound(
            load_balancer_backend_id)
    logger.info('.get() OK.')
    return load_balancer_backend


def modify(project_id, load_balancer_backend_id, name=None, description=None):
    logger.info('.modify() begin, load_balancer_backend: %s' %
                load_balancer_backend_id)

    load_balancer_backend = get(load_balancer_backend_id)
    load_balancer_backend.must_belongs_project(project_id)

    if name is None:
        name = load_balancer_backend['name']

    if description is None:
        description = load_balancer_backend['description']

    LoadBalancerBackend.update(load_balancer_backend_id, **{
        'name': name,
        'description': description,
        'updated': datetime.datetime.utcnow(),
    })

    logger.info('.modify() OK.')

    load_balancer_backend = get(load_balancer_backend_id)
    return load_balancer_backend


@base.transaction
def update(project_id,
           load_balancer_backend_id,
           weight):
    logger.info('.update() begin')

    backend = get(load_balancer_backend_id)
    backend.must_belongs_project(project_id)
    load_balancer_listener_id = backend['load_balancer_listener_id']
    load_balancer_listener = load_balancer_listener_model.get(
        load_balancer_listener_id)
    load_balancer_id = backend['load_balancer_id']
    with base.lock_for_update():
        load_balancer = load_balancer_model.get(load_balancer_id)

    # check loadbalancer status
    if (load_balancer_listener['status'] !=
        load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_ACTIVE) \
       or (load_balancer['status'] !=
           load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE) \
       or (backend['status'] != LOAD_BALANCER_BACKEND_STATUS_ACTIVE):
        raise iaas_error.LoadBalancerBackendCanNotUpdate(
            load_balancer_backend_id)

    try:
        network_provider.update_loadbalancer_member(
            loadbalancer_member_id=backend['op_member_id'],
            loadbalancer_pool_id=backend['op_pool_id'],
            weight=weight)
    except Exception as e:
        stack = traceback.format_exc()
        raise iaas_error.ProviderUpdateLoadBalancerBackendError(e, stack)
    if weight is not None:
        LoadBalancerBackend.update(load_balancer_backend_id, **{
            'weight': weight,
            'updated': datetime.datetime.utcnow()
        })

    load_balancer_id = backend['load_balancer_id']
    load_balancer_model.update_status(
        project_id=project_id,
        load_balancer_id=load_balancer_id,
        status=load_balancer_model.LOAD_BALANCER_STATUS_BUILDING
    )

    logger.info('.update() OK.')

    return model.actions_job('UpdateLoadBalancerBackend',
                             project_id,
                             [load_balancer_id],
                             [])


def count_backends_of_listener(load_balancer_listener_id):
    """
        count the backend number of the listener.
    """
    def where(t):
        _where = True
        _where = and_(
            _where,
            t.load_balancer_listener_id == load_balancer_listener_id
        )
        _where = and_(
            _where,
            t.status.in_([LOAD_BALANCER_BACKEND_STATUS_ACTIVE])
        )
        return _where
    count = LoadBalancerBackend.count(where)
    return count


def _pre_delete(project_id, load_balancer_backend_ids):
    load_balancer_backends = []
    for load_balancer_backend_id in load_balancer_backend_ids:
        load_balancer_backend = get(load_balancer_backend_id)
        load_balancer_id = load_balancer_backend['load_balancer_id']
        with base.lock_for_update():
            load_balancer = load_balancer_model.get(load_balancer_id)

        load_balancer_backend.must_belongs_project(project_id)
        load_balancer_listener_id = \
            load_balancer_backend['load_balancer_listener_id']
        load_balancer_listener = load_balancer_listener_model.get(
            load_balancer_listener_id)
        # check loadbalancer status
        if ((load_balancer['status'] !=
             load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE) and
            (load_balancer['status'] !=
             load_balancer_model.LOAD_BALANCER_STATUS_ERROR)) \
           or ((load_balancer_listener['status'] !=
                load_balancer_listener_model.
                LOAD_BALANCER_LISTENER_STATUS_ACTIVE) and
               (load_balancer_listener['status'] !=
                load_balancer_listener_model.
                LOAD_BALANCER_LISTENER_STATUS_ERROR)):
            raise iaas_error.LoadBalancerBackendCanNotDelete(
                load_balancer_backend_id)

        if not load_balancer_backend.status_deletable():
            raise iaas_error.LoadBalancerBackendCanNotDelete(
                load_balancer_backend_id)

        load_balancer_backends.append(load_balancer_backend)
    return load_balancer_backends


@base.transaction
def delete(project_id,
           load_balancer_backend_ids):
    logger.info('.delete() begin, '
                'total count: %s, load_balancer_backend_ids: %s' %
                (len(load_balancer_backend_ids), load_balancer_backend_ids))
    load_balancer_backends = _pre_delete(project_id,
                                         load_balancer_backend_ids)

    load_balancers = {}
    for load_balancer_backend in load_balancer_backends:
        lb_id = load_balancer_backend['load_balancer_id']
        lbb_id = load_balancer_backend['id']
        if lb_id not in load_balancers.keys():
            load_balancers[lb_id] = []
        load_balancers[lb_id].append(lbb_id)

        LoadBalancerBackend.update(lbb_id, **{
            'status': LOAD_BALANCER_BACKEND_STATUS_DELETED,
            'deleted': datetime.datetime.utcnow(),
        })
        load_balancer_model.update_status(
            project_id=project_id,
            load_balancer_id=lb_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    logger.info('.delete() OK.')
    for lbbs in load_balancers.values():
        job_model.create(
            action='EraseLoadBalancerBackends',
            params={
                'resource_ids': lbbs
            },
            try_period=10,
            try_max=1)


def erase(load_balancer_backend_id, is_last=False, try_time=0):
    logger.info('.erase() begin. load_balancer_backend_id: %s' % load_balancer_backend_id)  # noqa
    backend = get(load_balancer_backend_id)

    if backend['ceased']:
        logger.info('.erase() pass. already ceased.')
        return True
    # check loadbalancer status
    load_balancer_id = backend['load_balancer_id']
    load_balancer = load_balancer_model.get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = load_balancer_model.LOAD_BALANCER_STATUS_MAP[
        op_load_balancer_status]
    if status != load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE:
        if try_time == 3:
            LoadBalancerBackend.update(load_balancer_backend_id, **{
                'status': LOAD_BALANCER_BACKEND_STATUS_ACTIVE,
            })
            if is_last is True:
                load_balancer_model.LoadBalancer.update(
                    load_balancer_id,
                    **{'status':
                       load_balancer_model.LOAD_BALANCER_STATUS_ERROR})
        return False

    if backend['status'] == LOAD_BALANCER_BACKEND_STATUS_DELETED:
        try:
            network_provider.delete_loadbalancer_member(
                backend['op_member_id'],
                backend['op_pool_id'])
        except Exception as ex:
            if op_error.is_notfound(ex):
                pass
            else:
                if try_time == 3:
                    LoadBalancerBackend.update(load_balancer_backend_id, **{
                        'status': LOAD_BALANCER_BACKEND_STATUS_ACTIVE,
                    })
                    load_balancer_model.LoadBalancer.update(
                        load_balancer_id,
                        **{'status':
                           load_balancer_model.LOAD_BALANCER_STATUS_ERROR})
                trace = traceback.format_exc()
                raise iaas_error.ProviderDeleteLoadBalancerBackendError(
                    ex, trace)

        LoadBalancerBackend.update(load_balancer_backend_id, **{
            'ceased': datetime.datetime.utcnow(),
        })
        logger.info('.erase() OK. ceased.')

        if is_last is True:
            job_model.create(
                action='EraseLoadBalancerBackend',
                params={
                    'resource_ids': [backend['load_balancer_id']]
                },
                try_period=10)
    else:
        logger.warn('backend status is not DELETED, can not be ceased!')
        logger.warn('STRANGE, it should not enter .erase method!')

    return True
