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

import argparse
import icinga2_exporter.log as log
import icinga2_exporter.fileconfiguration as config
import icinga2_exporter.proxy as proxy

from flask import Flask
import icinga2_exporter.monitorconnection as monitorconnection


def start():
    """
    Used from __main__ to start as simple flask app
    :return:
    """
    parser = argparse.ArgumentParser(description='monitor_exporter')

    parser.add_argument('-f', '--configfile',
                        dest="configfile", help="configuration file")

    parser.add_argument('-p', '--port',
                        dest="port", help="Server port")

    args = parser.parse_args()

    port = 9631

    config_file = 'config.yml'
    if args.configfile:
        config_file = args.configfile

    configuration = config.read_config(config_file)
    if 'port' in configuration:
        port = configuration['port']

    if args.port:
        port = args.port

    log.configure_logger(configuration)
    ##

    monitorconnection.MonitorConfig(configuration)
    log.info('Starting web app on port: ' + str(port))

    app = Flask(__name__)

    app.register_blueprint(proxy.app, url_prefix='/')
    app.run(host='0.0.0.0', port=port)


def create_app(config_path=None):
    """
    Used typical from gunicorn if need to pass config file different from default, e.g.
    gunicorn -b localhost:5000 --access-logfile /dev/null -w 4 "wsgi:create_app('/tmp/config.yml')"
    :param config_path:
    :return:
    """
    config_file = 'config.yml'
    if config_path:
        config_file = config_path

    configuration = config.read_config(config_file)

    log.configure_logger(configuration)

    monitorconnection.MonitorConfig(configuration)
    log.info('Starting web app')

    app = Flask(__name__)

    app.register_blueprint(proxy.app, url_prefix='/')

    return app
