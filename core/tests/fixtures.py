import json
import datetime
from rainbow.api.public import switch as public_switch
from rainbow.api.manage import switch as manage_switch
from densefog.server import create_api
from densefog.server import create_worker
from densefog.common import utils
from densefog.model.job import job as job_model
from rainbow.model.project import project as project_model
from densefog.model.journal import operation as operation_model
from rainbow.model.project import access_key as access_key_model
from rainbow.model.iaas import load_balancer as load_balancer_model
from rainbow.model.iaas import load_balancer_listener as load_balancer_listener_model  # noqa
from rainbow.model.iaas import load_balancer_backend as load_balancer_backend_model  # noqa


project_id_a = 't-123'
subnet_id_a = 'snt-123'
access_key_a = 'access-key-a'
access_secret_a = 'access-secret-a'
load_balancer_id_a = 'lb-123'
load_balancer_listener_id_a = 'lbl-123'
load_balancer_backend_id_a = 'lbb-123'

job_id_a = 'job_id-123'
action_a = 'Sync'
params_a = json.dumps({})


def mock_nope(*args, **kwargs):
    return None


def insert_access_key(project_id=project_id_a,
                      access_key=access_key_a,
                      access_secret=access_secret_a):
    access_key_id = access_key_model.AccessKey.insert(**{
        'project_id': project_id,
        'key': access_key,
        'secret': access_secret,
        'deleted': 0,
        'expire_at': datetime.datetime.utcnow() + datetime.timedelta(days=365),   # noqa
        'created': datetime.datetime.utcnow(),
        'updated': datetime.datetime.utcnow(),
    })
    return access_key_id


def insert_load_balancer(project_id=project_id_a,
                         load_balancer_id=load_balancer_id_a,
                         subnet_id=subnet_id_a,
                         status='active'):
    load_balancer_id = load_balancer_model.LoadBalancer.insert(**{
        'id': load_balancer_id,
        'project_id': project_id,
        'subnet_id': subnet_id,
        'name': 'lb-123',
        'description': '',
        'bandwidth': 1,
        'address': '58.96.178.234',
        'op_floatingip_id': utils.generate_uuid(),
        'op_loadbalancer_id': utils.generate_uuid(),
        'status': status,
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })

    return load_balancer_id


def insert_load_balancer_listener(
        project_id=project_id_a,
        load_balancer_id=load_balancer_id_a,
        load_balancer_listener_id=load_balancer_listener_id_a,
        status='active'):
    load_balancer_listener_id = load_balancer_listener_model.LoadBalancerListener.insert(**{  # noqa
        'id': load_balancer_listener_id,
        'project_id': project_id,
        'load_balancer_id': load_balancer_id,
        'name': 'lbl-123',
        'description': '',
        'protocol': 'tcp',
        'port': 22,
        'balance_mode': 'ROUND_ROBIN',
        'sp_mode': None,
        'sp_timeout': None,
        'sp_key': None,
        'hm_delay': None,
        'hm_timeout': None,
        'hm_expected_codes': None,
        'hm_max_retries': None,
        'hm_http_method': None,
        'hm_url_path': None,
        'hm_type': None,
        'op_listener_id': utils.generate_uuid(),
        'op_pool_id': utils.generate_uuid(),
        'op_healthmonitor_id': utils.generate_uuid(),
        'status': status,
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })

    return load_balancer_listener_id


def insert_load_balancer_backend(
        project_id=project_id_a,
        load_balancer_id=load_balancer_id_a,
        load_balancer_listener_id=load_balancer_listener_id_a,
        load_balancer_backend_id=load_balancer_backend_id_a,
        status='active'):
    load_balancer_backend_id = load_balancer_backend_model.LoadBalancerBackend.insert(**{  # noqa
        'id': load_balancer_backend_id,
        'project_id': project_id,
        'load_balancer_id': load_balancer_id,
        'load_balancer_listener_id': load_balancer_listener_id,
        'name': load_balancer_backend_id,
        'description': '',
        'address': '192.160.100.3',
        'port': 80,
        'weight': 1,
        'status': status,
        'op_member_id': utils.generate_uuid(),
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })

    return load_balancer_backend_id


def insert_project(project_id,
                   qt_load_balancers=2222):
    project_id = project_model.Project.insert(**{
        'id': project_id,
        'op_project_id': utils.generate_key(32),
        'qt_load_balancers': qt_load_balancers,
        'cu_load_balancers': 0,
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })
    return project_id


def insert_job(project_id=project_id_a,
               job_id=job_id_a,
               action=action_a,
               params=params_a,
               status=job_model.JOB_STATUS_PENDING):

    job_id = job_model.Job.insert(**{
        'id': job_id,
        'project_id': project_id,
        'action': action,
        'status': status,
        'error': '',
        'result': '',
        'params': json.dumps(params),
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
        'run_at': datetime.datetime.utcnow(),
        'try_period': 1,
        'try_max': 3,
        'trys': 0,
    })
    return job_id


def insert_operation(action='insert_operation',
                     project_id=project_id_a):

    operation_id = operation_model.Operation.insert(**{
        'id': 'opertn-' + utils.generate_key(10),
        'project_id': project_id,
        'action': action,
        'access_key': 'access_key',
        'params': json.dumps({}),
        'resource_type': 'instance',
        'resource_ids': json.dumps([]),
        'ret_code': 0,
        'ret_message': 'ret_message',
        'updated': datetime.datetime.utcnow(),
        'created': datetime.datetime.utcnow(),
    })
    return operation_id


public = create_api('public').route(
    public_switch).service.service.test_client()
manage = create_api('manage').route(
    manage_switch).service.service.test_client()
worker = create_worker(pick_size=10, exec_size=10, exec_timeout=600)

op_mock_subnet = {
    'subnet': {
        'allocation_pools': [{'end': '192.168.0.254', 'start': '192.168.0.2'}],
        'cidr': '192.168.0.0/24',
        'created_at': '2016-05-20T03:56:51',
        'description': '',
        'dns_nameservers': [],
        'enable_dhcp': True,
        'gatewayIp': '192.168.0.1',
        'host_routes': [],
        'opSubnetId': utils.generate_uuid(),
        'ip_version': 4,
        'ipv6_address_mode': None,
        'ipv6_ra_mode': None,
        'name': 'rainbow-Hh5fCxev7F2nHXfVBPASV8',
        'network_id': utils.generate_uuid(),
        'subnetpool_id': None,
        'tenant_id': 't-s8DwDp34PR',
        'updated_at': '2016-05-20T03:56:51'
    }
}

op_mock_create_loadbalancer = {
    'loadbalancer': {
        'admin_state_up': True,
        'description': '',
        'id': '56f0937b-ccbd-4a99-b02b-1e37b409ba03',
        'listeners': [{'id': 'ac966af2-3d12-4697-889c-5b70027a8e51'}],
        'name': 'test_b',
        'operating_status': 'ONLINE',
        'provider': 'lvs',
        'provisioning_status': 'ACTIVE',
        'tenant_id': '254686300d8f49438fb105b693034181',
        'vip_address': '192.168.1.12',
        'vip_port_id': 'b83e9fc9-3a01-4623-927e-6e0dd8035501'
    }
}

op_mock_create_loadbalancer_member = {
    'member': {
        'address': '10.0.0.3',
        'admin_state_up': True,
        'id': '8a6adc34-38c8-4e99-9ce3-6465500c8559',
        'name': 'b1',
        'protocol_port': 22,
        'subnet_id': 'be36f320-6a31-4aa5-96a3-baf082da6305',
        'tenant_id': '254686300d8f49438fb105b693034181',
        'weight': 1
    }
}

op_mock_create_loadbalancer_listener = {
    'listener': {
        'admin_state_up': True,
        'connection_limit': -1,
        'default_pool_id': None,
        'default_tls_container_ref': None,
        'description': '',
        'id': '94e2348e-91c4-45e5-b38c-9a321f13e464',
        'loadbalancers': [{'id': 'ce162f4d-89da-471c-91bd-136146097dcb'}],
        'name': 'l1',
        'protocol': 'TCP',
        'protocol_port': 80,
        'sni_container_refs': [],
        'tenant_id': '254686300d8f49438fb105b693034181'
    }
}

op_mock_create_loadbalancer_pool = {
    'pool': {
        'admin_state_up': True,
        'description': '',
        'healthmonitor_id': None,
        'id': 'a5d74f07-0071-4095-a59c-a4dda2975f06',
        'lb_algorithm': 'ROUND_ROBIN',
        'listeners': [{'id': '94e2348e-91c4-45e5-b38c-9a321f13e464'}],
        'members': [],
        'name': 'p1',
        'protocol': 'TCP',
        'session_persistence': None,
        'tenant_id': '254686300d8f49438fb105b693034181'
    }
}

op_mock_create_loadbalancer_healthmonitor = {
    'healthmonitor': {
        'admin_state_up': True,
        'delay': 10,
        'id': '81633c1c-d83d-480d-9709-466eaffe3cc5',
        'max_retries': 3,
        'name': '',
        'pools': [{'id': 'a5d74f07-0071-4095-a59c-a4dda2975f06'}],
        'tenant_id': '254686300d8f49438fb105b693034181',
        'timeout': 10,
        'type': 'TCP'
    }
}

op_mock_project = {
    'enabled': True,
    'description': 'a demo project',
    'name': 'rainbow-demo-project',
}

op_mock_role = {
    'domain_id': None,
    'name': 'admin',
    'id': '1ddfe1a8e2ca47e2bbd0d080a7fb037f'
}

op_mock_user = {
    'username': 'admin',
    'enabled': True,
    'name': 'admin',
    'id': 'c71ec5303b174121a96f4a90404a5e9b'
}

op_mock_update_quota = {
    'quota': {
        'load_balancers': 100
    }
}

op_mock_get_monitor = []
