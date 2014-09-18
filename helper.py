import datetime
import math
import logging
import logging.handlers
import os
import re
import sys
import signal


__author__ = 'spance'
__app_full__ = 'GmailNotification'
__app__ = 'GNoti'

reMail = re.compile(r'[\w.+_\-]+@gmail.com')
reUrl = re.compile('^https?://.*')


def getLogger(name):
    """Get logging.Logger instance with GmailNotification logger name convention
    """
    if "." in name:
        name = "%s.%s" % (__app__, name.rpartition(".")[-1])
    else:
        name = "%s.%s" % (__app__, name)
    return logging.getLogger(name)


def signalHandler(sig, frame):
    # the inconsistent python exception mechanism is a torment.
    # the KeyboardInterrupt was transmitted to anywhere of stack.
    os.kill(os.getpid(), signal.SIGTERM)


signal.signal(signal.SIGINT, signalHandler)


def initLog(target):
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    try:
        os.chdir(appPath())
        # if Target is a directory, check and create when not exists.
        preparePath(target)
        open(target, "a").close()
        fileHandler = logging.handlers.RotatingFileHandler(target, maxBytes=10 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s %(name)-24s[%(process)d]: %(levelname)-7s %(message)s")
        screen_out = logging.StreamHandler(sys.stdout)
        for hd in [fileHandler, screen_out]:
            hd.setFormatter(formatter)
            log.addHandler(hd)
    except IOError:
        log.addHandler(logging.handlers.SysLogHandler(address='/dev/log'))
        log.exception("Unable to log into " + target)


def tryInput(prompt='', maxTry=3, allowBlank=False, re=None):
    var = ''
    try:
        while maxTry > 0:
            var = raw_input(prompt).strip()
            maxTry -= 1
            if allowBlank:
                break
            if var and (not re or (re and re.match(var))):
                break
    except (KeyboardInterrupt, EOFError) as e:
        pass
    return var


def preparePath(path):
    dirs = os.path.dirname(path)
    if dirs and not os.path.exists(dirs):
        os.makedirs(dirs)


def appPath():
    encoding = sys.getfilesystemencoding()
    return os.path.dirname(unicode(__file__, encoding))


class AvailedException(Exception):
    ''' AvailedException '''


class Timezone(datetime.tzinfo):
    def __init__(self, hours_offset=0, minutes_offset=0):
        super(Timezone, self).__init__()
        self.offset = hours_offset + minutes_offset / 60

    def utcoffset(self, dt):
        return datetime.timedelta(hours=self.offset)

    def dst(self, dt):
        return datetime.timedelta(hours=self.offset)

    def tzname(self, dt):
        fraction = abs(self.offset)
        fraction = (fraction - math.floor(fraction)) * 60
        return '%+03d:%02d' % (self.offset, fraction)