# Copyright 2015 FUJITSU LIMITED
# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

import logging
import pymysql

from monasca_notification.common.repositories.base.base_repo import BaseRepo
from monasca_notification.common.repositories import exceptions as exc

log = logging.getLogger(__name__)


class MysqlRepo(BaseRepo):
    def __init__(self, config):
        super(MysqlRepo, self).__init__(config)
        if 'ssl' in config['mysql']:
            self._mysql_ssl = config['mysql']['ssl']
        else:
            self._mysql_ssl = None

        self._mysql_host = config['mysql']['host']
        self._mysql_user = config['mysql']['user']
        self._mysql_passwd = config['mysql']['passwd']
        self._mysql_dbname = config['mysql']['db']
        self._mysql = None

    def _connect_to_mysql(self):
        self._mysql = None
        try:
            self._mysql = pymysql.connect(host=self._mysql_host,
                                          user=self._mysql_user,
                                          passwd=unicode(self._mysql_passwd).encode('utf-8'),
                                          db=self._mysql_dbname,
                                          ssl=self._mysql_ssl,
                                          use_unicode=True,
                                          charset="utf8")
            self._mysql.autocommit(True)
        except pymysql.Error as e:
            log.exception('MySQL connect failed %s', e)
            raise

    def fetch_notification(self, alarm):
        try:
            if self._mysql is None:
                self._connect_to_mysql()

            cur = self._mysql.cursor()
            cur.execute(self._find_alarm_action_sql, (alarm['alarmDefinitionId'], alarm['newState']))

            for row in cur:
                yield (row[1].lower(), row[0], row[2])
        except pymysql.Error as e:
            self._mysql = None
            log.exception("Couldn't fetch alarms actions %s", e)
            raise exc.DatabaseException(e)
