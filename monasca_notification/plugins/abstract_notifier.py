# (C) Copyright 2015 Hewlett Packard Enterprise Development LP
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

import abc
import datetime

import six
from jinja2 import Template


@six.add_metaclass(abc.ABCMeta)
class AbstractNotifier(object):
    def __init__(self, type):
        self._config = None
        self._type = type
        self._template_text = None
        self._template_mime_type = None
        self._template = None

    @property
    def type(self):
        return self._type

    def config(self, config_dict):
        self._config = {'timeout': 5}
        self._config.update(config_dict)
        tpl = self._config.get('template')
        if tpl:
            self._template_text = tpl.get('text')
            if not self._template_text:
                tpl_path = tpl['template_file']
                self._template_text = open(tpl_path, 'r').read()
            self._template_mime_type = tpl.get('mime_type')
            self._template = Template(self._template_text)

    @abc.abstractmethod
    def send_notification(self, notification):
        pass

    def _format_text_for_channel(self, text_md):
        """format markdown text (from the description) into the representation for the notification channel
        :param text_md: input text in MarkDown
        :return: reformatted text

        The default implementation will just pass it through
        """
        return text_md

    def _render_notification_text(self, notification, template=None):
        """Render the text body of the notification

        :param notification: notification object used to populate template variables
        :param template: template to be used (default self._template)
        :return: rendered Jinja2 template
        """

        if not template:
            template = self._template

        template_vars = notification.to_dict()
        template_vars['alarm_timestamp_utc'] = str(
            datetime.datetime.utcfromtimestamp(notification.alarm_timestamp)).replace(" ", "T") + 'Z'
        # replace markdown link syntax with Slack's own one
        template_vars['alarm_description'] = self.format_description(notification.alarm_description)
        return template.render(**template_vars)