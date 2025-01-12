import env  # noqa
import patches
import json
import datetime
from mock import patch
from nose import tools
from densefog.model.job import job as job_model
from rainbow.model.iaas import load_balancer as load_balancer_model
from rainbow.model.iaas import load_balancer_listener as load_balancer_listener_model  # noqa

import fixtures

project_id = 'prjct-1234'


def mock_create_listener(*args, **kwargs):
    return fixtures.op_mock_create_loadbalancer_listener


def mock_create_pool(*args, **kwargs):
    return fixtures.op_mock_create_loadbalancer_pool


def mock_create_healthmonitor(*args, **kwargs):
    return fixtures.op_mock_create_loadbalancer_healthmonitor


class TestModel:

    def setup(self):
        env.reset_db()
        self.project_id = fixtures.insert_project(project_id)
        self.load_balancer_id = fixtures.insert_load_balancer(
            project_id=self.project_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE
        )

    @patch('neutronclient.v2_0.client.Client.create_listener', mock_create_listener)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_pool', mock_create_pool)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_lbaas_healthmonitor', mock_create_healthmonitor)  # noqa
    def test_create(self):
        load_balancer_listener_model.create(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
            port=22,
            protocol='tcp',
            balance_mode='ROUND_ROBIN')

        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(load_balancer_listener_model.limitation()['total'], 1)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    def test_delete(self):
        load_balancer_listener_id = fixtures.insert_load_balancer_listener(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
        )

        load_balancer_listener_model.delete(self.project_id,
                                            [load_balancer_listener_id])

        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(job_model.limitation(
            run_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=20)
        )['total'], 1)
        tools.eq_(
            load_balancer_listener_model.get(
                load_balancer_listener_id)['status'],
            load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_DELETED)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    @patch('neutronclient.v2_0.client.Client.update_listener', fixtures.mock_nope)  # noqa
    @patch('neutronclient.v2_0.client.Client.update_pool', fixtures.mock_nope)
    @patch('neutronclient.v2_0.client.Client.update_lbaas_healthmonitor', fixtures.mock_nope)  # noqa
    def test_update(self):
        load_balancer_listener_id = fixtures.insert_load_balancer_listener(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
        )

        load_balancer_listener_model.update(self.project_id,
                                            load_balancer_listener_id,
                                            balance_mode='ROUND_ROBIN')

        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(
            load_balancer_listener_model.get(
                load_balancer_listener_id)['port'],
            22)
        tools.eq_(
            load_balancer_listener_model.get(
                load_balancer_listener_id)['balance_mode'],
            'ROUND_ROBIN')
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)


@patches.check_access_key(project_id)
class TestAPI:

    def setup(self):
        env.reset_db()
        self.project_id = fixtures.insert_project(project_id)
        self.load_balancer_id = fixtures.insert_load_balancer(
            project_id=self.project_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE
        )

    def test_public_describe_load_balancer_listeners(self):
        fixtures.insert_load_balancer_listener(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
        )

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'DescribeLoadBalancerListeners'
        }))
        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(1, json.loads(result.data)['data']['total'])

    @patch('neutronclient.v2_0.client.Client.create_listener', mock_create_listener)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_pool', mock_create_pool)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_lbaas_healthmonitor', mock_create_healthmonitor)  # noqa
    def test_public_create_load_balancer_listener(self):
        result = fixtures.public.post('/', data=json.dumps({
            'action': 'CreateLoadBalancerListener',
            'loadBalancerId': self.load_balancer_id,
            'port': 22,
            'protocol': 'TCP',
            'balanceMode': 'ROUND_ROBIN',
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(load_balancer_listener_model.limitation()['total'], 1)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    def test_public_delete_load_balancer_listeners(self):
        load_balancer_listener_id = fixtures.insert_load_balancer_listener(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
        )

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'DeleteLoadBalancerListeners',
            'loadBalancerListenerIds': [load_balancer_listener_id],
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(job_model.limitation(
            run_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=20)
        )['total'], 1)
        tools.eq_(
            load_balancer_listener_model.get(
                load_balancer_listener_id)['status'],
            load_balancer_listener_model.LOAD_BALANCER_LISTENER_STATUS_DELETED)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    @patch('neutronclient.v2_0.client.Client.update_listener', fixtures.mock_nope)  # noqa
    @patch('neutronclient.v2_0.client.Client.update_pool', fixtures.mock_nope)
    @patch('neutronclient.v2_0.client.Client.update_lbaas_healthmonitor', fixtures.mock_nope)  # noqa
    def test_update_load_balancer_listener(self):
        load_balancer_listener_id = fixtures.insert_load_balancer_listener(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
        )

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'UpdateLoadBalancerListener',
            'loadBalancerListenerId': load_balancer_listener_id,
            'port': 22,
            'balanceMode': 'ROUND_ROBIN'
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(
            load_balancer_listener_model.get(
                load_balancer_listener_id)['port'],
            22)
        tools.eq_(
            load_balancer_listener_model.get(
                load_balancer_listener_id)['balance_mode'],
            'ROUND_ROBIN')
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)
