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

import re
import urllib3
import icinga2_exporter.monitorconnection as Monitor
import icinga2_exporter.log as log

# Disable InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Perfdata:
    TOKENIZER_RE = (
            r"([^\s]+|'[^']+')=([-.\d]+)(c|s|ms|us|B|KB|MB|GB|TB|%)?" +
            r"(?:;([-.\d]+))?(?:;([-.\d]+))?(?:;([-.\d]+))?(?:;([-.\d]+))?")

    def __init__(self, monitor: Monitor, query_hostname: str):
        # Get Monitor configuration and build URL
        self.monitor = monitor
        self.query_hostname = query_hostname
        self.prefix = monitor.get_prefix()
        self.configured_labels = monitor.get_labels()
        self.perfname_to_label = monitor.get_perfname_to_label()
        self.perfdatadict = {}

    async def get_perfdata(self) -> dict:
        """
        Collect icinga2 data and parse it into prometheus metrics
        :return:
        """

        data_json = await self.monitor.async_get_perfdata(self.query_hostname)
        if 'results' in data_json:
            for serivce_attrs in data_json['results']:
                if 'attrs' in serivce_attrs and 'last_check_result' in serivce_attrs['attrs'] and 'performance_data' in \
                        serivce_attrs['attrs']['last_check_result'] and \
                        serivce_attrs['attrs']['last_check_result']['performance_data'] is not None:
                    check_command = serivce_attrs['attrs']['check_command']
                    # Get default labels
                    labels = {'hostname': serivce_attrs['attrs']['host_name'],
                              'service': serivce_attrs['attrs']['display_name']}

                    # For all host custom vars add as label
                    labels.update(Perfdata.get_host_custom_vars(serivce_attrs))


                    for perf_string in serivce_attrs['attrs']['last_check_result']['performance_data']:
                        perf = Perfdata.parse_perfdata(perf_string)

                        # For each perfdata metrics
                        for perf_data_key, perf_data_value in perf.items():

                            if 'value' in perf_data_value:
                                prometheus_key = self.format_promethues_metrics_name(check_command, perf_data_key,
                                                                                     perf_data_value)

                                # Add more labels based on perfname
                                if check_command in self.perfname_to_label:
                                    labels.update(
                                        Perfdata.add_labels_by_items(
                                            self.perfname_to_label[check_command]['label_name'],
                                            perf_data_key))

                                prometheus_key_with_labels = Perfdata.concat_metrics_name_and_labels(labels,
                                                                                                     prometheus_key)

                                self.perfdatadict.update({prometheus_key_with_labels: str(perf_data_value['value'])})

        return self.perfdatadict

    def format_promethues_metrics_name(self, check_command, key, value):
        """
        Format the prometheues metrics name according to naming configuration
        Typical
        icinga2_<check_command>_<perfname>_<unit>
        icinga2_<check_command>_<perfname>

        If the perfname to labels is configured for the check command it will formatted:
        icinga2_<check_command>_<unit>
        icinga2_<check_command>
        And than the perfname will be used as a label value

        :param check_command:
        :param key:
        :param value:
        :return:
        """
        if 'unit' in value and value['unit']:
            if check_command in self.perfname_to_label:
                prometheus_key = self.prefix + check_command + '_' + value['unit']
            else:
                prometheus_key = self.prefix + check_command + '_' + key.lower() + '_' + value['unit']
        else:
            if check_command in self.perfname_to_label:
                prometheus_key = self.prefix + check_command
            else:
                prometheus_key = self.prefix + check_command + '_' + key.lower()

        prometheus_key = Perfdata.rem_illegal_chars(prometheus_key)

        return prometheus_key

    def prometheus_format(self) -> str:
        """
        Build prometheus exporter response body
        :return:
        """
        metrics = ''
        for key, value in self.perfdatadict.items():
            metrics += key + ' ' + value + '\n'
        return metrics

    @staticmethod
    def get_host_custom_vars(serivce_attrs: dict) -> dict:
        """
        Get all host variables
        :param serivce_attrs:
        :return:
        """
        labels = {}
        if 'joins' in serivce_attrs and 'host' in serivce_attrs['joins'] and 'vars' in serivce_attrs['joins']['host']:
            for custom_vars_key, custom_vars_value in serivce_attrs['joins']['host']['vars'].items():
                labels[custom_vars_key.lower()] = custom_vars_value
        return labels

    @staticmethod
    def parse_perfdata(perfdata):
        """
        Parse the icinga2 perfdata depending of format
        :param perfdata:
        :return:
        """
        if type(perfdata) is str:
            perf = Perfdata.parse_perf_string(perfdata)
        elif type(perfdata) is dict:
            perf = Perfdata.parse_perf_dict(perfdata)
        else:
            perf = {}
        return perf

    @staticmethod
    def parse_perf_string(s: str) -> dict:
        """
        Parse icinga2 perfdata when in classic string format
        Return as
        <class 'dict'>: {'time': {'value': 0.00196, 'unit': 's', 'min': 0, 'max': 10}}
        :param s:
        :return:
        """

        metrics = {}
        counters = re.findall(Perfdata.TOKENIZER_RE, s)
        if counters is None:
            log.warn("Failed to parse performance data: {s}".format(
                s=s))
            return metrics

        for (key, value, uom, warn, crit, min, max) in counters:
            try:
                norm_value, norm_unit = Perfdata.normalize_to_unit(float(value), uom)
                metrics[key] = {'value': norm_value, 'unit': norm_unit}

            except ValueError:
                log.warn(
                    "Couldn't convert value '{value}' to float".format(
                        value=value))

        return metrics

    @staticmethod
    def parse_perf_dict(perf_string: dict) -> dict:
        """
        Parse icinga2 perfdata when in dict format
        :param perf_string:
        :return:
        """
        metrics = {perf_string['label']: {'value': perf_string['value'], 'unit': perf_string['unit']}}
        return metrics

    @staticmethod
    def normalize_to_unit(value, unit):
        """Normalize the value to the unit returned.
        We use base-1000 for second-based units, and base-1024 for
        byte-based units. Sadly, the Nagios-Plugins specification doesn't
        disambiguate base-1000 (KB) and base-1024 (KiB).
        """
        if unit == '%':
            return value / 100, 'ratio'
        if unit == 's':
            return value, 'seconds'
        if unit == 'ms':
            return value / 1000.0, 'seconds'
        if unit == 'us':
            return value / 1000000.0, 'seconds'
        if unit == 'B':
            return value, 'bytes'
        if unit == 'KB':
            return value * 1024, 'bytes'
        if unit == 'MB':
            return value * 1024 * 1024, 'bytes'
        if unit == 'GB':
            return value * 1024 * 1024 * 1024, 'bytes'
        if unit == 'TB':
            return value * 1024 * 1024 * 1024 * 1024, 'bytes'

        return value, ''

    @staticmethod
    def concat_metrics_name_and_labels(labels: dict, prometheus_key: str) -> str:
        """
        Build metric name with labels like
        metrics_name{label1="value1, .... }
        :param labels:
        :param prometheus_key:
        :return:
        """

        labelstring = Perfdata.labels_string(labels)
        prometheus_key = prometheus_key + '{' + labelstring + '}'

        return prometheus_key

    @staticmethod
    def labels_string(labels: dict) -> str:
        """
        Create a comma separated string of
        labels1=value1, ....
        :param labels:
        :return:
        """
        labelstring = ''
        sep = ''
        for label_key, label_value in labels.items():
            # Can only add custom vars that are simple strings. In incinga these can be complex dict structures
            # if type(label_value) is str or type(label_value) is int:
            if type(label_value) is str:
                labelstring += sep + label_key + '="' + label_value + '"'
                sep = ', '
        return labelstring

    @staticmethod
    def rem_illegal_chars(prometheus_key):
        # Replace illegal characters in metric name
        prometheus_key = prometheus_key.replace(' ', '_')
        prometheus_key = prometheus_key.replace('-', '_')
        prometheus_key = prometheus_key.replace('/', 'slash')
        prometheus_key = prometheus_key.replace('%', 'percent')
        return prometheus_key

    @staticmethod
    def add_labels_by_items(label: str, key: str) -> dict:
        item_label = {label.lower(): key}
        return item_label
