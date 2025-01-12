import env  # noqa
import patches
import fixtures
import json
from mock import patch
from nose import tools
# from densefog.common import utils


project_id_1 = 'prjct-1234'


def mock_list(*args, **kwargs):
    return fixtures.op_mock_get_monitor


def mock_nope(*args, **kwargs):
    return None


@patch('ceilometerclient.v2.statistics.StatisticsManager.list', mock_list)
@patches.check_access_key(project_id_1)
class TestAPI:

    def setup(self):
        env.reset_db()
        fixtures.insert_project(project_id_1)

    @patch('keystoneclient.adapter.Adapter.get', mock_nope)
    @patch('rainbow.model.lcs.client.call', mock_nope)
    @patch('rainbow.model.lcs.client.get_subnet', fixtures.op_mock_subnet['subnet'])  # noqa
    @patch('rainbow.model.lcs.client.count_active_floatingip', 1)
    def test_get_monitor(self):
        load_balancer_id = fixtures.insert_load_balancer()

        metrics = [
        ]

        for period in [
            '120mins',
            '720mins',
            '48hours',
            '14days',
            '30days',
        ]:
            result = fixtures.public.post('/', data=json.dumps({
                'action': 'GetMonitor',
                'resourceIds': [load_balancer_id],
                'metrics': metrics,
                'period': period,
            }))
            tools.eq_(200, result.status_code)
            tools.eq_(0, json.loads(result.data)['retCode'])
            tools.eq_(
                len(metrics),
                len(json.loads(result.data)['data']['monitorSet']))
            # tools.eq_(
            #     load_balancer_id,
            #     json.loads(result.data)['data']['monitorSet'][0]['resourceId'])
