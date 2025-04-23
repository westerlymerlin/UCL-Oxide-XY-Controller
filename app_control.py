"""
Application control and configuration management for the Raspberry Pi control system.

This module manages core application configuration, settings, and version information
for the Flask-based control system. It handles loading and maintaining application-wide
settings that define crucial operational parameters.

Attributes:
    VERSION (str): The current version of the application
    settings (dict): Application-wide configuration dictionary containing:
        - app-name (str): Application identifier used in logging and display
        - api-key (str): Authentication key for API access control
        - cputemp (str): File path for CPU temperature readings
        - logfilepath (str): Path to application log file
        - gunicornpath (str): Base directory for Gunicorn log files

Note:
    This module is a central configuration point for the application and should
    be imported by other modules that need access to global settings or version
    information.

"""

import random
import json
from datetime import datetime

VERSION = '1.0.6'

def initialise():
    """Setup the settings dict structure with default values"""
    isettings = {'LastSave': '01/01/2000 00:00:01',
                 'api-key': 'change-me',
                 'app-name': 'Oxide X-Y Stage Controller',
                 'cputemp': '/sys/class/thermal/thermal_zone0/temp',
                 'gunicornpath': './logs/',
                 'logappname': 'XY-Control-Py',
                 'logfilepath': './logs/xycontrol.log',
                 'loglevel': 'INFO',
                 'stepper-pulse-width': 0.02,
                 'x-a-gpio-pin': 6,
                 'x-aa-gpio-pin': 12,
                 'x-b-gpio-pin': 13,
                 'x-bb-gpio-pin': 16,
                 'x-max': 1000,
                 'x-max-gpio-pin': 17,
                 'x-min': 10,
                 'x-min-gpio-pin': 27,
                 'x-moving-gpio-pin': 24,
                 'xposition': 500,
                 'y-a-gpio-pin': 19,
                 'y-aa-gpio-pin': 20,
                 'y-b-gpio-pin': 26,
                 'y-bb-gpio-pin': 21,
                 'y-max': 1000,
                 'y-max-gpio-pin': 23,
                 'y-min': 10,
                 'y-min-gpio-pin': 18,
                 'y-moving-gpio-pin': 25,
                 'yposition': 500
                 }
    return isettings


def generate_api_key(key_len):
    """generate a new random api-key"""
    allowed_characters = "ABCDEFGHJKLMNPQRSTUVWXYZ-+~abcdefghijkmnopqrstuvwxyz123456789"
    return ''.join(random.choice(allowed_characters) for _ in range(key_len))


def writesettings():
    """Write settings to a json file"""
    settings['LastSave'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    with open('settings.json', 'w', encoding='utf-8') as outfile:
        json.dump(settings, outfile, indent=4, sort_keys=True)

def readsettings():
    """Read the json file"""
    try:
        with open('settings.json', 'r', encoding='utf-8') as json_file:
            jsettings = json.load(json_file)
            return jsettings
    except FileNotFoundError:
        print('File not found')
        return {}

def loadsettings():
    """Replace the default settings with those from the json files, if a setting is not in the json file (e.g. it is a
     new feature setting) then retain the default value and write that to the json file. If the api-key is the default
    value then generate a new key and save it."""
    global settings
    settingschanged = False
    fsettings = readsettings()
    for item in settings.keys():
        try:
            settings[item] = fsettings[item]
        except KeyError:
            print('settings[%s] Not found in json file using default' % item)
            settingschanged = True
    if settings['api-key'] == 'change-me':  # the default value
        settings['api-key'] = generate_api_key(128)
        settingschanged = True
    if settingschanged:
        writesettings()


settings = initialise()
loadsettings()
