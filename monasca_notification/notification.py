# (C) Copyright 2014-2016 Hewlett Packard Enterprise Development Company LP
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


class Notification(object):
    """An abstract base class used to define the notification interface
       and common functions
    """
    __slots__ = (
        'address',
        'alarm_id',
        'alarm_name',
        'alarm_timestamp',
        'message',
        'name',
        'notification_timestamp',
        'src_partition',
        'src_offset',
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

    def __init__(self, ntype, src_partition, src_offset, name, address, period,
                 retry_count, alarm):
        """Setup the notification object
             The src_partition and src_offset allow the notification
              to be linked to the alarm which triggered it.
             ntype - The notification type
             name - Name used in sending
             address - where to send the notification
             period - period of sending the notification
             retry_count - number of times we've tried to send
             alarm - info that caused the notification
             notifications that come after this one to remain uncommitted.
             Note that data may include unicode strings.
        """
        self.address = address
        self.name = name
        self.src_partition = src_partition
        self.src_offset = src_offset
        self.type = ntype
        self.retry_count = retry_count

        self.raw_alarm = alarm

        self.alarm_id = alarm['alarmId']
        self.alarm_name = alarm['alarmName']
        # The event timestamp is in milliseconds
        self.alarm_timestamp = alarm['timestamp'] / 1000
        self.message = alarm['stateChangeReason']
        self.state = alarm['newState']
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

    def __eq__(self, other):
        if not isinstance(other, Notification):
            return False

        for attrib in self.__slots__:
            if not getattr(self, attrib) == getattr(other, attrib):
                return False

        return True

    def to_json(self):
        """Return json representation
        """
        notification_fields = [
            'type',
            'name',
            'address',
            'retry_count',
            'raw_alarm',
            'alarm_id',
            'alarm_name',
            'alarm_timestamp',
            'message',
            'notification_timestamp',
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
        return json.dumps(notification_data)
