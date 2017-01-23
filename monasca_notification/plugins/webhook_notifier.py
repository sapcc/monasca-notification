# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
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

import requests

from monasca_notification.monitoring import client
from monasca_notification.monitoring.metrics import NOTIFICATION_SEND_TIMER
from monasca_notification.plugins import abstract_notifier

STATSD_CLIENT = client.get_client()
STATSD_TIMER = STATSD_CLIENT.get_timer()


class WebhookNotifier(abstract_notifier.AbstractNotifier):
    def __init__(self, log):
        super(WebhookNotifier, self).__init__("webhook")
        self._log = log

    @STATSD_TIMER.timed(NOTIFICATION_SEND_TIMER, dimensions={'notification_type': 'webhook'})
    def send_notification(self, notification):
        """Send the notification via webhook
            Posts on the given url
        """

        body = {'alarm_id': notification.alarm_id,
                'alarm_definition_id': notification.raw_alarm['alarmDefinitionId'],
                'alarm_name': notification.alarm_name,
                'alarm_description': notification.raw_alarm['alarmDescription'],
                'alarm_timestamp': notification.alarm_timestamp,
                'state': notification.state,
                'old_state': notification.raw_alarm['oldState'],
                'message': notification.message,
                'tenant_id': notification.tenant_id,
                'metrics': notification.metrics}

        headers = {'content-type': 'application/json'}

        url = notification.address

        try:
            # Posting on the given URL
            result = requests.post(url=url,
                                   data=json.dumps(body),
                                   headers=headers,
                                   timeout=self._config['timeout'])

            if result.status_code in range(200, 300):
                self._log.info("Notification successfully posted.")
                return True
            else:
                self._log.error("Received an HTTP code {} when trying to post on URL {}."
                                .format(result.status_code, url))
                return False
        except Exception:
            self._log.exception("Error trying to post on URL {}".format(url))
            return False
