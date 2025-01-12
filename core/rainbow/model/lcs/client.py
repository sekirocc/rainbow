import json
import traceback
from densefog.common import request
from rainbow import config
from rainbow.model.lcs import error

from densefog import logger
logger = logger.getChild(__file__)


def call(payload):
    url = config.CONF.lcs_manage_endpoint + '/'
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'X-Le-Key': config.CONF.lcs_manage_key,
        'X-Le-SECRET': config.CONF.lcs_manage_secret,
    }
    data = json.dumps(payload)
    logger.info('url: %s, headers: %s, data: %s' %
                (url, headers, data))
    res = request.post(url,
                       payload=data,
                       headers=headers,
                       logger=logger)
    logger.info('res: %s' % res)
    data = json.loads(res)
    if data['retCode'] == 0:
        return data
    raise error.ClientHttpError(200, res)


def get_networks(project_ids, status=None,
                 offset=0, limit=20,
                 reverse=True, verbose=False):
    logger.info('.get_networks() start. ')
    result = call({
                  'action': 'DescribeNetworks',
                  'projectIds': project_ids,
                  'status': status,
                  'limit': limit,
                  'offset': offset,
                  'reverse': reverse,
                  'verbose': verbose
                  })
    logger.info('.get_networks() OK. ')
    return result['data']


def get_subnet(project_id, subnet_id):
    logger.info('.get_subnet() start. ')
    result = call({
                  'action': 'DescribeSubnets',
                  'projectIds': [project_id],
                  'subnetIds': [subnet_id],
                  'status': ['active']
                  })
    logger.info('.get_subnet() OK. ')
    return result['data']['subnetSet'][0]


def associate_loadbalancer_to_subnet(loadbalancer_id, subnet_id):
    logger.info('.associate_loadbalancer_to_subnet() start. ')
    call({
         'action': 'AddSubnetResources',
         'resourceIds': [loadbalancer_id],
         'resourceType': 'loadBalancer',
         'subnetId': subnet_id,
         })
    logger.info('.associate_loadbalancer_to_subnet() OK. ')


def disassociate_loadbalancers_from_subnet(loadbalancer_ids):
    logger.info('.disassociate_loadbalancers_from_subnet() start. ')
    try:
        call({
            'action': 'RemSubnetResources',
            'resourceIds': loadbalancer_ids,
            'resourceType': 'loadBalancer'
        })
    except error.ClientHttpError as e:
        data = json.loads(e.res_content)
        if data['retCode'] == 4104:
            stack = traceback.format_exc()
            logger.trace(stack)
        else:
            raise

    logger.info('.disassociate_loadbalancers_from_subnet OK. ')


def count_active_floatingip():
    logger.info('.count_active_floatingip() start. ')
    result = call({
                  'action': 'CountFloatingips',
                  })
    logger.info('.count_active_floatingip() OK. ')
    return result['data']['count']


def consume_floatingips(floatingips):
    logger.info('.consume_floatingips() start. ')
    call({
         'action': 'ConsumeFloatingips',
         'addresses': floatingips,
         })
    logger.info('.consume_floatingips() OK. ')


def release_floatingips(floatingips):
    logger.info('.release_floatingips() start. ')
    call({
         'action': 'ReleaseFloatingips',
         'addresses': floatingips,
         })
    logger.info('.release_floatingips() OK. ')
