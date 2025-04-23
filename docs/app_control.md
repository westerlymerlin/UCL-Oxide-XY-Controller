# Contents for: app_control

* [app\_control](#app_control)
  * [random](#app_control.random)
  * [json](#app_control.json)
  * [datetime](#app_control.datetime)
  * [VERSION](#app_control.VERSION)
  * [initialise](#app_control.initialise)
  * [generate\_api\_key](#app_control.generate_api_key)
  * [writesettings](#app_control.writesettings)
  * [readsettings](#app_control.readsettings)
  * [loadsettings](#app_control.loadsettings)
  * [settings](#app_control.settings)

<a id="app_control"></a>

# app\_control

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

<a id="app_control.random"></a>

## random

<a id="app_control.json"></a>

## json

<a id="app_control.datetime"></a>

## datetime

<a id="app_control.VERSION"></a>

#### VERSION

<a id="app_control.initialise"></a>

#### initialise

```python
def initialise()
```

Setup the settings dict structure with default values

<a id="app_control.generate_api_key"></a>

#### generate\_api\_key

```python
def generate_api_key(key_len)
```

generate a new random api-key

<a id="app_control.writesettings"></a>

#### writesettings

```python
def writesettings()
```

Write settings to a json file

<a id="app_control.readsettings"></a>

#### readsettings

```python
def readsettings()
```

Read the json file

<a id="app_control.loadsettings"></a>

#### loadsettings

```python
def loadsettings()
```

Replace the default settings with those from the json files, if a setting is not in the json file (e.g. it is a
 new feature setting) then retain the default value and write that to the json file. If the api-key is the default
value then generate a new key and save it.

<a id="app_control.settings"></a>

#### settings

