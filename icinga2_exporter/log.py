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

import logging
import datetime
from pythonjsonlogger import jsonlogger

logger = logging.getLogger('icinga2-exporter')


# def configure_logger(log_level="INFO", log_filename=None, format=None):
def configure_logger(config):
    log_filename, log_level = read_config(config)

    if log_filename:
        hdlr = logging.FileHandler(log_filename)
    else:
        hdlr = logging.StreamHandler()

    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(log_level)

    # Add our handler to all loggers
    root = logging.root
    existing = root.manager.loggerDict.keys()
    for log1 in [logging.getLogger(name) for name in existing]:
        log1.addHandler(hdlr)

    # werkzeug = logging.getLogger('werkzeug')
    # werkzeug.setLevel("WARNING")


def read_config(config):
    log_filename = None
    log_level = 'INFO'
    if 'logger' in config:
        if 'logfile' in config['logger']:
            log_filename = config['logger']['logfile']

        if 'level' in config['logger']:
            log_level = config['logger']['level']
    return log_filename, log_level


def error(message, json_dict=None):
    logit(logger.error, json_dict, message)


def warn(message, json_dict=None):
    logit(logger.warning, json_dict, message)


def info(message, json_dict=None):
    logit(logger.info, json_dict, message)


def debug(message, json_dict=None):
    logit(logger.debug, json_dict, message)


def logit(log_func, json_dict, message):
    if json_dict:
        log_func('{}'.format(message), extra=json_dict)
    else:
        log_func('{}'.format(message))


def info_response_time(message: str, r_time: float):
    response_time = {"response_time_seconds": r_time}
    logger.info('{}'.format(message), extra=response_time)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
