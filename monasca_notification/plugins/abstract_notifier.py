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


@six.add_metaclass(abc.ABCMeta)
class AbstractNotifier(object):

    def __init__(self):
        self.config = None
        self.template_text = None
        self.template_mime_type = None

    @abc.abstractproperty
    def type(self):
        pass

    @abc.abstractproperty
    def statsd_name(self):
        pass

    def config(self, config_dict):
        self.config = {'timeout': 5}
        self.config.update(config_dict)
        tpl = self.config.get('template')
        if tpl:
            self.template_text = tpl.get('text')
            if not self.template_text:
                tpl_path = tpl['template_file']
                self.template_text = open(tpl_path, 'r').read()
            self.template_mime_type = tpl.get('mime_type')

    @abc.abstractmethod
    def send_notification(self, notification):
        pass
