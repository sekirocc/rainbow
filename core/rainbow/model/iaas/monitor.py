import json
import time
import traceback
import datetime
from densefog import db
from densefog.model import base
from rainbow.model.project import project as project_model
from rainbow.model.iaas import load_balancer as lb_model
from rainbow.model.iaas import error as iaas_error
from rainbow.model.iaas.openstack import telemetry as telemetry_provider

from densefog import logger
logger = logger.getChild(__file__)

MONITOR_PERIOD_120_MINS = '120mins'
MONITOR_PERIOD_720_MINS = '720mins'
MONITOR_PERIOD_48_HOURS = '48hours'
MONITOR_PERIOD_14_DAYS = '14days'
MONITOR_PERIOD_30_DAYS = '30days'

MONITOR_PERIODS = {
    MONITOR_PERIOD_120_MINS: [60, 120],
    MONITOR_PERIOD_720_MINS: [60 * 5, 144],
    MONITOR_PERIOD_48_HOURS: [60 * 15, 192],
    MONITOR_PERIOD_14_DAYS: [60 * 60 * 2, 168],
    MONITOR_PERIOD_30_DAYS: [60 * 60 * 12, 60],
}

MONITOR_METRICS = {}


class Monitor(base.ProjectModel):

    @classmethod
    def db(cls):
        return db.DB.monitor

    def format(self):
        data = json.loads(self['data'])
        formated = {
            'resourceId': self['resource_id'],
            'metric': self['metric'],
            'period': self['period'],
            'interval': self['interval'],
            'timeSeries': data,
            'updated': self['updated'],
        }
        return formated


def get_monitor(resource_id, project_id, metric, period):
    logger.info('.get_monitor() begin')

    interval, steps = MONITOR_PERIODS[period]

    monitor = Monitor.first_as_model(lambda t: Monitor.and_(
        t.resource_id == resource_id,
        t.interval == interval,
        t.period == period,
        t.metric == metric))

    if monitor:
        monitor.must_belongs_project(project_id)

    now = datetime.datetime.utcnow()
    if monitor is None or \
       monitor['updated'] + datetime.timedelta(seconds=interval) < now:
        monitor = pre_aggregate_monitor(
            resource_id=resource_id,
            project_id=project_id,
            metric=metric,
            period=period)

    logger.info('.get_monitor() OK.')
    return monitor


def pre_aggregate_monitor(resource_id, project_id, metric, period):
    logger.info('.pre_aggregate_monitor() begin')

    if resource_id.startswith('lb-'):
        op_resource_id = lb_model.get(resource_id)['op_loadbalancer_id']
    else:
        raise iaas_error.MonitorNotFound(resource_id)

    project = project_model.get(project_id)
    op_project_id = project['op_project_id']

    metrics = MONITOR_METRICS[metric]
    interval, steps = MONITOR_PERIODS[period]

    now = datetime.datetime.utcnow()
    end = int(time.mktime(now.timetuple())) / interval * interval
    start = end - interval * steps

    aggregate = {}

    timestamp = start
    while timestamp < end:
        t = datetime.datetime.fromtimestamp(timestamp).isoformat()
        aggregate.setdefault(t, {})['timestamp'] = t
        timestamp += interval

    for i, sub_metric in enumerate(metrics):
        meter, aggregation = metrics[sub_metric]

        if resource_id.startswith('lb-'):
            if i == 0:
                op_resource_id = '00' + op_resource_id[2:]
            else:
                op_resource_id = '01' + op_resource_id[2:]
        try:
            meter_aggregate = telemetry_provider.statistics(
                meter=meter,
                resource_id=op_resource_id,
                project_id=op_project_id,
                aggregation=aggregation,
                period=interval,
                start=datetime.datetime.fromtimestamp(start),
                end=datetime.datetime.fromtimestamp(end))
        except Exception as ex:
            trace = traceback.format_exc()
            raise iaas_error.ProviderStatisticsError(ex, trace)
        else:
            for sample in meter_aggregate:
                timestamp = sample['period_start']
                aggregate.setdefault(timestamp, {})['timestamp'] = timestamp
                aggregate[timestamp][sub_metric] = sample['value']

    aggregate = sorted(aggregate.values(), key=lambda a: a['timestamp'])

    monitor = Monitor.first_as_model(lambda t: Monitor.and_(
        t.resource_id == resource_id,
        t.interval == interval,
        t.period == period,
        t.metric == metric))

    if monitor is None:
        monitor_id = Monitor.insert(**{
            'resource_id': resource_id,
            'project_id': project_id,
            'metric': metric,
            'period': period,
            'interval': interval,
            'data': json.dumps(aggregate),
            'updated': datetime.datetime.fromtimestamp(end),
            'created': datetime.datetime.utcnow(),
        })
    else:
        Monitor.update(
            id=monitor['id'],
            data=json.dumps(aggregate),
            updated=datetime.datetime.fromtimestamp(end),
        )
        monitor_id = monitor['id']

    logger.info('.pre_aggregate_monitor() OK.')

    return Monitor.get_as_model(monitor_id)
