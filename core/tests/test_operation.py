import env  # noqa
import time
import json
from mock import patch
from nose import tools
import patches
from densefog.common import utils
from densefog.common.utils import MockObject
from densefog.model.journal import operation as operation_model
# from rainbow.model.iaas import load_balancer as lb_model

import fixtures

project_id_1 = 'prjct-1234'


def mock_volume_create(*args, **kwargs):
    mock = MockObject(**fixtures.op_mock_volume)
    mock.id = utils.generate_uuid()
    return mock


def mock_nope(*args, **kwargs):
    return True


def mock_get_subnet(*args, **kwargs):
    return fixtures.op_mock_subnet['subnet']


def mock_count_floatingip(*args, **kwargs):
    return 1


def mock_create_loadbalancer(*args, **kwargs):
    return fixtures.op_mock_create_loadbalancer


class Test:

    def setup(self):
        env.reset_db()
        fixtures.insert_project(project_id_1)

    @patch('neutronclient.v2_0.client.Client.create_loadbalancer', mock_create_loadbalancer)  # noqa
    @patch('neutronclient.v2_0.client.Client.delete_loadbalancer', mock_nope)  # noqa
    @patch('rainbow.model.iaas.load_balancer.LoadBalancer.status_deletable', mock_nope)  # noqa
    @patch('rainbow.model.lcs.client.call', mock_nope)
    @patch('rainbow.model.lcs.client.get_subnet', mock_get_subnet)  # noqa
    @patch('rainbow.model.lcs.client.count_active_floatingip', mock_count_floatingip)  # noqa
    @patch('rainbow.billing.load_balancers.LoadBalancerBiller.create_load_balancers', mock_nope)  # noqa
    @patch('rainbow.billing.load_balancers.LoadBalancerBiller.delete_load_balancers', mock_nope)  # noqa
    @patches.check_access_key(project_id_1)
    def test_create(self):
        result = fixtures.public.post('/', data=json.dumps({
            'action': 'CreateLoadBalancer',
            'subnetId': '1',
        }))
        tools.eq_(0, json.loads(result.data)['retCode'])
        loadbalancer_id = json.loads(result.data)['data']['loadBalancerId']

        time.sleep(1)
        fixtures.public.post('/', data=json.dumps({
            'action': 'DeleteLoadBalancers',
            'loadBalancerIds': [loadbalancer_id]
        }))

        time.sleep(1)
        result = fixtures.public.post('/', data=json.dumps({
            'action': 'CreateLoadBalancer',
            'subnetId': '2',
        }))
        loadbalancer_id = json.loads(result.data)['data']['loadBalancerId']

        time.sleep(1)
        fixtures.public.post('/', data=json.dumps({
            'action': 'DeleteLoadBalancers',
            'loadBalancerIds': [loadbalancer_id]
        }))

        time.sleep(1)
        fixtures.public.post('/', data=json.dumps({
            'action': 'DeleteLoadBalancers',
            'loadBalancerIds': ['some-other-volume-id']
        }))

        limit = operation_model.limitation(
            project_ids=[project_id_1], reverse=False)
        tools.eq_(limit['total'], 5)

        op2 = limit['items'][2]
        tools.eq_(op2['ret_code'], 0)
        tools.eq_(op2['ret_message'], 'good job.')
        tools.eq_(op2['action'], 'CreateLoadBalancer')
        params = json.loads(op2['params'])
        tools.eq_(params['subnetId'], '2')
        tools.eq_(op2['resource_type'], 'loadBalancer')

        op4 = limit['items'][4]
        tools.eq_(op4['ret_code'], 4104)
        tools.eq_(op4['ret_message'], 'Load Balancer (some-other-volume-id) is not found')  # noqa
        tools.eq_(op4['action'], 'DeleteLoadBalancers')
        params = json.loads(op4['params'])
        tools.eq_(params['loadBalancerIds'][0], 'some-other-volume-id')
        tools.eq_(op4['resource_type'], 'loadBalancer')

        for i, v in enumerate(['CreateLoadBalancer',
                               'DeleteLoadBalancers',
                               'CreateLoadBalancer',
                               'DeleteLoadBalancers',
                               'DeleteLoadBalancers']):
            tools.eq_(limit['items'][i]['action'], v)

    @patches.check_access_key(project_id_1)
    def test_describe_operations(self):
        fixtures.insert_operation(project_id=project_id_1, action='CreateLoadBalancer')   # noqa
        fixtures.insert_operation(project_id=project_id_1, action='DeleteLoadBalancers')   # noqa
        fixtures.insert_operation(project_id=project_id_1, action='CreateLoadBalancer')   # noqa
        fixtures.insert_operation(project_id=project_id_1, action='DeleteLoadBalancers')   # noqa
        fixtures.insert_operation(project_id=project_id_1, action='DeleteLoadBalancers')   # noqa

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'DescribeOperations',
        }))

        data = json.loads(result.data)
        tools.eq_(data['retCode'], 0)
        tools.eq_(len(data['data']['operationSet']), 5)
