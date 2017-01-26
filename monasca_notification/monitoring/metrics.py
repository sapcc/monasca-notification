# Copyright 2016 FUJITSU LIMITED
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

KAFKA_CONSUMER_ERRORS = 'kafka.consumer_errors'
""" errors occured when fetching messages from Kafka (incl. ZK) """
KAFKA_PRODUCER_ERRORS = "kafka.producer_errors"
""" errors when publishing a message or message batch to Kafka """
ALARMS_FINISHED_COUNT = 'notification.alarms_processed'
""" number of processed alarms """
NOTIFICATION_SENT_COUNT = 'notification.notifications_sent'
""" number of sent notifications """
NOTIFICATION_SEND_ERROR_COUNT = 'notification.notification_send_errors'
""" number of notification send errors """
NOTIFICATION_SEND_TIMER = 'notification.notification_send_time'
""" number of notification send timing """

CONFIGDB_ERRORS = "configdb.access_errors"
""" errors when accessing the configuration DB (e.g. MySQL) """
CONFIGDB_TIME = "configdb.access_time"
""" time needed to access the configuration DB (e.g. MySQL) """
