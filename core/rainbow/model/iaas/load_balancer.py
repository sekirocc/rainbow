from rainbow import model
import datetime
import traceback
from densefog import db
from densefog.common import utils
from densefog.model import base
from densefog.model import filters
from rainbow.model.iaas import error as iaas_error
from rainbow.model.iaas.openstack import network as network_provider
from rainbow.model.iaas.openstack import error as op_error
from rainbow.model.project import project as project_model
from rainbow.model.lcs import client as lcs_client
from densefog.model.job import job as job_model

from densefog import logger
logger = logger.getChild(__file__)

LOAD_BALANCER_STATUS_PENDING = 'pending'
LOAD_BALANCER_STATUS_ACTIVE = 'active'
LOAD_BALANCER_STATUS_BUILDING = 'building'
LOAD_BALANCER_STATUS_ERROR = 'error'
LOAD_BALANCER_STATUS_DELETED = 'deleted'

DEFAULT_BANDWIDTH = 1

LOAD_BALANCER_STATUS_MAP = {
    network_provider.LOADBALANCER_STATUS_ACTIVE: LOAD_BALANCER_STATUS_ACTIVE,  # noqa
    network_provider.LOADBALANCER_STATUS_PENDING_CREATE: LOAD_BALANCER_STATUS_PENDING,  # noqa
    network_provider.LOADBALANCER_STATUS_PENDING_UPDATE: LOAD_BALANCER_STATUS_BUILDING,  # noqa
    network_provider.LOADBALANCER_STATUS_PENDING_DELETE: LOAD_BALANCER_STATUS_BUILDING,  # noqa
    network_provider.LOADBALANCER_STATUS_INACTIVE: LOAD_BALANCER_STATUS_ERROR,  # noqa
    network_provider.LOADBALANCER_STATUS_ERROR: LOAD_BALANCER_STATUS_ERROR,  # noqa
}


class LoadBalancer(base.ResourceModel):

    @classmethod
    def db(cls):
        return db.DB.load_balancer

    def status_deletable(self):
        return self['status'] in [
            LOAD_BALANCER_STATUS_ACTIVE,
            LOAD_BALANCER_STATUS_ERROR,
        ]

    def status_updatable(self):
        return self['status'] in [
            LOAD_BALANCER_STATUS_ACTIVE
        ]

    def format(self):
        formated = {
            'loadBalancerId': self['id'],
            'projectId': self['project_id'],
            'name': self['name'],
            'subnetId': self['subnet_id'],
            'description': self['description'],
            'status': self['status'],
            'address': self['address'],
            'bandwidth': self['bandwidth'],
            'updated': self['updated'],
            'created': self['created'],
            'deleted': self['deleted'],
            'ceased': self['ceased'],
        }
        return formated


def create(project_id, subnet_id, bandwidth=DEFAULT_BANDWIDTH,
           name='', description=''):
    logger.info('.create() begin')

    active_floatingips = lcs_client.count_active_floatingip()
    if active_floatingips < 1:
        raise iaas_error.CreateEipInsufficientFloatingip(1, active_floatingips)

    subnet = lcs_client.get_subnet(project_id, subnet_id)
    op_subnet_id = subnet['opSubnetId']

    with base.open_transaction(db.DB):
        with base.lock_for_update():
            project = project_model.get(project_id)

        project.must_have_enough_quota('load_balancers', 1)
        # assume creation success
        project.consume_quota('load_balancers', 1)

    op_project_id = project['op_project_id']
    key = utils.generate_key(8)
    load_balancer_id = 'lb-%s' % key

    try:
        op_loadbalancer = network_provider.create_loadbalancer(
            op_project_id,
            subnet_id=op_subnet_id,
            name=load_balancer_id,
            rate_limit=bandwidth)
    except Exception as e:
        # rollback the quota
        with base.open_transaction(db.DB):
            with base.lock_for_update():
                project = project_model.get(project_id)
            # but we failed.
            project.release_quota('load_balancers', 1)

        stack = traceback.format_exc()
        raise iaas_error.ProviderCreateLoadBalancerError(e, stack)

    vip_address = op_loadbalancer['vip_address']
    vip_port_id = op_loadbalancer['vip_port_id']

    load_balancer_id = LoadBalancer.insert(**{
        'id': load_balancer_id,
        'project_id': project_id,
        'name': name,
        'subnet_id': subnet_id,
        'description': description,
        'bandwidth': bandwidth,
        'address': vip_address,
        'op_floatingip_id': vip_port_id,
        'op_loadbalancer_id': op_loadbalancer['id'],
        'status': LOAD_BALANCER_STATUS_PENDING,
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })

    try:
        lcs_client.consume_floatingips([vip_address])
        lcs_client.associate_loadbalancer_to_subnet(load_balancer_id,
                                                    subnet_id)
        logger.info('.create() OK.')
    except Exception:
        LoadBalancer.update(load_balancer_id,
                            **{'status': LOAD_BALANCER_STATUS_ERROR})
        raise

    return (model.actions_job('CreateLoadBalancer',
                              project_id,
                              [load_balancer_id],
                              []),
            load_balancer_id)


def _pre_delete(project_id, load_balancer_ids):
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    load_balancers = []

    for load_balancer_id in load_balancer_ids:
        with base.lock_for_update():
            load_balancer = get(load_balancer_id)

        load_balancer.must_belongs_project(project_id)
        if not load_balancer.status_deletable():
            raise iaas_error.LoadBalancerCanNotDelete(load_balancer_id)

        check_listener = lbl_model.count_listeners_of_loadbancer(
            load_balancer_id)
        if check_listener != 0:
            raise iaas_error.LoadBalancerInUse(load_balancer_id)

        load_balancers.append(load_balancer)

    return load_balancers


@base.transaction
def delete(project_id, load_balancer_ids):
    logger.info('.delete() begin, total count: %s, load_balancer_ids: %s' %
                (len(load_balancer_ids), load_balancer_ids))

    load_balancers = _pre_delete(project_id, load_balancer_ids)
    addresses = [load_balancer['address'] for load_balancer in load_balancers]

    for load_balancer_id in load_balancer_ids:
        LoadBalancer.update(load_balancer_id, **{
            'status': LOAD_BALANCER_STATUS_DELETED,
            'deleted': datetime.datetime.utcnow(),
        })

    with base.lock_for_update():
        project = project_model.get(project_id)
        project.release_quota('load_balancers', len(load_balancer_ids))

    lcs_client.release_floatingips(addresses)
    lcs_client.disassociate_loadbalancers_from_subnet(load_balancer_ids)
    logger.info('.delete() OK: %s')

    job_model.create(
        action='EraseLoadBalancers',
        params={
            'resource_ids': load_balancer_ids
        },
        run_at=utils.seconds_later(10),   # as fast as possible
        try_period=10)


def modify(project_id, load_balancer_id, name=None, description=None):
    logger.info('.modify() begin, load_balancer: %s' % load_balancer_id)

    load_balancer = get(load_balancer_id)
    load_balancer.must_belongs_project(project_id)

    if name is None:
        name = load_balancer['name']

    if description is None:
        description = load_balancer['description']

    LoadBalancer.update(load_balancer_id, **{
        'name': name,
        'description': description,
        'updated': datetime.datetime.utcnow(),
    })

    logger.info('.modify() OK.')

    load_balancer = get(load_balancer_id)
    return load_balancer


def _pre_update(project_id, load_balancer_ids):
    """
    load_balancer should be active,
    """
    load_balancers = []
    for load_balancer_id in load_balancer_ids:
        with base.lock_for_update():
            load_balancer = get(load_balancer_id)

        load_balancer.must_belongs_project(project_id)
        if not load_balancer.status_updatable():
            raise iaas_error.LoadBalancerCanNotUpdate(load_balancer_id)
        load_balancers.append(load_balancer)

    return load_balancers


@base.transaction
def update_status(project_id, load_balancer_id, status):
    with base.lock_for_update():
        load_balancer = get(load_balancer_id)

    load_balancer.must_belongs_project(project_id)
    LoadBalancer.update(load_balancer_id, **{
        'status': status,
        'updated': datetime.datetime.utcnow(),
    })


@base.transaction
def update(project_id, load_balancer_ids, bandwidth):
    logger.info('.update() begin, total count: %s' % len(load_balancer_ids))
    load_balancers = _pre_update(project_id, load_balancer_ids)

    updateds = []
    exceptions = []
    for load_balancer in load_balancers:
        load_balancer_id = load_balancer['id']
        try:
            network_provider.update_loadbalancer_rate_limit(
                load_balancer['op_loadbalancer_id'], rate_limit=bandwidth)
        except Exception as e:
            stack = traceback.format_exc()  # noqa
            e = iaas_error.ProviderUpdateFloatingipError(e, stack)

            exceptions.append({
                'load_balancer': None,
                'exception': e
            })
        else:
            LoadBalancer.update(load_balancer_id, **{
                'bandwidth': bandwidth,
                'updated': datetime.datetime.utcnow(),
            })
            updateds.append(load_balancer_id)

    logger.info('.update() OK, updateds: %s, exceptions: %s' %
                (len(updateds), len(exceptions)))

    return model.actions_result(updateds,
                                exceptions)


def get(load_balancer_id):
    logger.info('.get() begin. load_balancer_id: %s' % load_balancer_id)

    load_balancer = LoadBalancer.get_as_model(load_balancer_id)
    if load_balancer is None:
        raise iaas_error.LoadBalancerNotFound(load_balancer_id)
    logger.info('.get() OK.')
    return load_balancer


def limitation(load_balancer_ids=None, status=None, project_ids=None,
               verbose=False,
               search_word=None, offset=0, limit=10, reverse=True):
    def where(t):
        _where = True
        _where = filters.filter_ids(_where, t, load_balancer_ids)
        _where = filters.filter_project_ids(_where, t, project_ids)
        _where = filters.filter_search_word(_where, t, search_word)
        _where = filters.filter_status(_where, t, status)
        return _where

    logger.info('.limitation() begin.')

    page = LoadBalancer.limitation_as_model(where,
                                            limit=limit,
                                            offset=offset,
                                            order_by=filters.order_by(reverse))
    if verbose:
        # TODO:
        pass

    logger.info('.limitation() OK.')

    return page


def sync(load_balancer_id):
    logger.info('.sync() begin. load_balancer_id: %s' % load_balancer_id)

    load_balancer = get(load_balancer_id)
    op_loadbalancer_id = load_balancer['op_loadbalancer_id']

    op_load_balancer = network_provider.get_loadbalancer(op_loadbalancer_id)
    op_load_balancer_status = op_load_balancer['provisioning_status']

    status = LOAD_BALANCER_STATUS_MAP[op_load_balancer_status]
    logger.info('load_balancer status: (%s) => (%s) .' % (load_balancer['status'], status))  # noqa

    LoadBalancer.update(load_balancer_id, **{
        'status': status,
        'updated': datetime.datetime.utcnow(),
    })

    logger.info('.sync() OK.')

    load_balancer = get(load_balancer_id)
    return load_balancer


def erase(load_balancer_id):
    logger.info('.erase() begin. load_balancer_id: %s' % load_balancer_id)
    load_balancer = get(load_balancer_id)

    if load_balancer['ceased']:
        logger.info('.erase() pass. already ceased.')
        return

    if load_balancer['status'] == LOAD_BALANCER_STATUS_DELETED:
        # TODO
        # check listener & backends

        # delete load balancer
        try:
            network_provider.delete_loadbalancer(
                load_balancer['op_loadbalancer_id'])
        except Exception as ex:
            if op_error.is_notfound(ex):
                pass
            else:
                LoadBalancer.update(load_balancer_id, **{
                    'status': LOAD_BALANCER_STATUS_ERROR,
                })
                trace = traceback.format_exc()
                raise iaas_error.ProviderDeleteLoadBalancerError(ex, trace)

        LoadBalancer.update(load_balancer_id, **{
            'ceased': datetime.datetime.utcnow(),
        })
        logger.info('.erase() OK. ceased.')
    else:
        logger.warn('load_balancer status is not DELETED, can not be ceased!')
        logger.warn('STRANGE, it should not enter .erase method!')
