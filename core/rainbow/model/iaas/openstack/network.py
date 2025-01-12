from neutronclient.v2_0 import client as neutron_client
from rainbow.model.iaas.openstack import identify
from rainbow.model.iaas.openstack import cache_openstack_client

LOADBALANCER_STATUS_ACTIVE = 'ACTIVE'
LOADBALANCER_STATUS_PENDING_CREATE = 'PENDING_CREATE'
LOADBALANCER_STATUS_PENDING_UPDATE = 'PENDING_UPDATE'
LOADBALANCER_STATUS_PENDING_DELETE = 'PENDING_DELETE'
LOADBALANCER_STATUS_INACTIVE = 'INACTIVE'
LOADBALANCER_STATUS_ERROR = 'ERROR'


@cache_openstack_client('network')
def client():
    session = identify.client().session
    client = neutron_client.Client(session=session)
    client.lbaas_loadbalancers_path = "/lbaasv3/loadbalancers"
    client.lbaas_loadbalancer_path = "/lbaasv3/loadbalancers/%s"
    client.lbaas_loadbalancer_path_stats = "/lbaasv3/loadbalancers/%s/stats"
    client.lbaas_loadbalancer_path_status = \
        "/lbaasv3/loadbalancers/%s/statuses"
    client.lbaas_listeners_path = "/lbaasv3/listeners"
    client.lbaas_listener_path = "/lbaasv3/listeners/%s"
    client.lbaas_l7policies_path = "/lbaasv3/l7policies"
    client.lbaas_pools_path = "/lbaasv3/pools"
    client.lbaas_pool_path = "/lbaasv3/pools/%s"
    client.lbaas_healthmonitors_path = "/lbaasv3/healthmonitors"
    client.lbaas_healthmonitor_path = "/lbaasv3/healthmonitors/%s"
    client.lbaas_members_path = client.lbaas_pool_path + "/members"
    client.lbaas_member_path = client.lbaas_pool_path + "/members/%s"

    return client


def _extract_loadbalancer(lb):
    """
    {
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
            'vip_port_id': 'b83e9fc9-3a01-4623-927e-6e0dd8035501'}
    }
    """
    return {
        'id': lb['id'],
        'name': lb['name'],
        'vip_port_id': lb['vip_port_id'],
        'vip_address': lb['vip_address'],
        'tenant_id': lb['tenant_id'],
        'provisioning_status': lb['provisioning_status'],
        'operating_status': lb['operating_status'],
        'listeners': lb['listeners'],
        'admin_state_up': lb['admin_state_up'],
    }


def create_loadbalancer(project_id, subnet_id,
                        name, rate_limit):
    c = client()
    body_sample = {
        'loadbalancer': {
            'tenant_id': project_id,
            'tenant_subnet_id': subnet_id,
            'name': name,
            'rate_limit': rate_limit,
        }
    }
    lb = c.create_loadbalancer(body=body_sample)['loadbalancer']
    return _extract_loadbalancer(lb)


def get_loadbalancer(loadbalancer_id):
    c = client()
    lb = c.list_loadbalancers(id=loadbalancer_id)['loadbalancers'][0]
    return _extract_loadbalancer(lb)


def update_loadbalancer_rate_limit(loadbalancer_id, rate_limit):
    c = client()
    body_sample = {
        'loadbalancer': {
            'rate_limit': rate_limit
        }
    }
    c.update_loadbalancer(loadbalancer_id, body=body_sample)


def delete_loadbalancer(loadbalancer_id):
    c = client()
    c.delete_loadbalancer(loadbalancer_id)


def _extract_listener(l):
    """
    {'listener': {'admin_state_up': True,
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
      'tenant_id': '254686300d8f49438fb105b693034181'}}
    """
    return {
        'id': l['id'],
        'name': l['name'],
        'description': l['description'],
        'default_pool_id': l['default_pool_id'],
        'default_tls_container_ref': l['default_tls_container_ref'],
        'loadbalancers': l['loadbalancers'],
        'protocol': l['protocol'],
        'protocol_port': l['protocol_port'],
        'connection_limit': l['connection_limit'],
        'sni_container_refs': l['sni_container_refs'],
        'admin_state_up': l['admin_state_up'],
        'tenant_id': l['tenant_id'],
    }


def create_loadbalancer_listener(loadbalancer_id,
                                 name,
                                 protocol,
                                 port,
                                 connection_limit):
    c = client()
    body_sample = {
        'listener': {
            'admin_state_up': True,
            'loadbalancer_id': loadbalancer_id,
            'name': name,
            'protocol': protocol,
            'protocol_port': port,
            'connection_limit': connection_limit
        }
    }
    l = c.create_listener(body=body_sample)['listener']
    return _extract_listener(l)


def update_loadbalancer_listener(loadbalancer_listener_id,
                                 connection_limit):
    c = client()
    body_sample = {
        'listener': {
        }
    }
    if connection_limit is not None:
        body_sample['listener']['connection_limit'] = connection_limit
    if body_sample['listener']:
        c.update_listener(loadbalancer_listener_id,
                          body=body_sample)


def _extract_pool(p):
    """
    {'pool': {'admin_state_up': True,
      'description': '',
      'healthmonitor_id': None,
      'id': 'a5d74f07-0071-4095-a59c-a4dda2975f06',
      'lb_algorithm': 'ROUND_ROBIN',
      'listeners': [{'id': '94e2348e-91c4-45e5-b38c-9a321f13e464'}],
      'members': [],
      'name': 'p1',
      'protocol': 'TCP',
      'session_persistence': None,
      'tenant_id': '254686300d8f49438fb105b693034181'}}
    """
    return {
        'admin_state_up': True,
        'description': p['description'],
        'healthmonitor_id': p['healthmonitor_id'],
        'id': p['id'],
        'lb_algorithm': p['lb_algorithm'],
        'listeners': p['listeners'],
        'members': p['members'],
        'name': p['name'],
        'protocol': p['protocol'],
        'session_persistence': p['session_persistence'],
        'tenant_id': p['tenant_id']
    }


def create_loadbalancer_pool(loadbalancer_listener_id,
                             name,
                             protocol,
                             balance_mode,
                             session_persistence_mode,
                             session_persistence_timeout,
                             session_persistence_key):
    c = client()
    body_sample = {
        'pool': {
            'admin_state_up': True,
            'lb_algorithm': balance_mode,
            'listener_id': loadbalancer_listener_id,
            'name': name,
            'protocol': protocol
        }
    }
    if session_persistence_mode is not None:
        body_sample['pool']['session_persistence'] = \
            {'type': session_persistence_mode,
             'timeout': session_persistence_timeout,
             'cookie_name': session_persistence_key}

    p = c.create_lbaas_pool(body=body_sample)['pool']
    return _extract_pool(p)


def update_loadbalancer_pool(loadbalancer_pool_id,
                             balance_mode,
                             session_persistence_mode,
                             session_persistence_timeout,
                             session_persistence_key):
    c = client()
    body_sample = {
        'pool': {
        }
    }
    if balance_mode is not None:
        body_sample['pool']['lb_algorithm'] = balance_mode
    if session_persistence_mode is None:
        body_sample['pool']['session_persistence'] = None
    else:
        body_sample['pool']['session_persistence'] = \
            {'type': session_persistence_mode,
             'timeout': session_persistence_timeout,
             'cookie_name': session_persistence_key}

    if body_sample['pool']:
        c.update_lbaas_pool(loadbalancer_pool_id,
                            body=body_sample)


def _extract_healthmonitor(hm):
    """
    {'healthmonitor': {'admin_state_up': True,
      'delay': 10,
      'id': '81633c1c-d83d-480d-9709-466eaffe3cc5',
      'max_retries': 3,
      'name': '',
      'pools': [{'id': 'a5d74f07-0071-4095-a59c-a4dda2975f06'}],
      'tenant_id': '254686300d8f49438fb105b693034181',
      'timeout': 10,
      'type': 'TCP'}}
    """
    return {
        'admin_state_up': hm['admin_state_up'],
        'delay': hm['delay'],
        'id': hm['id'],
        'max_retries': hm['max_retries'],
        'name': hm['name'],
        'pools': hm['pools'],
        'tenant_id': hm['tenant_id'],
        'timeout': hm['timeout'],
        'type': hm['type']
    }


def create_loadbalancer_healthmonitor(loadbalancer_pool_id,
                                      name,
                                      delay,
                                      timeout,
                                      expected_codes,
                                      max_retries,
                                      http_method,
                                      url_path,
                                      type):
    c = client()
    body_sample = {
        'healthmonitor': {
            'admin_state_up': True,
            'delay': delay,
            'name': name,
            'max_retries': max_retries,
            'expected_codes': expected_codes,
            'pool_id': loadbalancer_pool_id,
            'timeout': timeout,
            'type': type
        }
    }

    if http_method is not None:
        body_sample['healthmonitor']['http_method'] = http_method
    if url_path is not None:
        body_sample['healthmonitor']['url_path'] = url_path

    p = c.create_lbaas_healthmonitor(body=body_sample)['healthmonitor']
    return _extract_healthmonitor(p)


def update_loadbalancer_healthmonitor(loadbalancer_healthmonitor_id,
                                      delay,
                                      timeout,
                                      expected_codes,
                                      max_retries,
                                      http_method,
                                      url_path):
    c = client()
    body_sample = {
        'healthmonitor': {
        }
    }
    if delay is not None:
        body_sample['healthmonitor']['delay'] = delay
    if timeout is not None:
        body_sample['healthmonitor']['timeout'] = timeout
    if max_retries is not None:
        body_sample['healthmonitor']['max_retries'] = max_retries
    if expected_codes is not None:
        body_sample['healthmonitor']['expected_codes'] = expected_codes
    if http_method is not None:
        body_sample['healthmonitor']['http_method'] = http_method
    if url_path is not None:
        body_sample['healthmonitor']['url_path'] = url_path
    if body_sample['healthmonitor']:
        c.update_lbaas_healthmonitor(loadbalancer_healthmonitor_id,
                                     body=body_sample)


def delete_loadbalancer_healthmonitor(healthmonitor_id):
    c = client()
    c.delete_lbaas_healthmonitor(healthmonitor_id)


def delete_loadbalancer_pool(pool_id):
    c = client()
    c.delete_lbaas_pool(pool_id)


def delete_loadbalancer_listener(listener_id):
    c = client()
    c.delete_listener(listener_id)


def _extract_member(m):
    """
    {'member': {'address': '10.0.0.3',
      'admin_state_up': True,
      'id': '8a6adc34-38c8-4e99-9ce3-6465500c8559',
      'name': 'b1',
      'protocol_port': 22,
      'subnet_id': 'be36f320-6a31-4aa5-96a3-baf082da6305',
      'tenant_id': '254686300d8f49438fb105b693034181',
      'weight': 1}}
    """
    return {
        'address': m['address'],
        'admin_state_up': m['admin_state_up'],
        'id': m['id'],
        'name': m['name'],
        'protocol_port': m['protocol_port'],
        'subnet_id': m['subnet_id'],
        'tenant_id': m['tenant_id'],
        'weight': m['weight']
    }


def create_loadbalancer_member(loadbalancer_pool_id,
                               subnet_id,
                               name,
                               address,
                               port,
                               weight=1):
    c = client()
    body_sample = {
        'member': {
            'admin_state_up': True,
            'subnet_id': subnet_id,
            'name': name,
            'protocol_port': port,
            'address': address,
            'weight': weight
        }
    }
    p = c.create_lbaas_member(loadbalancer_pool_id, body=body_sample)['member']
    return _extract_member(p)


def update_loadbalancer_member(loadbalancer_member_id,
                               loadbalancer_pool_id,
                               weight):
    c = client()
    body_sample = {
        'member': {
        }
    }
    if weight is not None:
        body_sample['member']['weight'] = weight
    if body_sample['member']:
        c.update_lbaas_member(loadbalancer_member_id,
                              loadbalancer_pool_id,
                              body=body_sample)


def delete_loadbalancer_member(loadbalancer_member_id,
                               loadbalancer_pool_id):
    c = client()
    c.delete_lbaas_member(loadbalancer_member_id, loadbalancer_pool_id)
