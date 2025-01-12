import flask
from mock import patch
import functools


def mock_load_project(project_id):
    from rainbow.model.project import project as project_model
    flask.request.project_id = project_id
    flask.request.project = project_model.get(project_id)


def mock_load_key():
    flask.request.key = 'ke7'
    flask.request.secret = 'sekret'


def check_access_key(project_id):
    return patch.multiple(
        'rainbow.api.middleware',
        _load_project=functools.partial(mock_load_project, project_id),    # noqa
        _load_access_key=mock_load_key)


def check_manage():
    return patch('rainbow.api.middleware._check_manage', lambda: True)
