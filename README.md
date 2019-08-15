icinga2-exporter
-----------------------

# Overview 

The cinga2-exporter utilize Icinga2 API to fetch service based performance data and publish it in a way that lets prometheus scrape the 
performance data as metrics.

Benefits:

- Enable advanced queries and aggregation on timeseries
- Promethues based alerting rules 
- Grafana graphing
- Utilize investments with Icinga2 of collecting metrics 


# Metrics naming
## Metric names
Metrics that is scraped with the icinga2-exporter will have the following name structure:
 
    icinga2_<check_command>_<perfname>_<unit>

> The icinga2 prefix can be changed by the configuration
> Unit is only added if it exists on perfromance data

Example from check command `check_ping` will result in two metrics: 
    
    icinga2_ping_rta_seconds
    icinga2_ping_pl_ratio

## Metric labels
The icinga2-exporter adds a number of labels to each metrics: 

- host - is the `host_name` in icinga2
- service - is the `display_name` in icinga2

Optional icinga2-exporter can be configured to add specific custom variables configured on the host. 
> Icinga2 support custom varaibles that can be complex data structures - but that is NOT currently supported 

> Labels created from custom variables are all transformed to lowercase. 

### Icinga2 performance metrics name to labels
As describe above the default naming of the promethues name is:

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
So if the check command is `disk` the promethues metrics will have a format like, depending on other custom variables :

    icinga2_disk_bytes{hostname="icinga2", service="disk", os="Docker", mount="/var/lib/icinga2"} 48356130816.0
    
If we did not make this translation we would got the following:

    icinga2_disk_slashvarslashibslashicinga2_bytes{hostname="icinga2", service="disk", os="Docker"} 48356130816.0
    
 Which is not good from a cardinality point of view.
 

# Configuration
## icinga2-exporter
All configuration is made in the config.yml file.

Example:
```yaml

# Port can be overridden by using -p if running development flask
#port: 963X

icinga2:
  # The url to the icinga2 server
  url: https://127.0.0.1:5665
  user: root
  passwd: cf593406ffcfd2ef
  # All prometheus metrics will be prefixed with this string
  metric_prefix: icinga2
  # Example of custom vars that should be added as labels and how to be translated
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
        label: mount

logger:
  # Path and name for the log file. If not set send to stdout
  logfile: /var/tmp/icinga2-exporter.log
  # Log level
  level: INFO
```

> When running with gunicorn the port is selected by gunicorn

# Logging
The log stream is configure in the above config. If `logfile` is not set the logs will go to stdout.

Logs are formatted as json so its easy to store logs in log servers like Loki and Elasticsearch. 

# Prometheus configuration
Prometheus can be used with static configuration or with dynamic file discovery using the project [icinga2-promdiscovery](https://bitbucket.org/opsdis/icinga2-promdiscovery)

Please add the the job to the scrape_configs in prometheus.yml.

> The target is the `host_name` configured in icinga2.

## Static config
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
        replacement: localhost:963X

```

## File discovery config for usage with `icinga2-promdiscovery`

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
        replacement: localhost:963X

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
## Development with flask built in webserver 

    python -m  icinga2_exporter -f config.yml

The switch -p enable setting of the port.
    
## Production with gunicorn 
Running with default config.yml. The default location is current directory

    gunicorn --access-logfile /dev/null -w 4 "wsgi:create_app()"
    
Set the path to the configuration file.

    gunicorn --access-logfile /dev/null -w 4 "wsgi:create_app('/etc/icinga2-exporter/config.yml')" 

> Port for gunicorn is default 8000, but can be set with -b, e.g. `-b localhost:963X`

## Test the connection 

Check if exporter is working. 

    curl -s http://localhost:963X/health

Get metrics for a host where target is a host, `host_name` that exists in icinga2

    curl -s http://localhost:963X/metrics?target=google.se

# System requierments
Python 3

For required packages please review `requirements.txt`
