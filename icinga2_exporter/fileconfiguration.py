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

import yaml


def read_config(config_file: str) -> dict:
    """
    Read configuration file
    :param config_file:
    :return:
    """
    config = {}
    try:
        with open(config_file, 'r') as ymlfile:
            config = yaml.load(ymlfile, Loader=yaml.SafeLoader)
    except (FileNotFoundError, IOError):
        print("Config file {} not found".format(config_file))
        exit(1)
    except (yaml.YAMLError, yaml.MarkedYAMLError) as err:
        print("Error will reading config file - {}".format(err))
        exit(1)

    return config
