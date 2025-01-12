import traceback
from rainbow.model.job import error as job_error
from densefog import logger
logger = logger.getChild(__file__)


def _sync_resources(resource_model, resources, time_sleep):
    """
    sync resource status from iaas provider
    """
    exceptions = []
    while True:
        busy_resources = []
        for resource_id in resources:
            logger.info('resource_model.sync(%s) start' % resource_id)
            try:
                resource = resource_model.sync(resource_id)
            except Exception as ex:
                logger.error('resource_model.sync(%s) ERROR!' % resource_id)
                exceptions.append({
                    'exception': ex,
                    'resource': resource_id
                })

            else:
                if resource.is_busy():
                    logger.info('resource is still busy, '
                                'put back for next loop')
                    busy_resources.append(resource_id)
                else:
                    logger.info('resource_model.sync(%s) OK.' % resource_id)

        if busy_resources:
            resources = busy_resources
            time_sleep(2)
        else:
            break

    if exceptions:
        raise job_error.SyncResourceException(exceptions)


def _erase_resources(resource_model, resources, time_sleep):
    """
    erase resource from iaas provider
    """
    exceptions = []
    for resource_id in resources:
        logger.info('resource_model.erase(%s) start' % resource_id)
        try:
            resource_model.erase(resource_id)
        except Exception as ex:
            logger.error('resource_model.erase(%s) ERROR!' % resource_id)
            exceptions.append({
                'exception': ex,
                'resource': resource_id
            })

        else:
            logger.info('resource_model.erase(%s) OK.' % resource_id)

    if exceptions:
        raise job_error.EraseResourceException(exceptions)
    else:
        time_sleep(2)


def sync(params, time_sleep, is_last_chance):
    pass


def create_load_balancer(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer as lb_model
    lb_ids = params['resource_ids']
    _sync_resources(lb_model, lb_ids, time_sleep)


def erase_load_balancers(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer as lb_model
    lb_ids = params['resource_ids']
    _erase_resources(lb_model, lb_ids, time_sleep)


def create_load_balancer_backend(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer as lb_model
    lb_ids = params['resource_ids']
    _sync_resources(lb_model, lb_ids, time_sleep)


def update_load_balancer_backend(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer as lb_model
    lb_ids = params['resource_ids']
    _sync_resources(lb_model, lb_ids, time_sleep)


def erase_load_balancer_backend(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer as lb_model
    lb_ids = params['resource_ids']
    _sync_resources(lb_model, lb_ids, time_sleep)


def erase_load_balancer_backends(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer_backend as lbb_model
    lbb_ids = params['resource_ids']
    exceptions = []
    try_time = 0
    while True:
        try_time += 1
        for i in xrange(len(lbb_ids) - 1, -1, -1):
            logger.info('lbb_model.erase(%s) start' % lbb_ids[i])
            try:
                continue_erase = False
                is_last = False
                if len(lbb_ids) is 1:
                    is_last = True
                continue_erase = lbb_model.erase(lbb_ids[i], is_last, try_time)
            except Exception as ex:
                logger.error('lbb_model.erase(%s) ERROR!' % lbb_ids[i])
                stack = traceback.format_exc()
                # TODO send email. job execution error!

                exceptions.append({
                    'exception': ex,
                    'stacktrace': stack,
                    'resource': lbb_ids[i]
                })
                time_sleep(2)
            else:
                if continue_erase:
                    logger.info('lbb_model.erase(%s) OK.' % lbb_ids[i])
                    lbb_ids.remove(lbb_ids[i])
                else:
                    time_sleep(2)

        if try_time == 3:
            if exceptions:
                raise job_error.EraseResourceException(exceptions)
            else:
                break
        if len(lbb_ids) == 0:
            break


def _sync_loadbalancer_resource(resource_model, resource_id,
                                sub_resource_id, time_sleep):
    """
    sync resource status from iaas provider
    """
    while True:
        logger.info('resource_model.sync(%s) start' % resource_id)
        try:
            resource = resource_model.sync(resource_id, sub_resource_id)
        except Exception as ex:
            logger.error('resource_model.sync(%s) ERROR!' % resource_id)
            exception = {
                'exception': ex,
                'resource': resource_id
            }
            raise job_error.SyncResourceException([exception])
        else:
            if resource.is_busy():
                logger.info('resource is still busy.')
                time_sleep(3)
            else:
                logger.info('resource_model.sync(%s) OK.' % resource_id)
                break


def create_load_balancer_front_end(params, time_sleep, is_last_chance):
    """
    sync resource status from iaas provider
    """
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lb_id = params['load_balancer_id']
    lbl_id = params['load_balancer_listener_id']
    continue_sync = False

    while True:
        logger.info('lbl_model.sync_create_loadbalancer_front_end(%s) start' %
                    lb_id)
        try:
            continue_sync = lbl_model.sync_create_loadbalancer_listener(params)
        except Exception as ex:
            logger.error('lbl_model.sync_create_loadbalancer_front_end(%s) \
                         ERROR!' % lb_id)
            stack = traceback.format_exc()
            # TODO send email. job execution error!
            exception = {
                'exception': ex,
                'stacktrace': stack,
                'resource': lb_id
            }
            raise job_error.SyncResourceException([exception])
        else:
            if continue_sync:
                logger.info('lbl_model.sync_create_loadbalancer_front_end(%s) \
                            OK.' % lb_id)
                break
            else:
                logger.info('resource is still busy, '
                            'put back for next loop')
                time_sleep(2)

    _sync_loadbalancer_resource(lbl_model, lb_id, lbl_id, time_sleep)


def update_load_balancer_front_end(params, time_sleep, is_last_chance):
    """
    sync resource status from iaas provider
    """
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lb_id = params['load_balancer_id']
    lbl_id = params['load_balancer_listener_id']
    continue_sync = False

    while True:
        logger.info('lbl_model.sync_update_load_balancer_front_end start')
        try:
            continue_sync = lbl_model.sync_update_loadbalancer_listener(params)
        except Exception as ex:
            logger.error('lbl_model.sync_update_load_balancer_front_end \
                         ERROR!')
            stack = traceback.format_exc()
            # TODO send email. job execution error!
            exception = {
                'exception': ex,
                'stacktrace': stack,
                'resource': lb_id
            }
            raise job_error.SyncResourceException([exception])
        else:
            if continue_sync:
                logger.info('lbl_model.sync_update_load_balancer_front_end \
                            OK.')
                break
            else:
                logger.info('resource is still busy, '
                            'put back for next loop')
                time_sleep(2)

    _sync_loadbalancer_resource(lbl_model, lb_id, lbl_id, time_sleep)


def erase_load_balancer_front_end(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lbl_ids = params['resource_ids']
    exceptions = []
    try_time = 0
    lbl_ids_finish = []
    num_lbl = len(lbl_ids)
    while True:
        try_time += 1
        for i in xrange(num_lbl - 1, -1, -1):
            logger.info('lbl_model.erase(%s) start' % lbl_ids[i])
            try:
                continue_erase = False
                if len(lbl_ids_finish) + 1 == num_lbl or try_time == 3:
                    continue_erase = lbl_model.erase_load_balancer_listener(
                        lbl_ids[i], try_time, lbl_ids_finish)
                else:
                    continue_erase = lbl_model.erase_load_balancer_listener(
                        lbl_ids[i], try_time)
            except Exception as ex:
                logger.error('lbl_model.erase(%s) ERROR!' % lbl_ids[i])
                stack = traceback.format_exc()
                # TODO send email. job execution error!

                exceptions.append({
                    'exception': ex,
                    'stacktrace': stack,
                    'resource': lbl_ids[i]
                })
                time_sleep(2)
            else:
                if continue_erase:
                    logger.info('lbl_model.erase(%s) OK.' % lbl_ids[i])
                    lbl_ids_finish.append(lbl_ids[i])
                    lbl_ids.remove(lbl_ids[i])
                else:
                    time_sleep(2)

        if try_time == 3:
            if exceptions:
                raise job_error.EraseResourceException(exceptions)
            else:
                break
        if len(lbl_ids) == 0:
            break


def create_load_balancer_listener(params, time_sleep, is_last_chance):
    """
    sync resource status from iaas provider
    """
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lbl_id = params['load_balancer_listener_id']
    continue_sync = False

    while True:
        logger.info('lbl_model.sync_create_loadbalancer_listener(%s) start' %
                    lbl_id)
        try:
            continue_sync = lbl_model.sync_create_loadbalancer_pool(params)
        except Exception as ex:
            logger.error('lbl_model.sync_create_loadbalancer_listener(%s) \
                         ERROR!' % lbl_id)
            stack = traceback.format_exc()
            # TODO send email. job execution error!
            exception = {
                'exception': ex,
                'stacktrace': stack,
                'resource': lbl_id
            }
            raise job_error.SyncResourceException([exception])
        else:
            if continue_sync:
                logger.info('lbl_model.sync_create_loadbalancer_listener(%s) \
                            OK.' % lbl_id)
                break
            else:
                logger.info('resource is still busy, '
                            'put back for next loop')
                time_sleep(2)


def update_load_balancer_listener(params, time_sleep, is_last_chance):
    """
    sync resource status from iaas provider
    """
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lbl_id = params['load_balancer_listener_id']
    continue_sync = False

    while True:
        logger.info('lbl_model.sync_update_loadbalancer_listener(%s) start' %
                    lbl_id)
        try:
            continue_sync = lbl_model.sync_update_loadbalancer_pool(params)
        except Exception as ex:
            logger.error('lbl_model.sync_update_loadbalancer_listener(%s) \
                         ERROR!' % lbl_id)
            stack = traceback.format_exc()
            # TODO send email. job execution error!
            exception = {
                'exception': ex,
                'stacktrace': stack,
                'resource': lbl_id
            }
            raise job_error.SyncResourceException([exception])
        else:
            if continue_sync:
                logger.info('lbl_model.sync_update_loadbalancer_listener(%s) \
                            OK.' % lbl_id)
                break
            else:
                logger.info('resource is still busy, '
                            'put back for next loop')
                time_sleep(2)


def erase_load_balancer_listener(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lbl_ids = params['resource_ids']
    exceptions = []
    try_time = 0
    lbl_ids_finish = []
    num_lbl = len(lbl_ids)
    while True:
        try_time += 1
        for i in xrange(num_lbl - 1, -1, -1):
            logger.info('lbl_model.erase(%s) start' % lbl_ids[i])
            try:
                continue_erase = False
                if len(lbl_ids_finish) + 1 == num_lbl or try_time == 3:
                    continue_erase = lbl_model.erase_load_balancer_pool(
                        lbl_ids[i], try_time, lbl_ids_finish)
                else:
                    continue_erase = lbl_model.erase_load_balancer_pool(
                        lbl_ids[i], try_time)
            except Exception as ex:
                logger.error('lbl_model.erase(%s) ERROR!' % lbl_ids[i])
                stack = traceback.format_exc()
                # TODO send email. job execution error!

                exceptions.append({
                    'exception': ex,
                    'stacktrace': stack,
                    'resource': lbl_ids[i]
                })
                time_sleep(2)
            else:
                if continue_erase:
                    logger.info('lbl_model.erase(%s) OK.' % lbl_ids[i])
                    lbl_ids_finish.append(lbl_ids[i])
                    lbl_ids.remove(lbl_ids[i])
                else:
                    time_sleep(2)

        if try_time == 3:
            if exceptions:
                raise job_error.EraseResourceException(exceptions)
            else:
                break
        if len(lbl_ids) == 0:
            break


def delete_load_balancer_listener(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    op_lbl_id = params['op_listener_id']
    continue_erase = False
    exceptions = []
    logger.info('lbl_model.delete openstack listener(%s) start' %
                op_lbl_id)
    try:
        continue_erase = lbl_model.delete_load_balancer_listener(params)
    except Exception as ex:
        stack = traceback.format_exc()
        logger.error('lbl_model.delete openstack listener(%s)!' %
                     op_lbl_id)
        # TODO send email. job execution error!
        exceptions.append({
            'exception': ex,
            'stacktrace': stack,
            'resource': op_lbl_id
        })
    else:
        if continue_erase:
            logger.info('lbl_model.delete openstack listener(%s) OK.' %
                        op_lbl_id)
    if exceptions:
        raise job_error.EraseResourceException(exceptions)


def create_load_balancer_pool(params, time_sleep, is_last_chance):
    """
    sync resource status from iaas provider
    """
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lbl_id = params['load_balancer_listener_id']
    continue_sync = False

    while True:
        logger.info('lbl_model.sync_create_loadbalancer_pool for \
                    listener(%s) start' % lbl_id)
        try:
            continue_sync = lbl_model.sync_create_loadbalancer_healthmonitor(
                params)
        except Exception as ex:
            logger.error('lbl_model.sync_create_loadbalancer_pool for \
                         listener(%s) ERROR!' % lbl_id)
            stack = traceback.format_exc()
            # TODO send email. job execution error!
            exception = {
                'exception': ex,
                'stacktrace': stack,
                'resource': lbl_id
            }
            raise job_error.SyncResourceException([exception])
        else:
            if continue_sync:
                logger.info('lbl_model.sync_create_loadbalancer_pool for \
                            listener(%s) OK.' % lbl_id)
                break
            else:
                logger.info('resource is still busy, '
                            'put back for next loop')
                time_sleep(2)


def update_load_balancer_pool(params, time_sleep, is_last_chance):
    """
    sync resource status from iaas provider
    """
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lbl_id = params['load_balancer_listener_id']
    continue_sync = False

    while True:
        logger.info('lbl_model.sync_update_loadbalancer_pool for \
                    listener(%s) start' % lbl_id)
        try:
            continue_sync = lbl_model.sync_update_loadbalancer_healthmonitor(
                params)
        except Exception as ex:
            logger.error('lbl_model.sync_update_loadbalancer_pool for \
                         listener(%s) ERROR!' % lbl_id)
            stack = traceback.format_exc()
            # TODO send email. job execution error!
            exception = {
                'exception': ex,
                'stacktrace': stack,
                'resource': lbl_id
            }
            raise job_error.SyncResourceException([exception])
        else:
            if continue_sync:
                logger.info('lbl_model.sync_update_loadbalancer_pool for \
                            listener(%s) OK.' % lbl_id)
                break
            else:
                logger.info('resource is still busy, '
                            'put back for next loop')
                time_sleep(2)


def erase_load_balancer_pool(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    lbl_ids = params['resource_ids']
    exceptions = []
    try_time = 0
    lbl_ids_finish = []
    num_lbl = len(lbl_ids)
    while True:
        try_time += 1
        for i in xrange(num_lbl - 1, -1, -1):
            logger.info('lbl_model.erase(%s) start' % lbl_ids[i])
            try:
                continue_erase = False
                if len(lbl_ids_finish) + 1 == num_lbl or try_time == 3:
                    continue_erase = lbl_model.\
                        erase_load_balancer_healthmonitor(lbl_ids[i],
                                                          try_time,
                                                          lbl_ids_finish)
                else:
                    continue_erase = lbl_model.\
                        erase_load_balancer_healthmonitor(lbl_ids[i], try_time)
            except Exception as ex:
                logger.error('lbl_model.erase(%s) ERROR!' % lbl_ids[i])
                stack = traceback.format_exc()
                # TODO send email. job execution error!

                exceptions.append({
                    'exception': ex,
                    'stacktrace': stack,
                    'resource': lbl_ids[i]
                })
                time_sleep(2)
            else:
                if continue_erase:
                    logger.info('lbl_model.erase(%s) OK.' % lbl_ids[i])
                    lbl_ids_finish.append(lbl_ids[i])
                    lbl_ids.remove(lbl_ids[i])
                else:
                    time_sleep(2)

        if try_time == 3:
            if exceptions:
                raise job_error.EraseResourceException(exceptions)
            else:
                break
        if len(lbl_ids) == 0:
            break


def delete_load_balancer_pool(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer_listener as lbl_model
    op_lbl_id = params['op_pool_id']
    continue_erase = False
    exceptions = []
    logger.info('lbl_model.delete openstack pool (%s) start' % op_lbl_id)
    try:
        continue_erase = lbl_model.delete_load_balancer_pool(params)
    except Exception as ex:
        logger.error('lbl_model.delete openstack pool (%s) ERROR!' %
                     op_lbl_id)
        stack = traceback.format_exc()
        # TODO send email. job execution error!
        exceptions.append({
            'exception': ex,
            'stacktrace': stack,
            'resource': op_lbl_id
        })
    else:
        if continue_erase:
            logger.info('lbl_model.delete openstack pool (%s) OK.' %
                        op_lbl_id)
    if exceptions:
        raise job_error.EraseResourceException(exceptions)


def erase_load_balancer_healthmonitor(params, time_sleep, is_last_chance):
    from rainbow.model.iaas import load_balancer as lb_model
    lb_id = params['resource_ids'][0]
    _sync_resources(lb_model, [lb_id], time_sleep)


def watching_jobs(params, time_sleep, is_last_chance):
    """Wathcing some jobs.
    watching untill all of them finished or errored.

    """
    from densefog.model.job import job as job_model

    error_jobs = []
    resources = params['job_ids']
    while True:
        busy_jobs = []
        for job_id in resources:
            job = job_model.get(job_id)

            logger.info('watching job (%s) start' % job_id)
            if job.is_finished():
                logger.info('watched job(%s) is finished, OK.' % job_id)
            elif job.is_error():
                logger.info('watched job(%s) is failed, OK.' % job_id)
                error_jobs.append(job)
            else:
                logger.debug('watched job(%s) is still busy, keep watch' % job_id)  # noqa
                busy_jobs.append(job_id)

        if busy_jobs:
            resources = busy_jobs
            time_sleep(2)
        else:
            break

    if error_jobs:
        raise job_error.WatchedJobsFailedException(error_jobs)
