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
import time

from prometheus_client import (CONTENT_TYPE_LATEST, Counter)
from quart import request, Response, jsonify, Blueprint

import icinga2_exporter.log as log
import icinga2_exporter.monitorconnection as monitorconnection
from icinga2_exporter.perfdata import Perfdata

app = Blueprint('icinga2', __name__)
total_requests = Counter('requests', 'Total requests to monitor-exporter endpoint')


@app.route('/', methods=['GET'])
def hello_world():
    return 'monitor-exporter alive'


@app.route("/metrics", methods=['GET'])
async def get_metrics():
    #log.info(request.url)
    target = request.args.get('target')

    monitor_data = Perfdata(monitorconnection.MonitorConfig(), target)

    # Fetch performance data from Monitor
    start_time = time.monotonic()
    try:
        loop = asyncio.get_event_loop()
        fetch_perfdata_task = loop.create_task(monitor_data.get_service_metrics())

        if monitorconnection.MonitorConfig().get_enable_scrape_metadata():
            fetch_metadata_task = loop.create_task(monitor_data.get_host_metrics())
            await fetch_metadata_task

        await fetch_perfdata_task

        scrape_duration = time.monotonic() - start_time
        monitor_data.add_perfdata("scrape_duration_seconds",
                                  {'hostname': target, 'server': monitorconnection.MonitorConfig().get_url()},
                                  scrape_duration)
        log.info("scrape", {'target': target, 'url': request.url, 'scrape_time': scrape_duration})
        target_metrics = monitor_data.prometheus_format()

        resp = Response(target_metrics)
        resp.headers['Content-Type'] = CONTENT_TYPE_LATEST
        # after_request_func(resp)
        return resp
    except monitorconnection.ScrapeExecption as err:
        log.warn(f"{err.message}", {'target': target, 'url': request.url, 'remote_url': err.url, 'err': err.err})
        resp = Response("")
        resp.status_code = 500
        return resp


@app.route("/health", methods=['GET'])
def get_health():
    return check_healthy()


# @app.after_request
def after_request_func(response):
    total_requests.inc()

    call_status = {'remote_addr': request.remote_addr, 'url': request.url, 'user_agent': request.user_agent,
                   'content_length': response.content_length, 'status': response.status_code}
    log.info('Access', call_status)

    return response


def check_healthy() -> Response:
    resp = jsonify({'status': 'ok'})
    resp.status_code = 200
    return resp
