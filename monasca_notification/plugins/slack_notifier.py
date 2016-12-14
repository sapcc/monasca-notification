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
import urlparse

import requests
from jinja2 import Template
from jinja2 import TemplateSyntaxError

from monasca_notification.plugins import abstract_notifier

"""
   notification.address = https://slack.com/api/chat.postMessage?token=token&channel=#channel"

   Slack documentation about tokens:
        1. Login to your slack account via browser and check the following pages
             a. https://api.slack.com/docs/oauth-test-tokens
             b. https://api.slack.com/tokens

"""

log = logging.getLogger(__name__)


class SlackNotifier(abstract_notifier.AbstractNotifier):
    def __init__(self, log):
        self._log = log
        self._template = None

    def config(self, config_dict):
        super(SlackNotifier, self).config(config_dict)
        if self.config.template_text:
            self._template = Template(self.template_text)

    @property
    def type(self):
        return "slack"

    @property
    def statsd_name(self):
        return 'sent_slack_count'

    def _build_slack_message(self, notification):
        """Builds slack message body
        """
        if self._template:
            template_vars = notification.__dict__
            try:
                text = self._template.render(**template_vars)
                if not self._template_mime_type or self._template_mime_type == "text/plain":
                    return dict(text=text)
                elif self._template_mime_type == "application/json":
                    return json.loads(text)
                else:
                    log.error('Invalid configuration of Slack plugin. Unsupported template.mime_type: %s',
                              self._template_mime_type)
            except TemplateSyntaxError:
                log.exception('Formatting of Slack notification template failed')

        return dict(text='%s - %s: %s'.format(notification.state, notification.alarm_description, notification.message))

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
        # URL without query params
        url = urlparse.urljoin(address, urlparse.urlparse(address).path)

        # Default option is to do cert verification
        verify = self.config.get('insecure', False)
        # If ca_certs is specified, do cert validation and ignore insecure flag
        if (self.config.get("ca_certs")):
            verify = self.config.get("ca_certs")

        proxyDict = None
        if (self.config.get("proxy")):
            proxyDict = {"https": self.config.get("proxy")}

        try:
            # Posting on the given URL
            self._log.debug("Sending to the url {0} , with query_params {1}".format(url, query_params))
            result = requests.post(url=url,
                                   json=slack_message,
                                   verify=verify,
                                   params=query_params,
                                   proxies=proxyDict,
                                   timeout=self.config['timeout'])
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
