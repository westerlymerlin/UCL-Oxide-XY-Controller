"""
Flask web application for Raspberry Pi system monitoring and control.

This module provides a web interface and API endpoints for monitoring and controlling
a Raspberry Pi system. It includes features for:
- System status monitoring (CPU temperature, running threads)
- Log viewing (Application, Gunicorn, System logs)
- RESTful API endpoints with authentication
- Real-time status updates via JavaScript

The application runs on Gunicorn when deployed on Raspberry Pi and includes
various endpoints for both web interface and programmatic access.

Routes:
    / : Main status page
    /statusdata : JSON endpoint for live status updates
    /api : Protected API endpoint for system control
    /pylog : Application log viewer
    /guaccesslog : Gunicorn access log viewer
    /guerrorlog : Gunicorn error log viewer
    /syslog : System log viewer

Authentication:
    API endpoints require a valid API key passed in the 'Api-Key' header.
"""
import subprocess
from threading import enumerate as enumerate_threads
from flask import Flask, render_template, jsonify, request
from steppercontrol import statusmessage, parsecontrol
from app_control import VERSION, settings
from logmanager import logger

app = Flask(__name__)
logger.info('Starting %s web app version %s', settings['app-name'], VERSION)
logger.info('Api-Key = %s', settings['api-key'])


def read_log_from_file(file_path):
    """Read a log from a file and reverse the order of the lines so newest is at the top"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return list(reversed(lines))


def read_cpu_temperature():
    """Read the CPU temperature and teturns in in Celcius"""
    with open(settings['cputemp'], 'r', encoding='utf-8') as f:
        log = f.readline()
    return round(float(log) / 1000, 1)


def threadlister():
    """Get a list of all threads running"""
    appthreads = []
    for appthread in enumerate_threads():
        appthreads.append([appthread.name, appthread.native_id])
    return appthreads


@app.route('/')
def index():
    """Main web status page"""
    return render_template('index.html', version=VERSION, appname=settings['app-name'], threads=threadlister())

@app.route('/statusdata', methods=['GET'])
def statusdata():
    """Status data read by javascript on default website so the page shows near live values"""
    ctrldata = statusmessage()
    ctrldata['cputemperature'] = read_cpu_temperature()
    return jsonify(ctrldata), 201


@app.route('/api', methods=['POST'])
def api():
    """API Endpoint for programatic access - needs request data to be posted in a json file. Contains a check for a
    valid API key."""
    try:
        logger.debug('API headers: %s', request.headers)
        logger.debug('API request: %s', request.json)
        if 'Api-Key' in request.headers.keys():  # check api key exists
            if request.headers['Api-Key'] == settings['api-key']:  # check for correct API key
                item = request.json['item']
                command = request.json['command']
                return jsonify(parsecontrol(item, command)), 201
            logger.warning('API: access attempt using an invalid token from %s', request.headers[''])
            return 'access token(s) unuthorised', 401
        logger.warning('API: access attempt without a token from  %s', request.headers['X-Forwarded-For'])
        return 'access token(s) incorrect', 401
    except KeyError:
        return "badly formed json message", 401



@app.route('/pylog')
def showplogs():
    """Show the Application log web page"""
    cputemperature = read_cpu_temperature()
    logs = read_log_from_file(settings['logfilepath'])
    return render_template('logs.html', rows=logs, log='Application log',
                           cputemperature=cputemperature, appname=settings['app-name'], version=VERSION)


@app.route('/guaccesslog')
def showgalogs():
    """"Show the Gunicorn Access Log web page"""
    cputemperature = read_cpu_temperature()
    logs = read_log_from_file(settings['gunicornpath'] + 'gunicorn-access.log')
    return render_template('logs.html', rows=logs, log='Gunicorn Access Log',
                           cputemperature=cputemperature, appname=settings['app-name'], version=VERSION)


@app.route('/guerrorlog')
def showgelogs():
    """"Show the Gunicorn Errors Log web page"""
    cputemperature = read_cpu_temperature()
    logs = read_log_from_file(settings['gunicornpath'] + 'gunicorn-error.log')
    return render_template('logs.html', rows=logs, log='Gunicorn Error Log',
                           cputemperature=cputemperature, appname=settings['app-name'], version=VERSION)


@app.route('/syslog')
def showslogs():
    """Show the last 2000 lines from the system log on a web page"""
    cputemperature = read_cpu_temperature()
    log = subprocess.Popen('/bin/journalctl -n 2000', shell=True,
                           stdout=subprocess.PIPE).stdout.read().decode(encoding='utf-8')
    logs = log.split('\n')
    logs.reverse()
    return render_template('logs.html', rows=logs, log='System Log', cputemperature=cputemperature,
                           version=VERSION, appname=settings['app-name'])



if __name__ == '__main__':
    app.run()
