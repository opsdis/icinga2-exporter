# -*- coding: utf-8 -*-
"""
    Copyright (C) 2019  Opsdis AB

    This file is part of monitor-exporter.

    monitor-exporter is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    monitor-exporter is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with monitor-exporter.  If not, see <http://www.gnu.org/licenses/>.

"""

from flask import Flask, request, Response, jsonify, Blueprint
from prometheus_client import (CONTENT_TYPE_LATEST, Counter)
from flask import Blueprint

from icinga2_exporter.perfdata import Perfdata
import icinga2_exporter.monitorconnection as monitorconnection
import icinga2_exporter.log as log

app = Blueprint("prom",__name__)
total_requests = Counter('requests', 'Total requests to monitor-exporter endpoint')


@app.route('/', methods=['GET'])
def hello_world():
    return 'monitor-exporter alive'


@app.route("/metrics", methods=['GET'])
def get_metrics():
    log.info(request.url)
    target = request.args.get('target')

    log.info('Collect metrics', {'target': target})

    monitor_data = Perfdata(monitorconnection.MonitorConfig(), target)

    # Fetch performance data from Monitor
    monitor_data.get_perfdata()

    target_metrics = monitor_data.prometheus_format()

    resp = Response(target_metrics)
    resp.headers['Content-Type'] = CONTENT_TYPE_LATEST

    return resp


@app.route("/health", methods=['GET'])
def get_health():
    return chech_healthy()


@app.after_request
def after_request_func(response):
    total_requests.inc()

    call_status = {'remote_addr': request.remote_addr, 'url': request.url, 'user_agent': request.user_agent,
                   'content_length': response.content_length, 'status': response.status_code}
    log.info('Access', call_status)

    return response


def chech_healthy() -> Response:
    resp = jsonify({'status': 'ok'})
    resp.status_code = 200
    return resp


# def read_config(config_file: str) -> dict:
#     """
#     Read configuration file
#     :param config_file:
#     :return:
#     """
#     config = {}
#     try:
#         ymlfile = open(config_file, 'r')
#         config = yaml.load(ymlfile, Loader=yaml.SafeLoader)
#     except (FileNotFoundError, IOError):
#         print("Config file {} not found".format(config_file))
#         exit(1)
#     except (yaml.YAMLError, yaml.MarkedYAMLError) as err:
#         print("Error will reading config file - {}".format(err))
#         exit(1)
#
#     return config


# def start():
#     parser = argparse.ArgumentParser(description='monitor_exporter')
#
#     parser.add_argument('-f', '--configfile',
#                         dest="configfile", help="configuration file")
#
#     parser.add_argument('-p', '--port',
#                         dest="port", help="Server port")
#
#     args = parser.parse_args()
#
#     port = 5000
#     if args.port:
#         port = args.port
#
#     config_file = 'config.yml'
#     if args.configfile:
#         config_file = args.configfile
#
#     configuration = config.read_config(config_file)
#
#     formatter = log.configure_logger(configuration)
#     ##
#
#     monitorconnection.MonitorConfig(configuration)
#     log.info('Starting web app on port: ' + str(port))
#
#
#     app.run(host='0.0.0.0', port=port)
#     app.logger.handlers[0].setFormatter(formatter)


# def create_app(config_path = None):
#
#     config_file = 'config.yml'
#     if config_path:
#         config_file = config_path
#
#     config = read_config(config_file)
#
#     formatter = log.configure_logger(config)
#
#     monitorconnection.MonitorConfig(config)
#     log.info('Starting web app')
#
#     app.logger.handlers[0].setFormatter(formatter)
#
#     return app