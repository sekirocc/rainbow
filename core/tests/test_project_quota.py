import json
from copy import copy
import env  # noqa
from mock import patch
from nose import tools
import patches
from densefog.common import utils
from densefog.common.utils import MockObject
from rainbow.model.project import project as project_model
from rainbow.model.project import error as project_error
from rainbow.model.iaas import load_balancer as lb_model

import fixtures
import fixtures_openstack as op_fixtures

project_id_1 = 'prjct-1234'
rand_id = 'some-unimportant-id'


def mock_nope(*args, **kwargs):
    return True


def mock_create_project(*args, **kwargs):
    server = MockObject(**copy(op_fixtures.op_mock_project))
    server.id = utils.generate_key(32)
    return server


def mock_find_role(*args, **kwargs):
    role = MockObject(**copy(op_fixtures.op_mock_role))
    return role


def mock_find_user(*args, **kwargs):
    user = MockObject(**copy(op_fixtures.op_mock_user))
    return user


def mock_op_quota(*args, **kwargs):
    return copy(op_fixtures.op_mock_update_quota)


def mock_get_subnet(*args, **kwargs):
    return fixtures.op_mock_subnet['subnet']


def mock_count_floatingip(*args, **kwargs):
    return 1


def mock_create_loadbalancer(*args, **kwargs):
    return fixtures.op_mock_create_loadbalancer


@patch('keystoneclient.v3.projects.ProjectManager.create', mock_create_project)
@patch('keystoneclient.v3.projects.ProjectManager.list', mock_nope)
@patch('keystoneclient.v3.projects.ProjectManager.update', mock_nope)
@patch('keystoneclient.v3.projects.ProjectManager.delete', mock_nope)
@patch('keystoneclient.v3.roles.RoleManager.grant', mock_nope)
@patch('keystoneclient.v3.users.UserManager.list', mock_nope)
@patch('keystoneclient.v3.users.UserManager.find', mock_find_user)
@patch('densefog.model.base.ResourceModel.must_not_busy', mock_nope)
@patch('rainbow.model.iaas.load_balancer.LoadBalancer.status_deletable', mock_nope)  # noqa
class TestModel:

    def setup(self):
        env.reset_db()

    @patch('rainbow.model.lcs.client.call', mock_nope)
    @patch('rainbow.model.lcs.client.get_subnet', mock_get_subnet)  # noqa
    @patch('rainbow.model.lcs.client.count_active_floatingip', mock_count_floatingip)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_loadbalancer', mock_create_loadbalancer)  # noqa
    def test_qt_loadbalancers(self):
        fixtures.insert_project(project_id_1, qt_load_balancers=2)

        (job_id, lb_id_a) = lb_model.create(project_id_1, '1')
        lb_model.create(project_id_1, '2')

        project = project_model.get(project_id_1)
        tools.eq_(project['cu_load_balancers'], 2)

        with tools.assert_raises(project_error.ResourceQuotaNotEnough):
            lb_model.create(project_id_1, '3')

        lb_model.delete(project_id_1, [lb_id_a])

        project = project_model.get(project_id_1)
        tools.eq_(project['cu_load_balancers'], 1)


@patch('keystoneclient.v3.projects.ProjectManager.create', mock_create_project)
@patch('keystoneclient.v3.projects.ProjectManager.list', mock_nope)
@patch('keystoneclient.v3.projects.ProjectManager.update', mock_nope)
@patch('keystoneclient.v3.projects.ProjectManager.delete', mock_nope)
@patch('keystoneclient.v3.roles.RoleManager.grant', mock_nope)
@patch('keystoneclient.v3.users.UserManager.list', mock_nope)
@patch('keystoneclient.v3.users.UserManager.find', mock_find_user)
@patch('densefog.model.base.ResourceModel.must_not_busy', mock_nope)
@patch('rainbow.model.iaas.load_balancer.LoadBalancer.status_deletable', mock_nope)  # noqa
@patches.check_access_key(project_id_1)
class TestAPI:

    def setup(self):
        env.reset_db()

    @patch('rainbow.model.lcs.client.call', mock_nope)
    @patch('rainbow.model.lcs.client.get_subnet', mock_get_subnet)  # noqa
    @patch('rainbow.model.lcs.client.count_active_floatingip', mock_count_floatingip)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_loadbalancer', mock_create_loadbalancer)  # noqa
    @patch('rainbow.billing.load_balancers.LoadBalancerBiller.create_load_balancers', mock_nope)  # noqa
    def test_describe_quotas(self):
        fixtures.insert_project(project_id_1,
                                qt_load_balancers=2)

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'CreateLoadBalancer',
            'subnetId': rand_id,
        }))
        tools.eq_(0, json.loads(result.data)['retCode'])

        result = fixtures.public.post('/', data=json.dumps({
            'action': 'DescribeQuotas'
        }))
        tools.eq_(0, json.loads(result.data)['retCode'])

        data = json.loads(result.data)
        tools.eq_(2, data['data']['total']['loadBalancers'])
        tools.eq_(1, data['data']['usage']['loadBalancers'])

    @patch('rainbow.model.lcs.client.call', mock_nope)
    @patch('rainbow.model.lcs.client.get_subnet', mock_get_subnet)  # noqa
    @patch('rainbow.model.lcs.client.count_active_floatingip', mock_count_floatingip)  # noqa
    @patch('neutronclient.v2_0.client.Client.create_loadbalancer', mock_create_loadbalancer)  # noqa
    @patch('rainbow.billing.load_balancers.LoadBalancerBiller.create_load_balancers', mock_nope)  # noqa
    def test_qt_load_balancers(self):
        fixtures.insert_project(project_id_1, qt_load_balancers=1)

        def send_request():
            result = fixtures.public.post('/', data=json.dumps({
                'action': 'CreateLoadBalancer',
                'subnetId': rand_id,
            }))

            return result

        result = send_request()
        tools.eq_(0, json.loads(result.data)['retCode'])

        result = send_request()

        data = json.loads(result.data)
        tools.eq_(data['retCode'], 4113)
        tools.eq_(data['message'],
                  'Project quota[load_balancers] not enough: want [1], but have [0]')  # noqa
        tools.eq_(data['data']['quota'], 1)
        tools.eq_(data['data']['used'], 1)
        tools.eq_(data['data']['want'], 1)
