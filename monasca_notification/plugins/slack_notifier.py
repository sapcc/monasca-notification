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
import re
import urlparse

import requests

from monasca_notification.monitoring import client
from monasca_notification.monitoring.metrics import NOTIFICATION_SEND_TIMER
from monasca_notification.plugins import abstract_notifier

"""
   notification.address = https://slack.com/api/chat.postMessage?token=token&channel=#channel"

   Slack documentation about tokens:
        1. Login to your slack account via browser and check the following pages
             a. https://api.slack.com/docs/oauth-test-tokens
             b. https://api.slack.com/tokens

"""

STATSD_CLIENT = client.get_client()
STATSD_TIMER = STATSD_CLIENT.get_timer()


class SlackNotifier(abstract_notifier.AbstractNotifier):
    def __init__(self, log):
        super(SlackNotifier, self).__init__("slack")
        self._log = log

    def _build_slack_message(self, notification):
        """Builds slack message body
        """
        if self._template:
            template_vars = notification.to_dict()
            # replace markdown link syntax with Slack's own one
            template_vars['alarm_description'] = re.sub(r"\[(.*)\]\((.*)\)", r"<\2|\1>", notification.alarm_description)
            text = self._template.render(**template_vars)
            if not self._template_mime_type or self._template_mime_type == "text/plain":
                return dict(text=text)
            elif self._template_mime_type == "application/json":
                try:
                    return json.loads(text)
                except ValueError as ex:
                    self._log.exception("Invalid JSON template for Slack plugin")
                    self._log.error("Error loading rendered template JSON: %s\n%s", ex.message, text)
            else:
                self._log.error('Invalid configuration of Slack plugin. Unsupported template.mime_type: %s',
                                self._template_mime_type)

        return dict(text='{} - {}: {}'.format(notification.state, notification.alarm_description, notification.message))

    @STATSD_TIMER.timed(NOTIFICATION_SEND_TIMER, dimensions={'notification_type': 'slack'})
    def send_notification(self, notification):
        """Send the notification via slack
            Posts on the given url
        """

        slack_message = self._build_slack_message(notification)

        address = notification.address
        #  "#" is reserved character and replace it with ascii equivalent
        #  Slack room has "#" as first character
        address = address.replace("#", "%23")

        parsed_url = urlparse.urlsplit(address)
        query_params = urlparse.parse_qs(parsed_url.query)

        # extract channel parameter and map it to JSON
        if 'channel' in query_params:
            slack_message['channel'] = query_params.pop('channel').pop().replace('%23', '#')

        # URL without query params
        url = urlparse.urljoin(address, urlparse.urlparse(address).path)

        # Default option is to do cert verification
        verify = self._config.get('insecure', False)
        # If ca_certs is specified, do cert validation and ignore insecure flag
        if self._config.get("ca_certs"):
            verify = self._config.get("ca_certs")

        proxy_dict = None
        if self._config.get("proxy"):
            proxy_dict = {"https": self._config.get("proxy")}

        try:
            # Posting on the given URL
            self._log.debug("Sending to the url {0} , with query_params {1}".format(url, query_params))
            result = requests.post(url=url,
                                   json=slack_message,
                                   verify=verify,
                                   params=query_params,
                                   proxies=proxy_dict,
                                   timeout=self._config['timeout'])
            result.raise_for_status()
            if result.headers['content-type'] == 'application/json':
                response = result.json()
                if response.get('ok'):
                    self._log.debug("Notification successfully posted.")
                else:
                    self._log.warning("Received an error message {} when trying to send to slack on URL {}."
                                      .format(response.get("error"), url))
                return False

            return True
        except Exception as ex:
            self._log.exception("Error trying to send to slack  on URL {}: {}".format(url, ex.message))
            return False
