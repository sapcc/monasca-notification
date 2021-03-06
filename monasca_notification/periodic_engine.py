# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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
import time

from oslo_log import log as logging

from monasca_notification.base_engine import BaseEngine
from monasca_notification.common.repositories import exceptions
from monasca_notification.common.utils import construct_notification_object
from monasca_notification.common.utils import get_db_repo
from processors import notification_processor

log = logging.getLogger(__name__)


class PeriodicEngine(BaseEngine):
    def __init__(self, config, period):
        super(PeriodicEngine, self).__init__(config, config['kafka']['periodic'][period],
                                             config['zookeeper']['periodic_path'][period])

        self._notifier = notification_processor.NotificationProcessor(config)
        self._db_repo = get_db_repo(config)
        self._period = period

    def _keep_sending(self, alarm_id, original_state, type, period):
        try:
            current_state = self._db_repo.get_alarm_current_state(alarm_id)
        except exceptions.DatabaseException:
            log.debug('Database Error.  Attempting reconnect')
            current_state = self._db_repo.get_alarm_current_state(alarm_id)

        # Alarm was deleted
        if current_state is None:
            return False
        # Alarm state changed
        if current_state != original_state:
            return False
        # Don't repeat OK alarms
        if current_state == "OK":
            return False

        return True

    def do_message(self, raw_notification):
        message = raw_notification[1].message.value
        notification_data = json.loads(message)
        notification = construct_notification_object(self._db_repo, notification_data)

        if notification is None:
            self._consumer.commit()
            return

        if not notification_data['notification_timestamp']:
            log.debug(u"Notification Timestamp empty for {} with name {} "
                      u"at {} with period {}.  ".format(notification.type,
                                                        notification.name,
                                                        notification.notification_timestamp,
                                                        notification.period))
            self._consumer.commit()
            return

        if self._keep_sending(notification.alarm_id,
                              notification.state,
                              notification.type,
                              notification.period):

            wait_duration = notification.period - (
                time.time() - notification_data['notification_timestamp'])

            log.debug(u"Wait Duration {}".format(wait_duration))
            if wait_duration < 0:
                log.debug(u"Periodic Firing for {} with name {} "
                          u"at {} with period {}.  ".format(notification.type,
                                             notification.name,
                                             notification_data['notification_timestamp'],
                                             notification.period))
                notification.notification_timestamp = time.time()
                self._notifier.send([notification])
            else:
                # log.debug(u"Periodic Waiting for {} with name {} "
                #           u"at {} with period {}.  ".format(notification.type,
                #                              notification.name,
                #                              notification_data['notification_timestamp'],
                #                              notification.period))
                notification.notification_timestamp = notification_data['notification_timestamp']
                time.sleep(1)

            self.publish_messages([notification], self._topic_name)

        self._consumer.commit()
