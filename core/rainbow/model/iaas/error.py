from densefog.error import BaseIaasException
from densefog.error import ResourceNotFound
from densefog.error import ResourceActionForbiden
from densefog.error import InvalidRequestParameter
from densefog.error import IaasProviderActionError


##################################################################
#
#  Not Found Exception Family
#
##################################################################

class SubnetNotFound(ResourceNotFound):
    def __init__(self, resource_id):
        ResourceNotFound.__init__(self, resource_id)
        self.message = 'Subnet (%s) is not found' % resource_id


class MonitorNotFound(ResourceNotFound):
    def __init__(self, resource_id):
        ResourceNotFound.__init__(self, resource_id)
        self.message = 'Monitor (%s) is not found' % resource_id


class LoadBalancerNotFound(ResourceNotFound):
    def __init__(self, resource_id):
        ResourceNotFound.__init__(self, resource_id)
        self.message = 'Load Balancer (%s) is not found' % resource_id


class LoadBalancerListenerNotFound(ResourceNotFound):
    def __init__(self, resource_id):
        ResourceNotFound.__init__(self, resource_id)
        self.message = 'Load Balancer Listener (%s) is not found' % resource_id


class LoadBalancerBackendNotFound(ResourceNotFound):
    def __init__(self, resource_id):
        ResourceNotFound.__init__(self, resource_id)
        self.message = 'Load Balancer Backend (%s) is not found' % resource_id


##################################################################
#
#  Action Forbiden Exception Family
#
##################################################################


class LoadBalancerCanNotDelete(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not delete load balancer (%s), '
                        'please check status') % resource_id


class LoadBalancerCanNotUpdate(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not update load balancer (%s), '
                        'please check status') % resource_id


class LoadBalancerInUse(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not delete load balancer (%s), '
                        'because its listener in use') % resource_id


class LoadBalancerListenerCanNotCreate(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not create load balancer listener (%s), '
                        'please check load balancer status') % resource_id


class LoadBalancerListenerCanNotUpdate(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not update load balancer listener (%s), '
                        'please check load balancer listener status') % \
            resource_id


class LoadBalancerListenerCanNotDelete(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not delete load balancer listener (%s), '
                        'please check status') % resource_id


class LoadBalancerListenerInUse(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not delete load balancer listener (%s), '
                        'because its backend in use') % resource_id


class LoadBalancerBackendCanNotCreate(ResourceActionForbiden):
    def __init__(self, resource_id=None):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not create load balancer backend, '
                        'please check loadbalancer or listener status')


class LoadBalancerBackendCanNotUpdate(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not update load balancer backend (%s), '
                        'please check status') % resource_id


class LoadBalancerBackendCanNotDelete(ResourceActionForbiden):
    def __init__(self, resource_id):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not delete load balancer backend (%s), '
                        'please check status') % resource_id


class LoadBalancerBackendInUse(ResourceActionForbiden):
    def __init__(self, resource_id=None):
        ResourceActionForbiden.__init__(self, resource_id)
        self.message = ('Can not create load balancer backend, '
                        'because address and port have already been used')


##################################################################
#
#  Provider Error Family
#
##################################################################

class ProviderUpdateFloatingipError(IaasProviderActionError):
    pass


class ProviderCreateProjectError(IaasProviderActionError):
    pass


class ProviderAddUserRoleError(IaasProviderActionError):
    pass


class ProviderCreateLoadBalancerError(IaasProviderActionError):
    pass


class ProviderCreateLoadBalancerListenerError(IaasProviderActionError):
    pass


class ProviderUpdateLoadBalancerListenerError(IaasProviderActionError):
    pass


class ProviderUpdateLoadBalancerBackendError(IaasProviderActionError):
    pass


class ProviderCreateLoadBalancerBackendError(IaasProviderActionError):
    pass


class ProviderDeleteLoadBalancerError(IaasProviderActionError):
    pass


class ProviderDeleteLoadBalancerListenerError(IaasProviderActionError):
    pass


class ProviderDeleteLoadBalancerBackendError(IaasProviderActionError):
    pass


class ProviderStatisticsError(IaasProviderActionError):
    pass


##################################################################
#
#  Request Parameter Invalid Error Family
#
##################################################################

class SessionPersistenceTimeoutFormatInvalid(InvalidRequestParameter):
    def __init__(self):
        self.message = 'when set session persistence, must have parameter timeout.'  # noqa

    def __str__(self):
        return self.message


class SessionPersistenceKeyFormatInvalid(InvalidRequestParameter):
    def __init__(self):
        self.message = 'when set session persistence to APP_COOKIE, must have parameter key.'  # noqa

    def __str__(self):
        return self.message


##################################################################
#
#  Other Exceptions
#
##################################################################

class ActionsPartialSuccessError(BaseIaasException):
    """
    when process multiple action, some failed. some succeeded.
    failed actions must have `exceptions`
    but success actions still count, so for
    the success part.
        if it resulted a job, place job_id here.
        if it resulted some concret results, pass them to results param

    normally there will be either results or job_id. but not both.
    """
    def __init__(self, exceptions, results=[], job_id=None):
        self.exceptions = exceptions
        self.results = results
        self.job_id = job_id

    def __str__(self):
        msg = ["some actions failed because the FOLLOWING exceptions:"]
        for ex_dict in self.exceptions:
            ex = ex_dict['exception']
            msg.append(str(ex))

        msg = "\n".join(msg)
        return msg


##################################################################
#
#  Specific Iaas Error Family
#
##################################################################

class ExplicitCodeException(BaseIaasException):
    pass


class CreateEipInsufficientFloatingip(ExplicitCodeException):
    def __init__(self, need, free):
        self.need = need
        self.free = free
        self.message = ('Eip can not be created, '
                        'free floating ips is insufficient. '
                        'you need %d, but there are %d left.' % (need, free))


class CreateLoadBalancerListenerWhenPortInUse(ExplicitCodeException):
    def __init__(self, port):
        self.port = port
        self.message = ('Listener can not be created '
                        'because the port (%s) has been used.') % (
            port)


class CreateLoadBalancerListenerOverLimit(ExplicitCodeException):
    def __init__(self, num):
        self.num = num
        self.message = ('Each loadbalancer has %s listeners at most and '
                        'has exceeded its resource limit.') % (
            num)


class LoadBalancerBackendOverLimit(ExplicitCodeException):
    def __init__(self, num):
        self.num = num
        self.message = ('Each listener has %s backends at most and '
                        'has exceeded its resource limit.') % (
            num)
