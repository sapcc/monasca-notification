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

import six
from jinja2 import Template


@six.add_metaclass(abc.ABCMeta)
class AbstractNotifier(object):

    def __init__(self):
        self._config = None
        self._template_text = None
        self._template_mime_type = None
        self._template = None

    @abc.abstractproperty
    def type(self):
        pass

    @abc.abstractproperty
    def statsd_name(self):
        pass

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
