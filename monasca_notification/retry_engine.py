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

import json
import time

from kafka import common

from monasca_notification.base_engine import BaseEngine
from monasca_notification.common.utils import construct_notification_object
from monasca_notification.common.utils import get_db_repo
from oslo_log import log as logging
from processors import notification_processor

from monitoring.metrics import KAFKA_CONSUMER_ERRORS, KAFKA_PRODUCER_ERRORS

log = logging.getLogger(__name__)


class RetryEngine(BaseEngine):
    def __init__(self, config):
        super(RetryEngine, self).__init__(config, config['kafka']['notification_retry_topic'],
                                          config['zookeeper']['notification_retry_path'])

        self._retry_interval = config['retry']['interval']
        self._retry_max = config['retry']['max_attempts']

        self._topics = {}
        self._topics['notification_topic'] = config['kafka']['notification_topic']
        self._topics['retry_topic'] = config['kafka']['notification_retry_topic']

        self._notifier = notification_processor.NotificationProcessor(config)
        self._db_repo = get_db_repo(config)

    def run(self):
        consumer_errors = self._statsd.get_counter(name=KAFKA_CONSUMER_ERRORS,
                                                   dimensions={'topic': self._topic_name})
        notification_producer_errors = self._statsd.get_counter(name=KAFKA_PRODUCER_ERRORS,
                                                   dimensions={'topic': self._topics['notification_topic']})
        retry_producer_errors = self._statsd.get_counter(name=KAFKA_PRODUCER_ERRORS,
                                                   dimensions={'topic': self._topics['retry_topic']})
        try:
            for raw_notification in self._consumer:
                message = raw_notification[1].message.value

                notification_data = json.loads(message)

                notification = construct_notification_object(self._db_repo, notification_data)

                if notification is None:
                    self._consumer.commit()
                    continue

                wait_duration = self._retry_interval - (
                    time.time() - notification_data['notification_timestamp'])

                if wait_duration > 0:
                    time.sleep(wait_duration)

                sent, failed = self._notifier.send([notification])

                if sent:
                    self.publish_messages([notification], self._topics['notification_topic'], notification_producer_errors)

                if failed:
                    notification.retry_count += 1
                    notification.notification_timestamp = time.time()
                    if notification.retry_count < self._retry_max:
                        log.error(u"retry failed for {} with name {} "
                                  u"at {}.  "
                                  u"Saving for later retry.".format(notification.type,
                                                                    notification.name,
                                                                    notification.address))
                        self.publish_messages([notification], self._topics['retry_topic'], retry_producer_errors)
                    else:
                        log.error(u"retry failed for {} with name {} "
                                  u"at {} after {} retries.  "
                                  u"Giving up on retry."
                                  .format(notification.type,
                                          notification.name,
                                          notification.address,
                                          self._retry_max))

                self._consumer.commit()

        except common.KafkaError:
            log.exception("Notification encountered Kafka errors while reading alarms")
            consumer_errors.increment(1)
            raise
