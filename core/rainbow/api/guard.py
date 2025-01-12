import traceback
import functools

from densefog.web import feb
from densefog.model.job import job as job_model

from rainbow import config
from rainbow.model.iaas import error as iaas_error
from rainbow.model.project import error as project_error
from rainbow.model.lcs import error as lcs_error

from densefog import logger
logger = logger.getChild(__file__)


def guard_explicit_code_failure(method):
    """
    response an error when catch ExplicitCodeException, which we want user
    notice its error code, and response data have more accurate infomation
    for user to notice.
    """
    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)

        except iaas_error.CreateLoadBalancerListenerWhenPortInUse as ex:
            stack = traceback.format_exc()
            logger.trace(stack)
            data = {
                'port': ex.port,
            }
            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(ex.message, 4772, data=data)

        except iaas_error.CreateLoadBalancerListenerOverLimit as ex:
            stack = traceback.format_exc()
            logger.trace(stack)
            data = {
                'num': ex.num,
            }
            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(ex.message, 4773, data=data)

        except iaas_error.LoadBalancerBackendOverLimit as ex:
            stack = traceback.format_exc()
            logger.trace(stack)
            data = {
                'num': ex.num,
            }
            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(ex.message, 4774, data=data)

    return guard


def guard_partial_success(resource_key):
    """
    catch every ActionsPartialSuccessErrors throwed by model apis.
    actually they are throwed by model apis.

    model api want to do action on multiple resources at once,
    some maybe successfully done, while others maybe failed.
    so model apis throw one ActionsPartialSuccessError to represent
    this kind of situation.

    in the ActionsPartialSuccessError, there are three properties
        exceptions:
            array of failed action's causing exception.
            normally these exceptions are caused by openstack provider.
        results:
            if action is sync action, which can get results instantly,
            then store their results here.
        job_id:
            if action is async action, which cannot get results now, then
            there must be a job holding these actions. this is the job's id


    """
    def outer(method):
        @functools.wraps(method)
        def guard(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except iaas_error.ActionsPartialSuccessError as e:
                logger.trace(e)

                data = {}
                if config.CONF.debug:
                    data = {'exceptionStr': str(e)}

                job_id = e.job_id
                results = e.results

                if not job_id and not results:
                    # no success cases.
                    if len(e.exceptions) == 1:
                        raise feb.HandleError('Action failed.', 5001, data=data)  # noqa
                    else:
                        raise feb.HandleError('Actions all failed.', 5001, data=data)  # noqa
                elif job_id:
                    # some job cases success.
                    data['jobId'] = job_id
                    data[resource_key] = job_model.get_resources(job_id)
                    raise feb.HandleError('Actions partial success', 5002, data=data)  # noqa
                else:
                    # some result cases success.
                    data[resource_key] = results
                    raise feb.HandleError('Actions partial success', 5002, data=data)  # noqa

        return guard

    return outer


def guard_project_quota(method):
    """
    response an error when user's quota is not enough
    """
    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except project_error.ResourceQuotaNotEnough as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {'quota': e.quota, 'used': e.used, 'want': e.want}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4113, data=data)

    return guard


def guard_project_failure(method):
    """
    response an error when project model related exceptions.
    """
    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)

        except project_error.ProjectDuplicated as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {'projectId': e.project_id}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4600, data=data)

        except project_error.ProjectNotFound as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {'projectId': e.project_id}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4604, data=data)

    return guard


def guard_auth_failure(method):
    """
    response an error when authenticate error
    """
    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)

        except project_error.AccessKeyExpired as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {'accessKey': e.key}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4101, data=data)

        except project_error.AccessKeyInvalid as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {'accessKey': e.key}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4101, data=data)

        except project_error.ManageAccessKeyInvalid as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {'accessKey': e.key}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4601, data=data)

    return guard


def guard_access_failure(method):
    """
    response an error when access error
    """
    @functools.wraps(method)
    def guard(*args, **kwargs):
        try:
            return method(*args, **kwargs)

        except project_error.AccessKeyNotFound as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {'accessKey': e.key}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4614, data=data)

        except project_error.AccessKeyDuplicated as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {'accessKey': e.key}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4611, data=data)

        except lcs_error.ClientHttpError as e:
            stack = traceback.format_exc()
            logger.trace(stack)

            data = {}

            if config.CONF.debug:
                data['exceptionStr'] = stack

            raise feb.HandleError(str(e), 4604, data=data)

    return guard
