from densefog import web
from rainbow.api import guard
from rainbow.api import middleware

import monitor as monitor_api
import job as job_api
import project as project_api
import operation as operation_api
import load_balancer as load_balancer_api


def w(f):
    @web.stat_user_access
    @web.guard_generic_failure
    @web.guard_provider_failure
    @web.guard_resource_failure
    @web.guard_params_failure
    @guard.guard_explicit_code_failure
    @guard.guard_project_failure
    @guard.guard_access_failure
    @guard.guard_auth_failure
    @middleware.load_access_key
    @middleware.load_project
    def inner():
        return f()

    return inner


switch = {
    # jobs
    'DescribeJobs': w(job_api.describe_jobs),
    # projects
    'DescribeQuotas': w(project_api.describe_quotas),
    # networks
    'DescribeNetworks': w(project_api.describe_networks),
    # load balancer
    'DescribeLoadBalancers': w(load_balancer_api.describe_load_balancers),  # noqa
    'CreateLoadBalancer': w(load_balancer_api.create_load_balancer),  # noqa
    'DeleteLoadBalancers': w(load_balancer_api.delete_load_balancers),  # noqa
    'ModifyLoadBalancerAttributes': w(load_balancer_api.modify_load_balancer_attributes),  # noqa
    'UpdateLoadBalancerBandwidth': w(load_balancer_api.update_load_balancer_bandwidth),  # noqa
    'DescribeLoadBalancerListeners': w(load_balancer_api.describe_load_balancer_listeners),  # noqa
    'CreateLoadBalancerListener': w(load_balancer_api.create_load_balancer_listener),  # noqa
    'DeleteLoadBalancerListeners': w(load_balancer_api.delete_load_balancer_listeners),  # noqa
    'ModifyLoadBalancerListenerAttributes': w(load_balancer_api.modify_load_balancer_listener_attributes),  # noqa
    'UpdateLoadBalancerListener': w(load_balancer_api.update_load_balancer_listener),  # noqa
    'DescribeLoadBalancerBackends': w(load_balancer_api.describe_load_balancer_backends),  # noqa
    'CreateLoadBalancerBackend': w(load_balancer_api.create_load_balancer_backend),  # noqa
    'DeleteLoadBalancerBackends': w(load_balancer_api.delete_load_balancer_backends),  # noqa
    'ModifyLoadBalancerBackendAttributes': w(load_balancer_api.modify_load_balancer_backend_attributes),  # noqa
    'UpdateLoadBalancerBackend': w(load_balancer_api.update_load_balancer_backend),  # noqa
    # monitor
    'GetMonitor': w(monitor_api.get_monitor),
    # operation
    'DescribeOperations': w(operation_api.describe_operations),
}
