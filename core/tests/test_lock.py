# import json
import time
# import gevent
# from gevent import monkey
import threading
# from copy import copy
import env  # noqa
# from mock import patch
from nose import tools
# from densefog.common import utils
# from densefog.common.utils import MockObject
from rainbow.model.project import project as project_model
from densefog.model import base

import fixtures

project_id_1 = 'prjct-1234'


class TestModel:

    def setup(self):
        env.reset_db()
        fixtures.insert_project(project_id_1)

    def test_row_lock(self):
        fixtures.insert_project('proj-aaa')
        fixtures.insert_project('proj-bbb')

        @base.transaction
        def update_project(project_id):
            with base.lock_for_update():
                project = project_model.get(project_id)

            project_model.Project.update(project['id'], qt_load_balancers=2)

            time.sleep(3)

        t1 = time.time()
        p1 = threading.Thread(target=update_project, args=('proj-aaa', ))
        p1.start()

        p2 = threading.Thread(target=update_project, args=('proj-bbb', ))
        p2.start()

        p1.join()
        p2.join()

        t2 = time.time()
        # if is table lock, then at least 6 seconds.
        # if is row lock, then at most 4 seconds to finish.
        tools.assert_less_equal(int(t2 - t1), 4)
