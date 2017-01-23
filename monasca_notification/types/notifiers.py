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

import logging
import time

from monasca_common.simport import simport

from monasca_notification.monitoring import client
from monasca_notification.monitoring.metrics import NOTIFICATION_SENT_COUNT, NOTIFICATION_SEND_ERROR_COUNT
from monasca_notification.plugins import email_notifier
from monasca_notification.plugins import pagerduty_notifier
from monasca_notification.plugins import webhook_notifier

log = logging.getLogger(__name__)

possible_notifiers = []
configured_notifiers = {}

STATSD_CLIENT = client.get_client()
statsd_sent_count = STATSD_CLIENT.get_counter(NOTIFICATION_SENT_COUNT)
statsd_send_error_count = STATSD_CLIENT.get_counter(NOTIFICATION_SEND_ERROR_COUNT)


def init():
    possible_notifiers.append(email_notifier.EmailNotifier(log))
    possible_notifiers.append(webhook_notifier.WebhookNotifier(log))
    possible_notifiers.append(pagerduty_notifier.PagerdutyNotifier(log))


def load_plugins(config):
    for plugin_class in config.get("plugins", []):
        try:
            possible_notifiers.append(simport.load(plugin_class)(log))
        except Exception:
            log.exception("unable to load the class {0} , ignoring it".format(plugin_class))


def enabled_notifications():
    results = []
    for key in configured_notifiers:
        results.append(key.upper())
    return results


def config(config):
    formatted_config = {type.lower(): value for type, value in config.iteritems()}
    for notifier in possible_notifiers:
        ntype = notifier.type.lower()
        if ntype in formatted_config:
            try:
                notifier.config(formatted_config[ntype])
                configured_notifiers[ntype] = notifier
                log.info("{} notification ready".format(ntype))
            except Exception:
                log.exception("config exception for {}".format(ntype))
        else:
            log.warn("No config data for type: {}".format(ntype))
    config_with_no_notifiers = set(formatted_config.keys()) - set(configured_notifiers.keys())
    if config_with_no_notifiers:
        log.warn("No notifiers found for {0}". format(", ".join(config_with_no_notifiers)))


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

        result = send_single_notification(notification)

        if result:
            sent.append(notification)
            statsd_sent_count.increment(1, dimensions={'notification_type': ntype})
        else:
            failed.append(notification)
            statsd_send_error_count.increment(1, dimensions={'notification_type': ntype})

    if len(invalid) > 0:
        statsd_send_error_count.increment(len(invalid), dimensions={'notification_type': 'INVALID'})

    return sent, failed, invalid


def send_single_notification(notification):
    ntype = notification.type
    try:
        return configured_notifiers[ntype].send_notification(notification)
    except Exception:
        log.exception("send_notification exception for {}".format(ntype))
        return False
