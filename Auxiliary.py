__author__ = 'shahargino'


from sys import exit
from datetime import datetime


class Auxiliary(object):
    """This class comprises general auxiliary methods, such as printing, error message, etc."""

    # ----------------------------------------------------------------------------------------
    def __init__(self, env, verbose):
        self.env = env
        self.verbose = verbose

    # ----------------------------------------------------------------------------------------
    def debug(self, tag, msg):
        if self.verbose: #and 'CPU' in tag and 'RD' not in tag and 'RD' not in msg:
            print("[%.02f ns] [%s] %s" % (self.env.now, tag, msg))

    # ----------------------------------------------------------------------------------------
    def message(self, tag, msg):
        print("[%.02f ns] [%s] %s" % (self.env.now, tag, msg))

    # ----------------------------------------------------------------------------------------
    def timestamp(self, tag, msg):
        time_str = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        print("="*70)
        print("[%.02f ns] [%s] %s - at %s" % (self.env.now, tag, msg, time_str))
        print("="*70)

    # ----------------------------------------------------------------------------------------
    def error(self, tag, msg):
        print("[%.02f ns] [ERROR] %s: %s" % (self.env.now, tag, msg))
        exit()
