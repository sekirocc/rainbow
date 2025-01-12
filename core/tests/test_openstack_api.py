import env  # noqa
# import copy
# from mock import patch
# from nose import tools
# from densefog.common.utils import MockObject
# from rainbow.model.iaas import error as iaas_error
# from rainbow.model.iaas.openstack import api as op_api

# import fixtures
# import fixtures_openstack as op_fixtures

project_id_1 = 'projct-1234'
op_project_id = 'dcad0a17bcb34f969aaf9acba243b4e1'
exc = Exception('HTTP Connection Error')


def mock_nope(*args, **kwargs):
    return None


class TestAPI:
    def setup(self):
        env.reset_db()
