# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
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

import time

from oslo_log import log as logging

from monasca_notification.base_engine import BaseEngine
from monasca_notification.monitoring.metrics import ALARMS_FINISHED_COUNT
from processors.alarm_processor import AlarmProcessor
from processors.notification_processor import NotificationProcessor

log = logging.getLogger(__name__)


class NotificationEngine(BaseEngine):
    def __init__(self, config):
        super(NotificationEngine, self).__init__(config, config['kafka']['alarm_topic'], config['zookeeper']['notification_path'])
        self._topics = {}
        self._topics['notification_topic'] = config['kafka']['notification_topic']
        self._topics['retry_topic'] = config['kafka']['notification_retry_topic']
        self._alarm_ttl = config['processors']['alarm']['ttl']
        self._alarms = AlarmProcessor(self._alarm_ttl, config)
        self._finished_count = self._statsd.get_counter(name=ALARMS_FINISHED_COUNT)
        self._notifier = NotificationProcessor(config)

    def _add_periodic_notifications(self, notifications):
        for notification in notifications:
            topic = notification.periodic_topic
            if topic in self._config['kafka']['periodic'] and notification.type == "webhook":
                notification.notification_timestamp = time.time()
                self._producer.publish(self._config['kafka']['periodic'][topic],
                                       [notification.to_json()])

    def do_message(self, alarm):
        log.debug('Received alarm >|%s|<', str(alarm))
        notifications, partition, offset = self._alarms.to_notification(alarm)
        if notifications:
            self._add_periodic_notifications(notifications)

            sent, failed = self._notifier.send(notifications)
            self.publish_messages(sent, self._topics['notification_topic'])
            self.publish_messages(failed, self._topics['retry_topic'])


        self._consumer.commit()

        self._finished_count.increment()
