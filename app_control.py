"""
Settings module, reads the settings from a settings.json file. If it does not exist or a new setting
has appeared it will creat from the defaults in the initialise function.
"""
import random
import json
from datetime import datetime

VERSION = '1.0.0'

def initialise():
    """Setup the settings structure with default values"""
    isettings = {'LastSave': '01/01/2000 00:00:01',
                 'app-name': 'Oxide Valve Controler',
                 'api-key': 'change-me',
                 'logfilepath': './logs/xycontrol.log',
                 'logappname': 'XY-Control-Py',
                 'loglevel': 'INFO',
                 'gunicornpath': './logs/',
                 'cputemp': '/sys/class/thermal/thermal_zone0/temp',
                 'x-bb-gpio-pin': 16,
                 'x-b-gpio-pin': 13,
                 'x-aa-gpio-pin': 12,
                 'x-a-gpio-pin': 6,
                 'x-max': 190,
                 'x-max-gpio-pin': 17,
                 'x-min': 10,
                 'x-min-gpio-pin': 18,
                 'xposition': 100,
                 'y-bb-gpio-pin': 21,
                 'y-b-gpio-pin': 26,
                 'y-aa-gpio-pin': 20,
                 'y-a-gpio-pin': 19,
                 'y-max': 190,
                 'y-max-gpio-pin': 23,
                 'y-min': 10,
                 'y-min-gpio-pin': 27,
                 'yposition': 100
                 }
    return isettings


def generate_api_key(key_len):
    """generate a new api key"""
    allowed_characters = "ABCDEFGHJKLMNPQRSTUVWXYZ-+~abcdefghijkmnopqrstuvwxyz123456789"
    return ''.join(random.choice(allowed_characters) for _ in range(key_len))


def writesettings():
    """Write settings to json file"""
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
    """Replace the default settings with thsoe from the json files"""
    global settings
    settingschanged = False
    fsettings = readsettings()
    for item in settings.keys():
        try:
            settings[item] = fsettings[item]
        except KeyError:
            print('settings[%s] Not found in json file using default' % item)
            settingschanged = True
    if settings['api-key'] == 'change-me':
        settings['api-key'] = generate_api_key(128)
        settingschanged = True
    if settingschanged:
        writesettings()


settings = initialise()
loadsettings()
