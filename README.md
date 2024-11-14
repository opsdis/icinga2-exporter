[![PyPI version](https://badge.fury.io/py/icinga2-exporter.svg)](https://badge.fury.io/py/icinga2-exporter)

icinga2-exporter
-----------------------

# Overview

The icinga2-exporter utilizes the [Icinga 2](https://icinga.com/) REST API to fetch service based performance
data and publish it in a way that lets [Prometheus](https://prometheus.io/) scrape the performance data as metrics.

The service is based on [Quart](https://pgjones.gitlab.io/quart/). Quart's is compatible with Flask but based 
on Asyncio.  

Benefits:

- Enable advanced queries and aggregation on timeseries
- Prometheus based alerting rules
- Grafana graphing
- Utilize investments with Icinga 2 of collecting metrics


# Metrics naming

## Metric names
Metrics that is scraped with the icinga2-exporter will have the following name structure:

    <metric_prefix>_<check_command>_<perfname>_<unit>

> The metric_prefix can be changed by the configuration, defaults to icinga2
> 
> Unit is only added if it exists on performance data

Example from check command `check_ping` will result in two metrics:

    icinga2_ping_rta_seconds
    icinga2_ping_pl_ratio

## Metric labels

The icinga2-exporter adds a number of labels to each metrics:

- hostname - is the `host_name` in icinga2
- service - is the `display_name` in icinga2

Optional icinga2-exporter can be configured to add specific custom variables configured on the host.

> **Note**:
>
> Icinga 2 supports custom variables that can be complex data structures - but that is NOT currently supported.

Labels created from custom variables are all transformed to lowercase.

### Performance metrics name to labels

As described above the default naming of the Prometheus name is:

    icinga2_<check_command>_<perfname>_<unit>

For some checks this does not work well like for the `disk` check command where the perfname are the unique mount paths.
For checks like that the where the perfname is defined depending on environment you can change so the perfname instead becomes a label.
This is defined in the configuration like:

```yaml
  perfnametolabel:
      # The command name
      disk:
        # the label name to be used
        label_name: mount
```
So if the check command is `disk` the Prometheus metrics will have a format like, depending on other custom variables :

    icinga2_disk_bytes{hostname="icinga2", service="disk", os="Docker", mount="/var/lib/icinga2"} 48356130816.0

If we did not make this translation we would got the following:

    icinga2_disk_slashvarslashibslashicinga2_bytes{hostname="icinga2", service="disk", os="Docker"} 48356130816.0

This would not be good from a cardinality point of view.

# Scrape duration

The scrape duration is a metrics that is reported for all targets. 

    icinga2_scrape_duration_seconds{hostname="<target>", server="<icinga2_server_url>"} 0.160983

# Scrape response

When requests are made to the exporter the following responses are possible:

- A target that exists - return all metrics and http status 200
- A target does not exists - return no metrics, empty response, and http status 200
- The export fail to scrape metrics from icinga2 - return empty response and http status 500

In the last scenario the exporter will log the reason for the failed scrape. A failed scrape can
have multiple reasons, for example:

- The icinga2 server is not responding
- Not having valid credentials
- Request to icinga2 timeout


# Configuration

## icinga2-exporter

The `icinga2-exporter` is configured by a yaml based configuration file.

Example:
```yaml

# Port can be overridden by using -p if running development quart
#port: 9638

icinga2:
   # The url to the icinga2 server
   url: https://127.0.0.1:5665
   # The icinga2 username
   user: root
   # The icinga2 password
   passwd: cf593406ffcfd2ef
   # Verify the ssl certificate, default false
   verify: false
   # Timeout accessing icinga server, default 5 sec
   timeout: 5
   # All prometheus metrics will be prefixed with this string
   metric_prefix: icinga2
   # Enables a separate request to fetch host metadata like state and state_type. Default false
   enable_scrape_metadata: true
   # Enables export of warning and critical threshold values. Default false
   enable_scrape_thresholds: false

   # Set the service name for host check metric, default is alive - only change this if it is a name conflict with other
   # services
   # host_check_service_name: alive

   # Example of host customer variables that should be added as labels and how to be translated
   host_custom_vars:
      # Specify which custom_vars to extract from hosts in icinga2
      - env:
           # Name of the label in Prometheus
           label_name: environment
      - site:
           label_name: dc

   # This section enable that for specific check commands the perfdata metrics name will not be part of the
   # prometheus metrics name, instead moved to a label
   # E.g for the disk command the perfdata name will be set to the label disk like:
   # icinga2_disk_bytes{hostname="icinga2", service="disk", os="Docker", disk="/var/log/icinga2"}
   perfnametolabel:
      # The command name
      disk:
         # the label name to be used
         label_name: mount

logger:
   # Path and name for the log file. If not set send to stdout
   logfile: /var/tmp/icinga2-exporter.log
   # Log level
   level: INFO
```

> When running with gunicorn the port is selected by gunicorn

## enable_scrape_thresholds

Set this to `true` to scrape warning and critical threshold values.

Thresholds that are scraped with the icinga2-exporter will have the following name structure:

    <metric_prefix>_<check_command>_<perfname>_<unit>_threshold_critical
    <metric_prefix>_<check_command>_<perfname>_<unit>_threshold_warning

> The metric_prefix can be changed by the configuration, defaults to icinga2
> 
> Unit is only added if it exists on performance data

Example from check command `check_ping` will result in two metrics together with metrics for critical and warning thresholds:

    icinga2_ping4_rta_seconds
    icinga2_ping4_rta_seconds_threshold_critical
    icinga2_ping4_rta_seconds_threshold_warning
    icinga2_ping_pl_ratio
    icinga2_ping4_pl_ratio_threshold_critical
    icinga2_ping4_pl_ratio_threshold_warning

## Logging

The log stream is configure in the above config. If `logfile` is not set the logs will go to stdout.

Logs are formatted as json so its easy to store logs in log servers like Loki and Elasticsearch.

## Prometheus configuration
Prometheus can be used with static configuration or with dynamic file discovery using the project [monitor-promdiscovery](https://github.com/opsdis/monitor-promdiscovery).

Please add the job to the `scrape_configs` in prometheus.yml.

> The target is the `host_name` configured in icinga2.

### Static config
```yaml

scrape_configs:
  - job_name: 'icinga2'
    metrics_path: /metrics
    static_configs:
      - targets:
        - icinga2
        - google.se
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9638

```

### File discovery config for usage with `monitor-promdiscovery`

```yaml

scrape_configs:
  - job_name: 'icinga2'
    scrape_interval: 1m
    metrics_path: /metrics
    file_sd_configs:
    - files:
      - 'sd/icinga2_sd.yml'
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9638

```
# Installing
1. Check out the git repo.
2. Install dependency

    `pip install -r requirements.txt`

3. Build a distribution

    `python setup.py sdist`

4. Install locally

    `pip install dist/icinga2-exporter-X.Y.Z.tar.gz`


# Running

## Development

Run the `icinga2-exporter` with the built-in Quart webserver:

    python -m  icinga2_exporter -f config.yml

To see all options:

    python -m  icinga2_exporter -h

## Production with hypercorn as ASGI continer 

Hypercorn is the recommended ASGI container for Quart. Install hypercorn with: 

    pip install hypercorn

Running with default config.yml. The default location is current directory

    hypercorn "icinga2_exporter.main:create_app()

Set the path to the configuration file.

    hypercorn "icinga2_exporter.main:create_app('/etc/icinga2-exporter/config.yml')"

> Port 8000 is the default port for hypercorn. For more configuration for hypercorn please visit 
> https://pgjones.gitlab.io/hypercorn/index.html

## Test the connection

Check if exporter is working.

    curl -s http://localhost:9638/health

Get metrics for a host where target is a host, `host_name` that exists in icinga2

    curl -s http://localhost:9638/metrics?target=google.se

# System requirements

Python 3.

For required packages please review `requirements.txt`.


