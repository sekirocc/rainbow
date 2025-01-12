from densefog import web
from rainbow.api import middleware
from rainbow.api import guard

import project as project_api


def w(f):
    @web.stat_user_access
    @web.guard_generic_failure
    @web.guard_provider_failure
    @web.guard_resource_failure
    @web.guard_params_failure
    @guard.guard_project_failure
    @guard.guard_access_failure
    @guard.guard_auth_failure
    @middleware.load_access_key
    @middleware.check_manage
    def inner():
        return f()

    return inner


switch = {
    # project quota
    'UpsertQuotas': w(project_api.upsert_quota),
    # access_key
    'CreateAccessKeys': w(project_api.create_access_keys),
    'DeleteAccessKeys': w(project_api.delete_access_keys),
}
