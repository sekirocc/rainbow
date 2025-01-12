# from densefog.common import utils

#################################################################
#
# raw objects returned directly from openstack components,
# such as compute, block, network, image.
#
#################################################################


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
