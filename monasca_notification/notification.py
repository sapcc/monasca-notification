# (C) Copyright 2014-2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging

import time

import datetime
from jinja2 import Template
from jinja2 import TemplateSyntaxError

log = logging.getLogger(__name__)


class Notification(object):
    """An abstract base class used to define the notification interface
       and common functions
    """
    __slots__ = (
        'address',
        'alarm_id',
        'alarm_name',
        'alarm_description',
        'alarm_timestamp',
        'alarm_age',
        'dimensions',
        'id',
        'message',
        'metric_values',
        'name',
        'notification_timestamp',
        'old_state',
        'state',
        'severity',
        'link',
        'lifecycle_state',
        'tenant_id',
        'type',
        'metrics',
        'retry_count',
        'raw_alarm',
        'period',
        'periodic_topic'
    )

    def __init__(self, id, type, name, address, period, retry_count, alarm):
        """Setup the notification object
             id - The notification id
             type - The notification type
             name - Name used in sending
             address - where to send the notification
             period - period of sending the notificationv
             retry_count - number of times we've tried to send
             alarm - info that caused the notification
             notifications that come after this one to remain uncommitted.
             Note that data may include unicode strings.
        """
        self.id = id
        self.address = address
        self.name = name
        self.type = type
        self.retry_count = retry_count

        self.raw_alarm = alarm

        self.alarm_id = alarm['alarmId']
        self.alarm_name = alarm['alarmName']
        self.alarm_description = alarm['alarmDescription']
        # The event timestamp is in milliseconds
        self.alarm_timestamp = alarm['timestamp'] / 1000
        self.alarm_age = time.time() - self.alarm_timestamp
        self.message = alarm['stateChangeReason']
        self.state = alarm['newState']
        self.old_state = alarm['oldState']
        self.severity = alarm['severity']
        self.link = alarm['link']
        self.lifecycle_state = alarm['lifecycleState']
        self.tenant_id = alarm['tenantId']
        self.metrics = alarm['metrics']

        # to be updated on actual notification send time
        self.notification_timestamp = None

        # set periodic topic
        self.periodic_topic = period
        self.period = period

        # collect alarm dimensions and render alarm-description as needed
        self.dimensions = {}
        for metric in self.metrics:
            for k, v in metric['dimensions'].iteritems():
                old = self.dimensions.get(k)
                if not old:
                    self.dimensions[k] = v
                elif isinstance(old, set):
                    old.add(v)
                else:
                    self.dimensions[k] = {old, v}
        for k, v in self.dimensions.iteritems():
            if isinstance(v, set):
                self.dimensions[k] = ", ".join(v)

        # provide actual metric values leading to the alarm
        self.metric_values = {}
        for subalarm in alarm['subAlarms']:
            metric_name = subalarm['subAlarmExpression']['metricDefinition']['name']
            metric_value = subalarm['currentValues']
            if len(metric_value) == 0:
                self.metric_values[metric_name] = None
            elif len(metric_value) == 1:
                self.metric_values[metric_name] = metric_value[0]
            else:
                self.metric_values[metric_name] = metric_value

        # add additional variables
        template_vars = {}
        template_vars.update(self.dimensions)
        template_vars.update(self.metric_values)
        template_vars['_age'] = self.alarm_age
        template_vars['_timestamp'] = str(datetime.datetime.utcfromtimestamp(self.alarm_timestamp)).replace(" ", "T") + 'Z'
        template_vars['_state'] = self.state
        template_vars['_old_state'] = self.old_state

        # attempt interpreting description as Jinja2 template
        try:
            self.alarm_description = Template(self.alarm_description).render(**template_vars)
        except TemplateSyntaxError:
            pass
        except Exception:
            log.exception("failed rendering alarm-definition: %s", self.alarm_description)

    def __eq__(self, other):
        if not isinstance(other, Notification):
            return False

        for attrib in self.__slots__:
            if not getattr(self, attrib) == getattr(other, attrib):
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_json(self):
        notification_data = self.to_dict()
        return json.dumps(notification_data)

    def to_dict(self):
        """Return json representation
            """
        notification_fields = [
            'id',
            'type',
            'name',
            'address',
            'retry_count',
            'raw_alarm',
            'alarm_id',
            'alarm_name',
            'alarm_description',
            'alarm_timestamp',
            'message',
            'notification_timestamp',
            'old_state',
            'state',
            'severity',
            'link',
            'lifecycle_state',
            'tenant_id',
            'period',
            'periodic_topic'
        ]
        notification_data = {name: getattr(self, name)
                             for name in notification_fields}
        return notification_data
