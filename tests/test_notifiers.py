# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
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

import contextlib
import mock
import time
import unittest

from monasca_notification.notification import Notification
from monasca_notification.types import notifiers


def alarm(metrics):
    return {"tenantId": "0",
            "alarmId": "0",
            "alarmName": "test Alarm",
            "oldState": "OK",
            "newState": "ALARM",
            "severity": "LOW",
            "link": "some-link",
            "lifecycleState": "OPEN",
            "stateChangeReason": "I am alarming!",
            "timestamp": time.time(),
            "metrics": metrics}


class NotifyStub(object):
    def __init__(self, trap, config, send, failure):
        self.config_exception = config
        self.send_exception = send
        self.failure = failure
        self.trap = trap

    @property
    def type(self):
        return "email"

    @property
    def statsd_name(self):
        return "smtp_sent"

    def config(self, config_dict):
        if self.config_exception:
            raise Exception
        else:
            pass

    def send_notification(self, notification_obj):
        if self.send_exception:
            raise Exception
        else:
            if self.failure:
                return False
            else:
                return True


class Statsd(object):
    def __init__(self):
        self.timer = StatsdTimer()
        self.counter = StatsdCounter()

    def get_timer(self):
        return self.timer

    def get_counter(self, key):
        return self.counter


class StatsdTimer(object):
    def __init__(self):
        self.timer_calls = {}

    @contextlib.contextmanager
    def time(self, key):
        self.start(key)
        yield
        self.stop(key)

    def start(self, key):
        key = key + "_start"
        if key in self.timer_calls:
            self.timer_calls[key] += 1
        else:
            self.timer_calls[key] = 1

    def stop(self, key):
        key = key + "_stop"
        if key in self.timer_calls:
            self.timer_calls[key] += 1
        else:
            self.timer_calls[key] = 1


class StatsdCounter(object):
    def __init__(self):
        self.counter = 0

    def increment(self, val):
        self.counter += val


class TestInterface(unittest.TestCase):
    def setUp(self):
        self.trap = []
        self.statsd = Statsd()
        self.email_config = {'server': 'my.smtp.server',
                             'port': 25,
                             'user': None,
                             'password': None,
                             'timeout': 60,
                             'from_addr': 'hpcs.mon@hp.com'}

    def tearDown(self):
        notifiers.possible_notifiers = []
        notifiers.configured_notifiers = {}
        self.trap = []

    def _configExceptionStub(self, log):
        return NotifyStub(self.trap, True, False, False)

    def _sendExceptionStub(self, log):
        return NotifyStub(self.trap, False, True, False)

    def _sendFailureStub(self, log):
        return NotifyStub(self.trap, False, False, True)

    def _goodSendStub(self, log):
        return NotifyStub(self.trap, False, False, False)

    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_enabled_notifications(self, mock_log, mock_smtp):
        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'},
                       'pagerduty': {'address': 'xyz.com'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)
        notifications = notifiers.enabled_notifications()

        self.assertEqual(len(notifications), 3)
        self.assertEqual(sorted(notifications),
                         ["email", "pagerduty", "webhook"])

    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_config_missing_data(self, mock_log, mock_smtp):
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.info = self.trap.append

        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)

        self.assertIn("No config data for type: pagerduty", self.trap)

    @mock.patch('monasca_notification.types.notifiers.email_notifier')
    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_config_exception(self, mock_log, mock_smtp, mock_email):
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.exception = self.trap.append

        mock_email.EmailNotifier = self._configExceptionStub

        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'},
                       'pagerduty': {'address': 'abc'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)

        self.assertIn("config exception for email", self.trap)

    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_config_correct(self, mock_log, mock_smtp):
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.info = self.trap.append

        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'},
                       'pagerduty': {'address': 'abc'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)

        self.assertIn("email notification ready", self.trap)
        self.assertIn("webhook notification ready", self.trap)
        self.assertIn("pagerduty notification ready", self.trap)

    @mock.patch('monasca_notification.types.notifiers.email_notifier')
    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_send_notification_exception(self, mock_log, mock_smtp, mock_email):
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.exception = self.trap.append

        mock_email.EmailNotifier = self._sendExceptionStub

        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'},
                       'pagerduty': {'address': 'abc'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)

        notifications = []
        notifications.append(Notification('email', 0, 1,
                                          'email notification',
                                          'me@here.com', 0, alarm({})))

        notifiers.send_notifications(notifications)

        self.assertIn("send_notification exception for email", self.trap)

    @mock.patch('monasca_notification.types.notifiers.email_notifier')
    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_send_notification_failure(self, mock_log, mock_smtp, mock_email):
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.exception = self.trap.append

        mock_email.EmailNotifier = self._sendFailureStub

        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'},
                       'pagerduty': {'address': 'abc'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)

        notifications = []
        notifications.append(Notification('email', 0, 1,
                                          'email notification',
                                          'me@here.com', 0, alarm({})))

        sent, failed, invalid = notifiers.send_notifications(notifications)

        self.assertEqual(sent, [])
        self.assertEqual(len(failed), 1)
        self.assertEqual(invalid, [])

    @mock.patch('monasca_notification.types.notifiers.email_notifier')
    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_send_notification_unconfigured(self, mock_log, mock_smtp, mock_email):
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.info = self.trap.append

        mock_email.EmailNotifier = self._sendExceptionStub

        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)

        self.assertIn("No config data for type: pagerduty", self.trap)

        notifications = []
        notifications.append(Notification('pagerduty', 0, 1,
                                          'pagerduty notification',
                                          'me@here.com', 0, alarm({})))

        sent, failed, invalid = notifiers.send_notifications(notifications)

        self.assertEqual(sent, [])
        self.assertEqual(failed, [])
        self.assertEqual(len(invalid), 1)

        self.assertIn("attempting to send unconfigured notification: pagerduty", self.trap)

    @mock.patch('monasca_notification.types.notifiers.time')
    @mock.patch('monasca_notification.types.notifiers.email_notifier')
    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_send_notification_correct(self, mock_log, mock_smtp,
                                       mock_email, mock_time):
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append

        mock_email.EmailNotifier = self._goodSendStub

        mock_time.time.return_value = 42

        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'},
                       'pagerduty': {'address': 'abc'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)

        notifications = []
        notifications.append(Notification('email', 0, 1,
                                          'email notification',
                                          'me@here.com', 0, alarm({})))
        notifications.append(Notification('email', 0, 1,
                                          'email notification',
                                          'foo@here.com', 0, alarm({})))
        notifications.append(Notification('email', 0, 1,
                                          'email notification',
                                          'bar@here.com', 0, alarm({})))

        sent, failed, invalid = notifiers.send_notifications(notifications)

        self.assertEqual(len(sent), 3)
        self.assertEqual(failed, [])
        self.assertEqual(invalid, [])

        for n in sent:
            self.assertEqual(n.notification_timestamp, 42)

    @mock.patch('monasca_notification.types.notifiers.email_notifier')
    @mock.patch('monasca_notification.types.notifiers.email_notifier.smtplib')
    @mock.patch('monasca_notification.types.notifiers.log')
    def test_statsd(self, mock_log, mock_smtp, mock_email):
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append

        mock_email.EmailNotifier = self._goodSendStub

        config_dict = {'email': self.email_config,
                       'webhook': {'address': 'xyz.com'},
                       'pagerduty': {'address': 'abc'}}

        notifiers.init(self.statsd)
        notifiers.config(config_dict)

        notifications = []
        notifications.append(Notification('email', 0, 1,
                                          'email notification',
                                          'me@here.com', 0, alarm({})))
        notifications.append(Notification('email', 0, 1,
                                          'email notification',
                                          'foo@here.com', 0, alarm({})))
        notifications.append(Notification('email', 0, 1,
                                          'email notification',
                                          'bar@here.com', 0, alarm({})))

        notifiers.send_notifications(notifications)

        self.assertEqual(self.statsd.timer.timer_calls['email_time_start'], 3)
        self.assertEqual(self.statsd.timer.timer_calls['email_time_stop'], 3)
        self.assertEqual(self.statsd.counter.counter, 3)
