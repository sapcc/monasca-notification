# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
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

import logging
import monascastatsd

from monasca_common.kafka.consumer import KafkaConsumer
from monasca_common.kafka.producer import KafkaProducer
from processors.alarm_processor import AlarmProcessor
from processors.base import BaseProcessor
from processors.notification_processor import NotificationProcessor

log = logging.getLogger(__name__)


class NotificationEngine(object):
    def __init__(self, config):
        self._topics = {}
        self._topics['notification_topic'] = config['kafka']['notification_topic']
        self._topics['retry_topic'] = config['kafka']['notification_retry_topic']
        self._statsd = monascastatsd.Client(name='monasca',
                                            dimensions=BaseProcessor.dimensions)
        self._consumer = KafkaConsumer(config['kafka']['url'],
                                       config['zookeeper']['url'],
                                       config['zookeeper']['notification_path'],
                                       config['kafka']['group'],
                                       config['kafka']['alarm_topic'])
        self._producer = KafkaProducer(config['kafka']['url'])
        self._alarm_ttl = config['processors']['alarm']['ttl']
        self._alarms = AlarmProcessor(self._alarm_ttl, config)
        self._notifier = NotificationProcessor(config['notification_types'])

    def run(self):
        finished_count = self._statsd.get_counter(name='alarms_finished_count')
        for alarm in self._consumer:
            log.debug('Received alarm >|%s|<', str(alarm))
            notifications, partition, offset = self._alarms.to_notification(alarm)
            if notifications:
                sent, failed = self._notifier.send(notifications)
                self._producer.publish(self._topics['notification_topic'],
                                       [i.to_json() for i in sent])
                self._producer.publish(self._topics['retry_topic'],
                                       [i.to_json() for i in failed])
            self._consumer.commit()
            finished_count.increment()
