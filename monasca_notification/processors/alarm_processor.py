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
import logging
import monascastatsd
import time

from monasca_notification.common.repositories import exceptions as exc
from monasca_notification.common.utils import get_db_repo
from monasca_notification.notification import Notification
from monasca_notification.notification_exceptions import AlarmFormatError
from monasca_notification.processors.base import BaseProcessor


log = logging.getLogger(__name__)


class AlarmProcessor(BaseProcessor):
    def __init__(self, alarm_ttl, config):
        self._alarm_ttl = alarm_ttl
        self._statsd = monascastatsd.Client(name='monasca',
                                            dimensions=BaseProcessor.dimensions)
        self._db_repo = get_db_repo(config)

    @staticmethod
    def _parse_alarm(alarm_data):
        """Parse the alarm message making sure it matches the expected format.
        """
        expected_fields = [
            'actionsEnabled',
            'alarmId',
            'alarmDefinitionId',
            'alarmName',
            'newState',
            'oldState',
            'stateChangeReason',
            'severity',
            'link',
            'lifecycleState',
            'tenantId',
            'timestamp'
        ]
        json_alarm = json.loads(alarm_data)
        alarm = json_alarm['alarm-transitioned']
        for field in expected_fields:
            if field not in alarm:
                raise AlarmFormatError('Alarm data missing field %s' % field)
        if ('tenantId' not in alarm) or ('alarmId' not in alarm):
            raise AlarmFormatError

        return alarm

    def _alarm_is_valid(self, alarm):
        """Check if the alarm is enabled and is within the ttl, return True in that case
        """
        if not alarm['actionsEnabled']:
            log.debug('Actions are disabled for this alarm.')
            return False

        alarm_age = time.time() - alarm['timestamp'] / 1000
        if (self._alarm_ttl is not None) and (alarm_age > self._alarm_ttl):
            log.warn('Received alarm older than the ttl, skipping. Alarm from %s' %
                     time.ctime(alarm['timestamp'] / 1000))
            return False

        return True

    def _build_notification(self, partition, offset, alarm):
        db_time = self._statsd.get_timer()

        with db_time.time('config_db_time'):
            alarms_actions = self._db_repo.fetch_notification(alarm)

        return [Notification(alarms_action[0],
                             partition,
                             offset,
                             alarms_action[1],
                             alarms_action[2],
                             alarms_action[3],
                             0,
                             alarm) for alarms_action in alarms_actions]

    def to_notification(self, raw_alarm):
        """Check the notification setting for this project then create the appropriate notification
        """
        failed_parse_count = self._statsd.get_counter(name='alarms_failed_parse_count')
        no_notification_count = self._statsd.get_counter(name='alarms_no_notification_count')
        notification_count = self._statsd.get_counter(name='created_count')

        partition = raw_alarm[0]
        offset = raw_alarm[1].offset
        try:
            alarm = self._parse_alarm(raw_alarm[1].message.value)
        except Exception as e:  # This is general because of a lack of json exception base class
            failed_parse_count += 1
            log.exception("Invalid Alarm format skipping partition %d, offset %d\nError%s" % (partition, offset, e))
            return [], partition, offset

        log.debug("Read alarm from alarms sent_queue. Partition %d, Offset %d, alarm data %s"
                  % (partition, offset, alarm))

        if not self._alarm_is_valid(alarm):
            no_notification_count += 1
            return [], partition, offset

        try:
            notifications = self._build_notification(partition, offset, alarm)
        except exc.DatabaseException:
            log.debug('Database Error.  Attempting reconnect')
            notifications = self._build_notification(partition, offset, alarm)

        if len(notifications) == 0:
            no_notification_count += 1
            log.debug('No notifications found for this alarm, partition %d, offset %d, alarm data %s'
                      % (partition, offset, alarm))
            return [], partition, offset
        else:
            log.debug('Found %d notifications: [%s]', len(notifications), notifications)
            notification_count += len(notifications)
            return notifications, partition, offset
