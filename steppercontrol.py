"""
Main controller classes
"""
import threading
from time import sleep
import os
from threading import Timer
from RPi import GPIO
from logmanager import logger
from app_control import settings, writesettings


class StepperClass:
    """Class to control a stepper motor"""
    def __init__(self, direction, a, aa, b, bb, limmax, limmin):
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
        self.positionsetting = '%sposition' % direction
        self.upperlimitsetting = '%s-max' % direction
        self.lowerlimitsetting = '%s-min' % direction
        self.position = settings[self.positionsetting]
        self.upperlimit = settings[self.upperlimitsetting]
        self.lowerlimit = settings[self.lowerlimitsetting]
        self.maxswitch = 0
        self.minswitch = 0
        self.sequence = 0
        self.pulsewidth = 0.025
        self.moving = False
        self.calibrating = False
        GPIO.setup([a, aa, b, bb], GPIO.OUT)
        GPIO.setup(limmax, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Max limit switch
        GPIO.setup(limmin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Min Limit Switch
        readerthread = threading.Timer(1,self.readswitches)
        readerthread.name = '%s switches reader' %direction
        readerthread.start()


    def readswitches(self):
        """Read the switch values"""
        while True:
            self.maxswitch = GPIO.input(self.channelupperlimit)
            self.minswitch = GPIO.input(self.channellowerlimit)
            sleep(0.5)


    def current(self):
        """Return current sequence, used for debugging"""
        return self.seq[self.sequenceindex]

    def movenext(self, fine=False):
        """Move +1 step"""
        stepincrement = 1
        if self.position < self.upperlimit:
            self.sequenceindex += stepincrement
            if self.sequenceindex > 7:
                self.sequenceindex = 0
            self.output(self.seq[self.sequenceindex])
            self.position += stepincrement
            sleep(self.pulsewidth)
            if not fine:
                self.output([0, 0, 0, 0])
            # print('Move %s' % stepincrement)

    def moveprevious(self, fine=False):
        """Move -1 step"""
        stepincrement = -1
        if self.position > self.lowerlimit:
            self.sequenceindex += stepincrement
            if self.sequenceindex < 0:
                self.sequenceindex = 7
            self.output(self.seq[self.sequenceindex])
            self.position += stepincrement
            sleep(self.pulsewidth)
            if not fine:
                self.output([0, 0, 0, 0])
            # print('Move %s' % stepincrement)

    def updateposition(self):
        """write the position to the settings file"""
        settings[self.positionsetting] = self.position
        writesettings()

    def stop(self):
        """Stop moving"""
        self.moving = False
        self.sequence = self.sequence + 1
        logger.info('%s stepper stopped, position = %s', self.axis, self.position)
        self.output([0, 0, 0, 0])

    def move(self, steps):
        """Move **steps** at full speed"""
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
            sleep(self.pulsewidth * 2)
        self.updateposition()
        self.stop()


    def moveslow(self, steps):
        """Moce **steps** slowly"""
        self.sequence = self.sequence + 1
        self.moving = True
        while steps != 0 and self.moving:
            if steps > 0:
                steps -= 1
                self.movenext(True)
                print(self.seq[self.sequenceindex])
            else:
                steps += 1
                self.moveprevious(True)
                print(self.seq[self.sequenceindex])
            sleep(1)

    def moveto(self, target):
        """Move the motor to a specific target value on the ADC"""
        self.moving = True
        self.sequence = self.sequence + 1
        seq = self.sequence
        if self.lowerlimit <= target <= self.upperlimit:
            stepcounter = 0
            delta = target - self.position
            # print('delta = %s' % delta)
            while self.position != target and seq == self.sequence:
                stepcounter += 1
                if delta > 0:
                    if abs(target - self.position) < 10:
                        self.movenext(True)  # fine steps
                        if self.position > target:
                            self.moveprevious(True)
                            self.stop()
                            return
                    else:
                        self.movenext()
                else:
                    if abs(target - self.position) < 10:
                        self.moveprevious(True)   # fine steps
                        if self.position < target:
                            self.movenext(True)
                            self.stop()
                            return
                    else:
                        self.moveprevious()
                difference = abs(target - self.position)
                # print('difference %f' % difference )
                if difference > 5:
                    sleep(self.pulsewidth * 2)
                else:
                    sleep(0.3)
        self.moving = False

    def output(self, channels):
        """Output the value to thE coils on the stepper"""
        GPIO.output(self.channela, channels[0])
        GPIO.output(self.channelaa, channels[1])
        GPIO.output(self.channelb, channels[2])
        GPIO.output(self.channelbb, channels[3])

def statusmessage():
    """Return the psotion status to the web page"""
    statuslist = ({'xpos': stepperx.position, 'ypos': steppery.position, 'xminswitch': stepperx.minswitch,
                   'xmaxswitch': stepperx.maxswitch, 'yminswitch': steppery.minswitch,
                   'ymaxswitch': steppery.maxswitch})
    return statuslist

def apistatus():
    """Return the ststus as a json message for the api"""
    statuslist = ({'xpos': stepperx.position, 'xmoving': stepperx.moving, 'ypos': steppery.position,
                   'ymoving': steppery.moving })
    return statuslist

def parsecontrol(item, command):
    """Parser that recieves messages from the API or web page posts and directs messages to the correct function"""
    try:
        if item != 'getxystatus':
            logger.info('%s : %s ', item, command)
        if item == 'xmove':
            timerthread = Timer(1, lambda: stepperx.move(command))
            timerthread.name = 'xmove thread'
            timerthread.start()
        elif item == 'ymove':
            timerthread = Timer(1, lambda: steppery.move(command))
            timerthread.name = 'ymove thread'
            timerthread.start()
        elif item == 'xmoveto':
            timerthread = Timer(1, lambda: stepperx.moveto(command))
            timerthread.name = 'ymove to %s thread' % command
            timerthread.start()
        elif item == 'ymoveto':
            timerthread = Timer(1, lambda: steppery.moveto(command))
            timerthread.name = 'ymove to %s thread' % command
            timerthread.start()
        elif item == 'output':
            stepperx.output(command)
            steppery.output(command)
        elif item == 'restart':
            if command == 'pi':
                logger.warning('Restart command recieved: system will restart in 15 seconds')
                timerthread = Timer(15, reboot)
                timerthread.start()
        # print('X = %s, Y = %s' % (stepperx.listlocation(), steppery.listlocation()))
    except ValueError:
        logger.error('incorrect json message')
    except IndexError:
        logger.error('bad valve number')


def runselftest():
    """Run a selftest defined in the **testsequence** method"""
    logger.info('Stopping both motors prior to testing')
    stepperx.stop()
    steppery.stop()
    logger.info('Starting test sequence in 10 seconds')
    timerthread = Timer(10, testsequence)
    timerthread.name = 'selftest thread'
    timerthread.start()

def reboot():
    """API call to reboot the Raspberry Pi"""
    logger.warning('System is restarting now')
    os.system('sudo reboot')

def testsequence():
    """test sequence for the x-y table"""
    logger.info('Self test started ************************************')
    logger.info('Starting channel x tests')
    logger.info('Setting all x channels to 1 for 5 seconds')
    stepperx.output([1, 1, 1, 1])
    sleep(5)
    logger.info('Setting all x channels to 0 for 5 seconds')
    stepperx.output([0, 0, 0, 0])
    sleep(5)
    logger.info('step x 10 steps forward')
    stepperx.moveslow(10)
    stepperx.output([0, 0, 0, 0])
    sleep(5)
    logger.info('step x 10 steps backward')
    stepperx.moveslow(-10)
    stepperx.output([0, 0, 0, 0])
    sleep(5)
    logger.info('Finished Channel x tests')
    logger.info('Starting channel y tests')
    logger.info('Setting all y channels to 1 for 5 seconds')
    steppery.output([1, 1, 1, 1])
    sleep(5)
    logger.info('Setting all y channels to 0 for 5 seconds')
    steppery.output([0, 0, 0, 0])
    sleep(5)
    logger.info('step y 10 steps forward')
    steppery.moveslow(10)
    steppery.output([0, 0, 0, 0])
    sleep(5)
    logger.info('step y 10 steps backward')
    steppery.moveslow(-10)
    steppery.output([0, 0, 0, 0])
    sleep(5)
    logger.info('Finished Channel y tests')
    logger.info('Self test ended ************************************')


logger.info("xy controller started")
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
stepperx = StepperClass('x', settings['x-a-gpio-pin'], settings['x-aa-gpio-pin'],settings['x-b-gpio-pin'],
                        settings['x-bb-gpio-pin'], settings['x-max-gpio-pin'], settings['x-min-gpio-pin'])
steppery = StepperClass('y', settings['y-a-gpio-pin'], settings['y-aa-gpio-pin'],settings['y-b-gpio-pin'],
                        settings['y-bb-gpio-pin'], settings['y-max-gpio-pin'], settings['y-min-gpio-pin'])
logger.info("xy controller ready")
