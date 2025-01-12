import env  # noqa
import patches
import json
import datetime
from mock import patch
from nose import tools
from densefog.model.job import job as job_model
from rainbow.model.iaas import load_balancer as load_balancer_model
from rainbow.model.iaas import load_balancer_backend as load_balancer_backend_model  # noqa

import fixtures

project_id = 'prjct-1234'
rand_id = 'some-unimportant-id'


def mock_create_member(*args, **kwargs):
    return fixtures.op_mock_create_loadbalancer_member


def mock_get_subnet(*args, **kwargs):
    return fixtures.op_mock_subnet['subnet']


class TestModel:

    def setup(self):
        env.reset_db()
        self.project_id = fixtures.insert_project(project_id)
        self.load_balancer_id = fixtures.insert_load_balancer(
            project_id=self.project_id,
            subnet_id=rand_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE
        )
        self.load_balancer_listener_id = \
            fixtures.insert_load_balancer_listener(
                project_id=self.project_id,
                load_balancer_id=self.load_balancer_id,
            )

    @patch('rainbow.model.lcs.client.get_subnet', mock_get_subnet)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_lbaas_member', mock_create_member)  # noqa
    def test_create(self):
        load_balancer_backend_model.create(
            project_id=self.project_id,
            load_balancer_listener_id=self.load_balancer_listener_id,
            address='192.168.1.1',
            port=22,
            weight=1)

        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(load_balancer_backend_model.limitation()['total'], 1)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    def test_delete(self):
        load_balancer_backend_id = fixtures.insert_load_balancer_backend(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
            load_balancer_listener_id=self.load_balancer_listener_id,
        )

        load_balancer_backend_model.delete(self.project_id,
                                           [load_balancer_backend_id])

        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(job_model.limitation(
            run_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=20)
        )['total'], 1)
        tools.eq_(
            load_balancer_backend_model.get(
                load_balancer_backend_id)['status'],
            load_balancer_backend_model.LOAD_BALANCER_BACKEND_STATUS_DELETED)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    @patch('neutronclient.v2_0.client.Client.update_lbaas_member', fixtures.mock_nope)  # noqa
    def test_update(self):
        load_balancer_backend_id = fixtures.insert_load_balancer_backend(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
            load_balancer_listener_id=self.load_balancer_listener_id,
        )

        load_balancer_backend_model.update(self.project_id,
                                           load_balancer_backend_id,
                                           weight=20)

        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(
            load_balancer_backend_model.get(
                load_balancer_backend_id)['weight'],
            20)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)


@patches.check_access_key(project_id)
class TestAPI:

    def setup(self):
        env.reset_db()
        self.project_id = fixtures.insert_project(project_id)
        self.load_balancer_id = fixtures.insert_load_balancer(
            project_id=self.project_id,
            subnet_id=rand_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE
        )
        self.load_balancer_listener_id = \
            fixtures.insert_load_balancer_listener(
                project_id=self.project_id,
                load_balancer_id=self.load_balancer_id,
            )

    def test_public_describe_load_balancer_backends(self):
        fixtures.insert_load_balancer_backend(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
            load_balancer_listener_id=self.load_balancer_listener_id,
        )

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'DescribeLoadBalancerBackends'
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(1, json.loads(result.data)['data']['total'])

    @patch('rainbow.model.lcs.client.get_subnet', mock_get_subnet)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_lbaas_member', mock_create_member)  # noqa
    def test_public_create_load_balancer_backend(self):
        result = fixtures.public.post('/', data=json.dumps({
            'action': 'CreateLoadBalancerBackend',
            'loadBalancerListenerId': self.load_balancer_listener_id,
            'address': '192.168.1.1',
            'port': 22,
            'weight': 1,
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(load_balancer_backend_model.limitation()['total'], 1)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    def test_delete(self):
        load_balancer_backend_id = fixtures.insert_load_balancer_backend(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
            load_balancer_listener_id=self.load_balancer_listener_id,
        )

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'DeleteLoadBalancerBackends',
            'loadBalancerBackendIds': [load_balancer_backend_id],
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(job_model.limitation(
            run_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=20)
        )['total'], 1)
        tools.eq_(
            load_balancer_backend_model.get(
                load_balancer_backend_id)['status'],
            load_balancer_backend_model.LOAD_BALANCER_BACKEND_STATUS_DELETED)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

    @patch('neutronclient.v2_0.client.Client.update_lbaas_member', fixtures.mock_nope)  # noqa
    def test_update(self):
        load_balancer_backend_id = fixtures.insert_load_balancer_backend(
            project_id=self.project_id,
            load_balancer_id=self.load_balancer_id,
            load_balancer_listener_id=self.load_balancer_listener_id,
        )

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'UpdateLoadBalancerBackend',
            'loadBalancerBackendId': load_balancer_backend_id,
            'weight': 20,
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(
            load_balancer_backend_model.get(
                load_balancer_backend_id)['weight'],
            20)
        tools.eq_(load_balancer_model.get(self.load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)
