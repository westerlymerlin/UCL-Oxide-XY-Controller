"""
Stepper motor control interface for Raspberry Pi hardware control system.

This module provides functionality to control and monitor stepper motors connected
to the Raspberry Pi. It handles both status reporting and command parsing for
motor control operations.

Functions:
    statusmessage() -> dict:
        Returns the current status of all stepper motors in the system.
        The status includes position, state, and other relevant motor parameters.
        Returns:
            dict: Current status of the stepper motors

    parsecontrol(item: str, command: str) -> dict:
        Parses and executes control commands for specified stepper motor.

        Args:
            item (str): The identifier of the stepper motor to control
            command (str): The control command to execute

        Returns:
            dict: Result of the control operation including status and any error messages

Note:
    This module interfaces directly with hardware components and should be used
    with appropriate driver board to prevent mechanical issues.


"""
import threading
from time import sleep
import os
from threading import Timer
from RPi import GPIO
from logmanager import logger
from app_control import settings, writesettings


class StepperClass:
    """
    Class to manage and control a stepper motor using GPIO and threading.

    This class provides methods to move, stop, calibrate, and manage the position
    of a stepper motor. It uses GPIO pins for hardware interaction and threading
    for continuous monitoring of limit switches and movement control. The class
    ensures safe operation by respecting hardware-defined movement limits and includes
    calibration capabilities to define the valid range of motion. The settings
    configuration is used for storing and updating operational parameters.

    """
    def __init__(self, direction, a, aa, b, bb, limmax, limmin, moveled):
        self.axis = direction
        self.seq = [[1, 0, 1, 0],
                    [1, 0, 0, 0],
                    [1, 0, 0, 1],
                    [0, 0, 0, 1],
                    [0, 1, 0, 1],
                    [0, 1, 0, 0],
                    [0, 1, 1, 0],
                    [0, 0, 1, 0]
                    ]
        self.channela = a
        self.channelaa = aa
        self.channelb = b
        self.channelbb = bb
        self.sequenceindex = 0
        self.channelupperlimit = limmax
        self.channellowerlimit = limmin
        self.channelmoveled = moveled
        self.positionsetting = '%sposition' % direction
        self.upperlimitsetting = '%s-max' % direction
        self.lowerlimitsetting = '%s-min' % direction
        self.position = settings[self.positionsetting]
        self.upperlimit = settings[self.upperlimitsetting]
        self.lowerlimit = settings[self.lowerlimitsetting]
        self.maxswitch = 0
        self.minswitch = 0
        self.sequence = 0
        self.pulsewidth = settings['stepper-pulse-width']
        self.moving = False
        self.calibrating = False
        GPIO.setup([a, aa, b, bb, moveled], GPIO.OUT)
        self.moveled_pwm = GPIO.PWM(moveled, 1)
        GPIO.setup(limmax, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Max limit switch
        GPIO.setup(limmin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Min Limit Switch
        readerthread = threading.Timer(1, self.__read_switches)
        readerthread.name = '%s limit switches reader' %direction
        readerthread.start()


    def __read_switches(self):
        """
        Continuously monitors the state of the minimum and maximum limit switches and updates
        the corresponding attributes. Reacts to changes in the limit switch states by logging
        events and optionally stopping movement. Also manages the LED indicating movement
        activity.

        :raises RuntimeError: If the GPIO library encounters an error while reading input values
            or controlling PWM components.
        """
        minswich = 1
        maxswitch = 1
        moving = 0
        while True:
            self.maxswitch = GPIO.input(self.channelupperlimit)
            self.minswitch = GPIO.input(self.channellowerlimit)
            if minswich != self.minswitch:
                minswich = self.minswitch
                if minswich == 0:
                    logger.info('Min limit switch %s reached', self.axis)
                    if not self.calibrating:
                        self.stop()
            if maxswitch != self.maxswitch:
                maxswitch = self.maxswitch
                if maxswitch == 0:
                    logger.info('Max limit switch %s reached', self.axis)
                    if not self.calibrating:
                        self.stop()
            if moving != self.moving:
                moving = self.moving
                if self.moving:
                    self.moveled_pwm.start(10)
                else:
                    self.moveled_pwm.stop()
            sleep(0.5)


    def current(self):
        """Return current sequence, only used for debugging"""
        return self.seq[self.sequenceindex]

    def movenext(self):
        """Move +1 step towards the maximum, if the maximum value has been reached it will not move further"""
        stepincrement = 1
        if (self.position < self.upperlimit) or self.calibrating:
            if self.maxswitch == 1 or self.calibrating:
                self.sequenceindex += stepincrement
                if self.sequenceindex > 7:
                    self.sequenceindex = 0
                self.output(self.seq[self.sequenceindex])
                self.position += stepincrement
                sleep(self.pulsewidth)

    def moveprevious(self):
        """Move -1 step towards the minimum, if the minimum value has been reached it will not move further."""
        stepincrement = -1
        if (self.position > self.lowerlimit) or self.calibrating:
            if self.minswitch == 1 or self.calibrating:
                self.sequenceindex += stepincrement
                if self.sequenceindex < 0:
                    self.sequenceindex = 7
                self.output(self.seq[self.sequenceindex])
                self.position += stepincrement
                sleep(self.pulsewidth)


    def updateposition(self):
        """write the stepper position to the settings file"""
        settings[self.positionsetting] = self.position
        writesettings()

    def stop(self):
        """Stop the stepper motor and set the coils to 0, also update the position of the stepper and write to
        the settings file"""
        self.moving = False
        self.sequence = self.sequence + 1
        logger.info('%s stepper stopped, position = %s', self.axis, self.position)
        self.output([0, 0, 0, 0])

    def move(self, steps):
        """Move **n steps** at full speed"""
        self.sequence = self.sequence + 1
        self.moving = True
        if steps == 0:
            self.stop()
        while steps != 0 and self.moving:
            if steps > 0:
                steps -= 1
                self.movenext()
            else:
                steps += 1
                self.moveprevious()
        self.updateposition()
        self.stop()


    def moveslow(self, steps):
        """Move **steps** slowly"""
        self.sequence = self.sequence + 1
        self.moving = True
        while steps != 0 and self.moving:
            if steps > 0:
                steps -= 1
                self.movenext()
            else:
                steps += 1
                self.moveprevious()
            sleep(1)
        self.stop()
        self.moving = False

    def moveto(self, target):
        """
        Moves the axis to the specified target position within its limits.

        This method initiates the movement process for the axis motor to reach the
        desired target position. The movement continues as long as the motor is in
        motion and has not been interrupted by external control. The method checks
        if the target position is within the specified range of lower and upper limits
        and adjusts the motor position incrementally. It stops the motion and updates
        the motor status accordingly when the target is reached or the sequence changes.

        :param target: Desired position to move the axis to.
        :type target: int or float
        :return: None
        """
        self.moving = True
        self.sequence = self.sequence + 1
        seq = self.sequence
        if self.lowerlimit <= target <= self.upperlimit:
            stepcounter = 0
            delta = target - self.position
            # print('delta = %s' % delta)
            while self.position != target and seq == self.sequence and self.moving:
                stepcounter += 1
                if delta > 0:
                    self.movenext()
                else:
                    self.moveprevious()
                difference = abs(target - self.position)
                if difference < 10:
                    sleep(self.pulsewidth * 10)
        logger.info('%s Move to %s complete, position = %s', self.axis, target, self.position)
        self.stop()
        self.moving = False

    def output(self, channels):
        """Output the value to the coils on the stepper"""
        GPIO.output(self.channela, channels[0])
        GPIO.output(self.channelaa, channels[1])
        GPIO.output(self.channelb, channels[2])
        GPIO.output(self.channelbb, channels[3])

    def calibrate(self):
        """Run a calibration routine to find the man and max limit switches and reset the position of the stage. The
        routine will move the stepper backward as far as the minimum switch is triggered, it will then slowly move the
        stepper forward until the switch is just released. This position is then recorded as zero. The stepper will
        then be moved forward unti the maximum limit is triggeed, then move backward until the switch is released,
        this position (- 10 steps) is stored as the maximum value. The routine then calculates the centre position and
        moves the stepper to that position. When calibrating the read() method will not stop the motor when a limit
        switch is triggered"""
        self.calibrating = True
        logger.info('Starting Calibrating %s', self.axis)
        self.moving = True
        while self.minswitch == 1:
            self.moveprevious()
        while self.minswitch == 0:
            self.movenext()
            sleep(self.pulsewidth * 5)
        logger.info('Min limit reset, setting zero')
        self.position = 0
        while self.maxswitch == 1:
            self.movenext()
        while self.maxswitch == 0:
            self.moveprevious()
            sleep(self.pulsewidth * 5)
        logger.info('Max limit set to %s', self.position -10)
        self.upperlimit = self.position - 10
        settings[self.upperlimitsetting] = self.upperlimit
        self.updateposition()
        self.calibrating = False
        centre = int((self.upperlimit - self.lowerlimit) / 2)
        logger.info('Calibrating %s complete moving to centre', self.axis)
        self.moveto(centre)
        self.stop()
        self.updateposition()
        logger.info('Calibrating %s complete, position = %s', self.axis, self.position)

def statusmessage():
    """Return the psotion and stepper status in a format that can be read by the web page"""
    statuslist = ({'xpos': stepperx.position, 'ypos': steppery.position, 'xminswitch': stepperx.minswitch,
                   'xmaxswitch': stepperx.maxswitch, 'yminswitch': steppery.minswitch,
                   'ymaxswitch': steppery.maxswitch, 'stepperxa': GPIO.input(stepperx.channela),
                   'stepperxaa': GPIO.input(stepperx.channelaa), 'stepperxb': GPIO.input(stepperx.channelb),
                   'stepperxbb': GPIO.input(stepperx.channelbb), 'stepperya': GPIO.input(steppery.channela),
                   'stepperyaa': GPIO.input(steppery.channelaa), 'stepperyb': GPIO.input(steppery.channelb),
                   'stepperybb': GPIO.input(steppery.channelbb)})
    return statuslist

def apistatus():
    """Return the status as a json message for the api"""
    statuslist = ({'xpos': stepperx.position, 'xmoving': stepperx.moving, 'ypos': steppery.position,
                   'ymoving': steppery.moving })
    return statuslist


def updatesetting(newsetting): # must be a dict object
    """Update the settings variable and file with the new values from an api call"""
    if isinstance(newsetting, dict):
        for item in newsetting.keys():
            settings[item] = newsetting[item]
        writesettings()


def parsecontrol(item, command):
    """Parser that recieves messages from the API or web page posts and directs messages to the correct function:
    Valid messages are:
    getxystatus: returns the current position of the steppers
    (axis)move: moves the stepper axis by the number of steps specified
    (axix)moveto: moves the stepper axis to the position specified
    (axis)calibrate: calibrates the stepper axis
    calibrate-all: calibrates both axes
    output: sets the coils on the stepper to the value specified (used foir testing ta stepper motor
    getsettings: returns the current settings in a json format
    updatesetting: updates the settings file with the new values specified in a json object
    restart: restarts the raspberry pi
    """
    try:
        if item != 'getxystatus':
            logger.info('Request recieved {%s : %s}', item, command)
        else:
            return apistatus()
        if item == 'xmove':
            timerthread = Timer(0.1, lambda: stepperx.move(command))
            timerthread.name = 'xmove thread'
            timerthread.start()
            return apistatus()
        if item == 'ymove':
            timerthread = Timer(0.1, lambda: steppery.move(command))
            timerthread.name = 'ymove thread'
            timerthread.start()
            return apistatus()
        if item == 'xmoveto':
            timerthread = Timer(0.1, lambda: stepperx.moveto(command))
            timerthread.name = 'xmove to %s thread' % command
            timerthread.start()
            return apistatus()
        if item == 'ymoveto':
            timerthread = Timer(0.1, lambda: steppery.moveto(command))
            timerthread.name = 'ymove to %s thread' % command
            timerthread.start()
            return apistatus()
        if item == 'xcalibrate':
            timerthread = Timer(0.1, stepperx.calibrate)
            timerthread.name = 'x calibrating thread'
            timerthread.start()
            return apistatus()
        if item == 'ycalibrate':
            timerthread = Timer(0.1, steppery.calibrate)
            timerthread.name = 'y calibrating thread'
            timerthread.start()
            return apistatus()
        if item == 'calibrate-all':
            logger.info('Calibrating all axis')
            timerthread = Timer(0.1, steppery.calibrate)
            timerthread.name = 'y calibrating thread'
            timerthread.start()
            timerthread = Timer(0.1, steppery.calibrate)
            timerthread.name = 'y calibrating thread'
            timerthread.start()
            return apistatus()
        if item == 'output':
            stepperx.output(command)
            steppery.output(command)
            return apistatus()
        if item == 'updatesetting':
            logger.warning('parsecontrol Setting changed via api - %s', command)
            updatesetting(command)
            return settings
        if item == 'getsettings':
            return settings
        if item == 'restart':
            if command == 'pi':
                logger.warning('Restart command recieved: system will restart in 15 seconds')
                timerthread = Timer(15, reboot)
                timerthread.start()
            return {'command': 'rebooting'}
        return {'error': 'unknown command'}
    except ValueError:
        logger.error('incorrect json message')
        return {'error': 'incorrect json message'}
    except IndexError:
        logger.error('bad Item')
        return {'error': 'incorrect json message'}


def reboot():
    """API call to reboot the Raspberry Pi"""
    logger.warning('System is restarting now')
    os.system('sudo reboot')



logger.info("xy controller started")
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
stepperx = StepperClass('x', settings['x-a-gpio-pin'], settings['x-aa-gpio-pin'],settings['x-b-gpio-pin'],
                        settings['x-bb-gpio-pin'], settings['x-max-gpio-pin'], settings['x-min-gpio-pin'],
                        settings['x-moving-gpio-pin'])
steppery = StepperClass('y', settings['y-a-gpio-pin'], settings['y-aa-gpio-pin'],settings['y-b-gpio-pin'],
                        settings['y-bb-gpio-pin'], settings['y-max-gpio-pin'], settings['y-min-gpio-pin'],
                        settings['y-moving-gpio-pin'])
logger.info("xy controller ready")
