# -*- coding: utf-8 -*-
"""
    Copyright (C) 2019  Opsdis AB

    This file is part of icinga2-exporter.

    icinga2-exporter is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    icinga2-exporter is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with icinga2-exporter-exporter.  If not, see <http://www.gnu.org/licenses/>.

"""
import asyncio
import json
import time
from typing import Dict, Any

import aiohttp
from aiohttp import ClientConnectorError

import icinga2_exporter.log as log


class ScrapeExecption(Exception):
    def __init__(self, message: str, err: Exception, url: str = None):
        self.message = message
        self.err = err
        self.url = url


class Singleton(type):
    """
    Provide singleton pattern to MonitorConfig. A new instance is only created if:
     - instance do not exists
     - config is provide in constructor call, __init__
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances or args:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class MonitorConfig(object, metaclass=Singleton):
    config_entry = 'icinga2'

    def __init__(self, config=None):
        """
        The constructor takes on single argument that is a config dict
        :param config:
        """
        self.user = ''
        self.passwd = ''
        self.host = ''
        self.headers = {'content-type': 'application/json'}
        self.verify = False
        self.enable_scrape_metadata = False
        self.retries = 5
        self.timeout = 5
        self.labels = []
        self.url_query_service_perfdata = ''
        self.perfname_to_label = []
        self.host_check_service_name = 'alive'

        if config:
            self.user = config[MonitorConfig.config_entry]['user']
            self.passwd = config[MonitorConfig.config_entry]['passwd']
            self.host = config[MonitorConfig.config_entry]['url']
            if 'metric_prefix' in config[MonitorConfig.config_entry]:
                self.config_entry = config[MonitorConfig.config_entry]['metric_prefix'] + '_'
            if 'host_custom_vars' in config[MonitorConfig.config_entry]:
                self.labels = config[MonitorConfig.config_entry]['host_custom_vars']
            if 'perfnametolabel' in config[MonitorConfig.config_entry]:
                self.perfname_to_label = config[MonitorConfig.config_entry]['perfnametolabel']
            if 'timeout' in config[MonitorConfig.config_entry]:
                self.timeout = int(config[MonitorConfig.config_entry]['timeout'])
            if 'verify' in config[MonitorConfig.config_entry]:
                self.verify = bool(config[MonitorConfig.config_entry]['verify'])
            if 'enable_scrape_metadata' in config[MonitorConfig.config_entry]:
                self.enable_scrape_metadata = bool(config[MonitorConfig.config_entry]['enable_scrape_metadata'])
            if 'host_check_service_name' in config[MonitorConfig.config_entry]:
                self.host_check_service_name = config[MonitorConfig.config_entry]['host_check_service_name']

            self.url_query_service_perfdata = self.host + '/v1/objects/services'
            self.url_query_host_metadata = self.host + '/v1/objects/hosts/{hostname}'

    def get_enable_scrape_metadata(self):
        return self.enable_scrape_metadata

    def get_user(self):
        return self.user

    def get_passwd(self):
        return self.passwd

    def get_header(self):
        return self.headers

    def get_verify(self):
        return self.verify

    def get_url(self):
        return self.host

    def number_of_retries(self):
        return self.retries

    def get_prefix(self):
        return self.config_entry

    def get_host_check_service_name(self):
        return self.host_check_service_name

    def get_labels(self):
        labeldict = {}

        for label in self.labels:
            for custom_var, value in label.items():
                for key, prom_label in value.items():
                    labeldict.update({custom_var: prom_label})
        return labeldict

    def get_perfname_to_label(self):
        return self.perfname_to_label

    async def async_get_service_data(self, hostname) -> Dict[str, Any]:
        """
        Get the meta and performance data for all services on a hostname
        :param hostname:
        :return:
        """
        body = {"joins": ["host.vars"],
                "attrs": ["__name", "display_name", "check_command", "last_check_result", "vars", "host_name",
                          "downtime_depth", "acknowledgement", "max_check_attempts", "last_reachable", "state",
                          "state_type"],
                "filter": 'match(\"{}\",service.host_name)'.format(hostname)}

        data_json = await self.async_post(self.url_query_service_perfdata, body)

        if not data_json:
            log.warn('Received no perfdata from Icinga2')

        return data_json

    async def async_get_host_data(self, hostname) -> Dict[str, Any]:
        """
        Get the host data including the meta and performance data
        :param hostname:
        :return:
        """

        data_json = await self.async_post(self.url_query_host_metadata.format(hostname=hostname))

        if not data_json:
            log.warn('Received no metadata from Icinga2')

        return data_json

    async def async_post(self, url, body = None) -> Dict[str, Any]:

        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.monotonic()
                async with session.post(url, auth=aiohttp.BasicAuth(self.user, self.passwd),
                                        verify_ssl=self.verify,
                                        timeout=self.timeout,
                                        headers={'Content-Type': 'application/json',
                                                 'X-HTTP-Method-Override': 'GET'},
                                        data=json.dumps(body)) as response:
                    re = await response.text()
                    log.debug(f"request", {'method': 'post', 'url': url, 'status': response.status,
                                           'response_time': time.monotonic() - start_time})
                    if response.status != 200 and response.status != 201:
                        log.warn(f"{response.reason} status {response.status}")
                        return {}

                    return json.loads(re)

        except asyncio.TimeoutError as err:
            raise ScrapeExecption(message=f"Timeout after {self.timeout} sec", err=err, url=self.host)
        except ClientConnectorError as err:
            raise ScrapeExecption(message="Connection error", err=err, url=self.host)

