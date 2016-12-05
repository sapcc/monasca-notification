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
ALARMS_FINISHED_COUNT = 'notification.alarms_finished_count'