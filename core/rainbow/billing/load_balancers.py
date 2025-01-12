import traceback
from rainbow.billing.biller import BaseBiller
from rainbow.billing.biller import RESOURCE_TYPE_BANDWIDTH

from densefog import logger
logger = logger.getChild(__file__)


class LoadBalancerBiller(BaseBiller):

    def _collect_usages(self, project_id, load_balancer_ids):
        from rainbow.model.iaas import load_balancer as lb_model
        page = lb_model.limitation(project_ids=[project_id],
                                   load_balancer_ids=load_balancer_ids)
        load_balancers = page['items']

        resource_usages = []
        for load_balancer in load_balancers:
            resource_usages.append({
                'resource_id': load_balancer['id'],
                'resource_name': load_balancer['name'],
                'resource_usage': '%dMbps' % load_balancer['bandwidth'],
            })
        return resource_usages

    def create_load_balancers(self, project_id, load_balancer_ids):
        logger.info('biller to create load_balancers: %s' % load_balancer_ids)

        if not project_id or not load_balancer_ids:
            return

        resource_usages = self._collect_usages(project_id, load_balancer_ids)

        try:
            resp = self.create_resources(project_id,
                                         RESOURCE_TYPE_BANDWIDTH,
                                         None,
                                         resource_usages)
            logger.info('create_resources resp code: %s, message: %s' % (
                        resp['retCode'], resp['message']))
            return resp

        except Exception:
            stack = traceback.format_exc()
            logger.trace(stack)
        pass

    def delete_load_balancers(self, project_id, load_balancer_ids):
        logger.info('biller to delete load_balancers: %s' % load_balancer_ids)

        if not project_id or not load_balancer_ids:
            return

        try:
            resp = self.delete_resources(project_id, load_balancer_ids)

            logger.info('delete_resources resp code: %s, message: %s' % (
                        resp['retCode'], resp['message']))
            return resp

        except Exception:
            stack = traceback.format_exc()
            logger.trace(stack)

    def update_bandwidth(self, project_id, load_balancer_ids):
        logger.info('biller to update brandwidth load_balancers: %s' %
                    load_balancer_ids)

        if not project_id or not load_balancer_ids:
            return

        resource_usages = self._collect_usages(project_id, load_balancer_ids)

        try:
            resps = []
            for resource_usage in resource_usages:
                resource_id = resource_usage['resource_id']
                usage = resource_usage['resource_usage']
                resp = self.modify_resource_attributes(project_id,
                                                       resource_id,
                                                       None,
                                                       usage)

                logger.info('modify_resource_attributes resp code: %s, '
                            'message: %s' % (resp['retCode'], resp['message']))
                resps.append(resp)

            return resps

        except Exception:
            stack = traceback.format_exc()
            logger.trace(stack)
