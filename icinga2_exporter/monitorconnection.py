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

import requests
import json
import aiohttp
from requests.auth import HTTPBasicAuth
import icinga2_exporter.log as log


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
            if 'enable_scrape_metadata' in config[MonitorConfig.config_entry]:
                self.enable_scrape_metadata = bool(config[MonitorConfig.config_entry]['enable_scrape_metadata'])
            config[MonitorConfig.config_entry]['passwd']

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

    def get_labels(self):
        labeldict = {}

        for label in self.labels:
            for custom_var, value in label.items():
                for key, prom_label in value.items():
                    labeldict.update({custom_var: prom_label})
        return labeldict

    def get_perfname_to_label(self):
        return self.perfname_to_label

    def get_perfdata(self, hostname):
        # Get performance data from Monitor and return in json format
        body = {"joins": ["host.vars"],
                "attrs": ["__name", "display_name", "check_command", "last_check_result", "vars", "host_name"],
                "filter": 'service.host_name==\"{}\"'.format(hostname)}

        data_json = self.post(self.url_query_service_perfdata, body)

        if not data_json:
            log.warn('Received no perfdata from Icinga2')

        return data_json

    def post(self, url, body):
        data_json = {}
        try:
            data_from_monitor = requests.post(url, auth=HTTPBasicAuth(self.user, self.passwd),
                                              verify=False,
                                              headers={'Content-Type': 'application/json',
                                                       'X-HTTP-Method-Override': 'GET'},
                                              data=json.dumps(body), timeout=self.timeout)
            data_json = json.loads(data_from_monitor.content)
            log.debug('API call: ' + data_from_monitor.url)
            data_from_monitor.raise_for_status()

            if data_from_monitor.status_code != 200 and data_from_monitor.status_code != 201:
                log.warn("Not a valid response - {}:{}".format(str(data_from_monitor.content),
                                                               data_from_monitor.status_code))
            else:
                log.info("call api {}".format(url), {'status': data_from_monitor.status_code,
                                                     'response_time': data_from_monitor.elapsed.total_seconds()})
        except requests.exceptions.RequestException as err:
            log.error("{}".format(str(err)))

        return data_json


    async def async_get_perfdata(self, hostname):
        # Get performance data from Monitor and return in json format
        body = {"joins": ["host.vars"],
                "attrs": ["__name", "display_name", "check_command", "last_check_result", "vars", "host_name", "downtime_depth", "acknowledgement","max_check_attempts", "last_reachable", "state", "state_type"],
                "filter": 'service.host_name==\"{}\"'.format(hostname)}

        data_json = await self.async_post(self.url_query_service_perfdata, body)

        if not data_json:
            log.warn('Received no perfdata from Icinga2')

        return data_json


    async def async_post(self, url, body):
        data_json = {}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, auth=aiohttp.BasicAuth(self.user, self.passwd),
                                        verify_ssl=False,
                                        headers={'Content-Type': 'application/json',
                                                 'X-HTTP-Method-Override': 'GET'},
                                        data=json.dumps(body)) as response:
                    re = await response.text()
                    return json.loads(re)
        finally:
            pass

    async def async_get_metadata(self, hostname):
        # Get performance data from Monitor and return in json format

        data_json = await self.async_get(self.url_query_host_metadata.format(hostname = hostname))

        if not data_json:
            log.warn('Received no metadata from Icinga2')

        return data_json

    async def async_get(self, url):
        data_json = {}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=aiohttp.BasicAuth(self.user, self.passwd),
                                        verify_ssl=False,
                                        headers={'Content-Type': 'application/json',
                                                 'X-HTTP-Method-Override': 'GET'}) as response:
                    re = await response.text()
                    return json.loads(re)
        finally:
            pass
