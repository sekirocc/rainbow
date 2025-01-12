import json
import env  # noqa
from mock import patch
import patches
from nose import tools
from densefog.common import utils
from densefog.common.utils import MockObject
from rainbow.model.project import project as project_model

import fixtures

project_id_1 = 'prjct-1234'

project_id_a = 'project-123-a'
project_id_b = 'project-456-b'


def mock_nope(*args, **kwargs):
    return True


def mock_none(*args, **kwargs):
    raise


def mock_create_project(*args, **kwargs):
    server = MockObject(**fixtures.op_mock_project)
    server.id = utils.generate_key(32)
    return server


def mock_find_role(*args, **kwargs):
    role = MockObject(**fixtures.op_mock_role)
    return role


def mock_find_user(*args, **kwargs):
    user = MockObject(**fixtures.op_mock_user)
    return user


def mock_op_quota(*args, **kwargs):
    return fixtures.op_mock_update_quota


@patch('keystoneclient.v3.projects.ProjectManager.create', mock_create_project)
@patch('keystoneclient.v3.domains.DomainManager.find', mock_nope)
@patch('keystoneclient.v3.projects.ProjectManager.list', mock_none)
@patch('keystoneclient.v3.projects.ProjectManager.update', mock_nope)
@patch('keystoneclient.v3.projects.ProjectManager.delete', mock_nope)
@patch('keystoneclient.v3.roles.RoleManager.find', mock_find_role)
@patch('keystoneclient.v3.roles.RoleManager.grant', mock_nope)
@patch('keystoneclient.v3.users.UserManager.list', mock_nope)
@patch('keystoneclient.v3.users.UserManager.find', mock_find_user)
@patch('neutronclient.v2_0.client.Client.update_quota', mock_op_quota)
class TestModel:

    def setup(self):
        env.reset_db()

    def test_create(self):
        project_model.create('tnt_id_a', 10)   # noqa
        project_model.create('tnt_id_b', 10)   # noqa

        tools.eq_(project_model.limitation()['total'], 2)

    def test_update(self):
        project_id = fixtures.insert_project('project_id_a')
        project_model.update(project_id, **{
            'qt_load_balancers': 11,
        })

        t = project_model.get(project_id)
        tools.eq_(t['qt_load_balancers'], 11)

    def test_get(self):
        project_id = fixtures.insert_project('project_id_a')
        t = project_model.get(project_id)
        tools.eq_(t['qt_load_balancers'], 2222)

    def test_limitation(self):
        fixtures.insert_project('project_id_a')
        fixtures.insert_project('project_id_b')

        page = project_model.limitation(reverse=True)

        tools.eq_(page['total'], 2)
        tools.ok_(page['items'][0]['id'] in ['project_id_a', 'project_id_b'])  # noqa


@patch('keystoneclient.v3.projects.ProjectManager.create', mock_create_project)
@patch('keystoneclient.v3.projects.ProjectManager.list', mock_nope)
@patch('keystoneclient.v3.projects.ProjectManager.update', mock_nope)
@patch('keystoneclient.v3.projects.ProjectManager.delete', mock_nope)
@patch('keystoneclient.v3.roles.RoleManager.find', mock_find_role)
@patch('keystoneclient.v3.roles.RoleManager.grant', mock_nope)
@patch('keystoneclient.v3.users.UserManager.list', mock_nope)
@patch('keystoneclient.v3.users.UserManager.find', mock_find_user)
@patch('neutronclient.v2_0.client.Client.update_quota', mock_op_quota)
@patches.check_manage()
class TestAPI:

    def setup(self):
        env.reset_db()
        fixtures.insert_project(project_id_1)

    def test_upsert_project(self):

        def send_request(project_id, qt_loadBalancers):
            result = fixtures.manage.post('/', data=json.dumps({
                'action': 'UpsertProject',
                'projectId': project_id,
                'quotaLoadBalancers': qt_loadBalancers,
            }))
            return result

        # insert
        send_request(project_id_1, 11)

        project = project_model.get(project_id_1)
        project['qt_loadBalancers'] = 11

        # update
        send_request(project_id_1, 22)

        project = project_model.get(project_id_1)
        project['qt_loadBalancers'] = 2222
