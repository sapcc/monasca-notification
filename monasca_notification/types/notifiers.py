# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

import logging
import time

from monasca_notification.types import email_notifier
from monasca_notification.types import pagerduty_notifier
from monasca_notification.types import webhook_notifier

log = logging.getLogger(__name__)

possible_notifiers = []
configured_notifiers = {}
statsd_counter = {}

statsd = None
statsd_timer = None


def init(statsd_obj):
    global statsd, statsd_timer
    statsd = statsd_obj
    statsd_timer = statsd.get_timer()

    possible_notifiers.append(email_notifier.EmailNotifier(log))
    possible_notifiers.append(webhook_notifier.WebhookNotifier(log))
    possible_notifiers.append(pagerduty_notifier.PagerdutyNotifier(log))


def enabled_notifications():
    results = []
    for key in configured_notifiers:
        results.append(key)
    return results


def config(config):
    for notifier in possible_notifiers:
        ntype = notifier.type
        if ntype in config:
            try:
                notifier.config(config[ntype])
                configured_notifiers[ntype] = notifier
                statsd_counter[ntype] = statsd.get_counter(notifier.statsd_name)
                log.info("{} notification ready".format(ntype))
            except Exception:
                log.exception("config exception for {}".format(ntype))
        else:
            log.warn("No config data for type: {}".format(ntype))


def send_notifications(notifications):
    sent = []
    failed = []
    invalid = []

    for notification in notifications:
        ntype = notification.type
        if ntype not in configured_notifiers:
            log.warn("attempting to send unconfigured notification: {}".format(ntype))
            invalid.append(notification)
            continue

        notification.notification_timestamp = time.time()

        with statsd_timer.time(ntype + '_time'):
            result = send_single_notification(notification)

        if result:
            sent.append(notification)
            statsd_counter[ntype].increment(1)
        else:
            failed.append(notification)

    return (sent, failed, invalid)


def send_single_notification(notification):
    ntype = notification.type
    try:
        return configured_notifiers[ntype].send_notification(notification)
    except Exception:
        log.exception("send_notification exception for {}".format(ntype))
        return False
