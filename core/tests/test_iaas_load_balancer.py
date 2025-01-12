import env  # noqa
import patches
import json
import datetime
import copy
from mock import patch
from nose import tools
from densefog.model.job import job as job_model
from rainbow.model.iaas import load_balancer as load_balancer_model
from rainbow.model.iaas import error as iaas_error
from rainbow.model.iaas.openstack import network as network_provider

import fixtures

project_id = 'prjct-1234'
rand_id = 'some-unimportant-id'


def mock_create_loadbalancer(*args, **kwargs):
    return fixtures.op_mock_create_loadbalancer


def mock_nope(*args, **kwargs):
    return True


def mock_get_subnet(*args, **kwargs):
    return fixtures.op_mock_subnet['subnet']


def mock_count_floatingip(*args, **kwargs):
    return 1


class TestModel:

    def setup(self):
        env.reset_db()
        fixtures.insert_project(project_id)

    @patch('rainbow.model.lcs.client.call', mock_nope)
    @patch('rainbow.model.lcs.client.get_subnet', mock_get_subnet)  # noqa
    @patch('rainbow.model.lcs.client.count_active_floatingip', mock_count_floatingip)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_loadbalancer', mock_create_loadbalancer)  # noqa
    def test_create(self):
        with patch('rainbow.model.lcs.client.count_active_floatingip', return_value=0):  # noqa
            with tools.assert_raises(iaas_error.CreateEipInsufficientFloatingip):  # noqa
                load_balancer_model.create(project_id=project_id,
                                           subnet_id=rand_id,
                                           bandwidth=1,
                                           name='lb-aaa')

        (job_id, load_balancer_id) = load_balancer_model.create(
            project_id=project_id,
            subnet_id=rand_id,
            bandwidth=1,
            name='lb-aaa')

        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(load_balancer_model.limitation()['total'], 1)
        tools.eq_(load_balancer_model.get(load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_PENDING)

    def test_sync(self):
        load_balancer_id = fixtures.insert_load_balancer(project_id)

        mock = {
            'loadbalancers': [
                copy.deepcopy(
                    fixtures.op_mock_create_loadbalancer['loadbalancer']
                )
            ]
        }
        mock['loadbalancers'][0]['provisioning_status'] = network_provider.LOADBALANCER_STATUS_PENDING_CREATE  # noqa
        with patch('neutronclient.v2_0.client.Client.list_loadbalancers', return_value=mock):  # noqa
            load_balancer = load_balancer_model.sync(load_balancer_id)
            tools.eq_(load_balancer['status'],
                      load_balancer_model.LOAD_BALANCER_STATUS_PENDING)

        mock['loadbalancers'][0]['provisioning_status'] = network_provider.LOADBALANCER_STATUS_PENDING_UPDATE  # noqa
        with patch('neutronclient.v2_0.client.Client.list_loadbalancers', return_value=mock):  # noqa
            load_balancer = load_balancer_model.sync(load_balancer_id)
            tools.eq_(load_balancer['status'],
                      load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

        mock['loadbalancers'][0]['provisioning_status'] = network_provider.LOADBALANCER_STATUS_PENDING_DELETE  # noqa
        with patch('neutronclient.v2_0.client.Client.list_loadbalancers', return_value=mock):  # noqa
            load_balancer = load_balancer_model.sync(load_balancer_id)
            tools.eq_(load_balancer['status'],
                      load_balancer_model.LOAD_BALANCER_STATUS_BUILDING)

        mock['loadbalancers'][0]['provisioning_status'] = network_provider.LOADBALANCER_STATUS_ACTIVE  # noqa
        with patch('neutronclient.v2_0.client.Client.list_loadbalancers', return_value=mock):  # noqa
            load_balancer = load_balancer_model.sync(load_balancer_id)
            tools.eq_(load_balancer['status'],
                      load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE)

        mock['loadbalancers'][0]['provisioning_status'] = network_provider.LOADBALANCER_STATUS_INACTIVE  # noqa
        with patch('neutronclient.v2_0.client.Client.list_loadbalancers', return_value=mock):  # noqa
            load_balancer = load_balancer_model.sync(load_balancer_id)
            tools.eq_(load_balancer['status'],
                      load_balancer_model.LOAD_BALANCER_STATUS_ERROR)

        mock['loadbalancers'][0]['provisioning_status'] = network_provider.LOADBALANCER_STATUS_ERROR  # noqa
        with patch('neutronclient.v2_0.client.Client.list_loadbalancers', return_value=mock):  # noqa
            load_balancer = load_balancer_model.sync(load_balancer_id)
            tools.eq_(load_balancer['status'],
                      load_balancer_model.LOAD_BALANCER_STATUS_ERROR)

    def test_modify(self):
        load_balancer_id = fixtures.insert_load_balancer(project_id)

        load_balancer_model.modify(project_id,
                                   load_balancer_id,
                                   name='lb-name-2',
                                   description='description-2')

        tools.eq_(load_balancer_model.get(load_balancer_id)['description'],
                  'description-2')
        tools.eq_(load_balancer_model.get(load_balancer_id)['name'],
                  'lb-name-2')

    @patch('neutronclient.v2_0.client.Client.update_loadbalancer', mock_nope)
    def test_update(self):
        load_balancer_id = fixtures.insert_load_balancer(project_id)

        load_balancer_model.update(project_id,
                                   [load_balancer_id],
                                   bandwidth=10)

        tools.eq_(load_balancer_model.get(load_balancer_id)['bandwidth'],
                  10)

    @patch('rainbow.model.lcs.client.call', mock_nope)
    def test_delete(self):
        load_balancer_id = fixtures.insert_load_balancer(
            project_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE
        )

        load_balancer_model.delete(project_id,
                                   [load_balancer_id])

        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(job_model.limitation(
            run_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=20)
        )['total'], 1)
        tools.eq_(load_balancer_model.limitation()['total'], 1)
        tools.eq_(load_balancer_model.get(load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_DELETED)

    @patch('neutronclient.v2_0.client.Client.delete_loadbalancer', mock_nope)
    def test_erase(self):
        load_balancer_id = fixtures.insert_load_balancer(
            project_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_DELETED
        )

        load_balancer_model.erase(load_balancer_id)

        tools.eq_(
            load_balancer_model.get(load_balancer_id)['status'],
            load_balancer_model.LOAD_BALANCER_STATUS_DELETED)
        tools.assert_not_equal(
            load_balancer_model.get(load_balancer_id)['ceased'],
            None)


@patches.check_access_key(project_id)
class TestAPI:

    def setup(self):
        env.reset_db()
        fixtures.insert_project(project_id)

    def test_public_describe_load_balancers(self):
        fixtures.insert_load_balancer(project_id=project_id)

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'DescribeLoadBalancers'
        }))
        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(1, json.loads(result.data)['data']['total'])

    @patch('rainbow.model.lcs.client.call', mock_nope)
    @patch('rainbow.model.lcs.client.get_subnet', mock_get_subnet)  # noqa
    @patch('rainbow.model.lcs.client.count_active_floatingip', mock_count_floatingip)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_loadbalancer', mock_create_loadbalancer)  # noqa
    @patch('rainbow.billing.load_balancers.LoadBalancerBiller.create_load_balancers', mock_nope)  # noqa
    def test_public_create_load_balancer(self):
        result = fixtures.public.post('/', data=json.dumps({
            'action': 'CreateLoadBalancer',
            'subnetId': rand_id,
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])

        load_balancer_id = json.loads(result.data)['data']['loadBalancerId']
        tools.eq_(load_balancer_model.limitation(
            load_balancer_ids=[load_balancer_id])['total'], 1)

    @patch('rainbow.model.lcs.client.call', mock_nope)
    @patch('rainbow.billing.load_balancers.LoadBalancerBiller.delete_load_balancers', mock_nope)  # noqa
    def test_public_delete_load_balancers(self):
        load_balancer_id = fixtures.insert_load_balancer(
            project_id,
            status=load_balancer_model.LOAD_BALANCER_STATUS_ACTIVE
        )

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'DeleteLoadBalancers',
            'loadBalancerIds': [load_balancer_id],
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(job_model.limitation()['total'], 1)
        tools.eq_(job_model.limitation(
            run_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=20)
        )['total'], 1)
        tools.eq_(load_balancer_model.limitation()['total'], 1)
        tools.eq_(load_balancer_model.get(load_balancer_id)['status'],
                  load_balancer_model.LOAD_BALANCER_STATUS_DELETED)

    def test_public_modify_load_balancer_attributes(self):
        load_balancer_id = fixtures.insert_load_balancer(project_id)

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'ModifyLoadBalancerAttributes',
            'loadBalancerId': load_balancer_id,
            'name': 'lb-name-2',
            'description': 'description-2'
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(load_balancer_model.get(load_balancer_id)['description'],
                  'description-2')
        tools.eq_(load_balancer_model.get(load_balancer_id)['name'],
                  'lb-name-2')

    @patch('neutronclient.v2_0.client.Client.update_loadbalancer', mock_nope)
    @patch('rainbow.billing.load_balancers.LoadBalancerBiller.update_bandwidth', mock_nope)  # noqa
    def test_public_update_load_balancer_bandwidth(self):
        load_balancer_id = fixtures.insert_load_balancer(project_id)

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'UpdateLoadBalancerBandwidth',
            'loadBalancerIds': [load_balancer_id],
            'bandwidth': 10,
        }))

        tools.eq_(0, json.loads(result.data)['retCode'])
        tools.eq_(load_balancer_model.get(load_balancer_id)['bandwidth'],
                  10)
