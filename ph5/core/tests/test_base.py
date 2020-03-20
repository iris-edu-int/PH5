import os
import shutil
import tempfile
import unittest
import logging
from StringIO import StringIO

from ph5 import logger, ch
from ph5.core import experiment


def initialize_ex(nickname, path, editmode=False):
    ex = experiment.ExperimentGroup(nickname=nickname, currentpath=path)
    ex.ph5open(editmode)
    ex.initgroup()
    return ex


class LogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # enable propagating to higher loggers
        logger.propagate = 1
        # disable writing log to console
        logger.removeHandler(ch)
        # add StringIO handler to prevent message "No handlers could be found"
        log = StringIO()
        cls.newch = logging.StreamHandler(log)
        logger.addHandler(cls.newch)

    @classmethod
    def tearDownClass(cls):
        # disable propagating to higher loggers
        logger.propagate = 0
        # revert logger handler
        logger.removeHandler(cls.newch)
        logger.addHandler(ch)


class TempDirTestCase(unittest.TestCase):

    def setUp(self):
        """
        create tmpdir
        """
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp(dir=self.home + "/ph5/test_data/")
        os.chdir(self.tmpdir)
        self.debug()

    def tearDown(self):
        self.debug()
        self.find_all_file_loggers()
        if self._resultForDoCleanups.wasSuccessful():
            try:
                shutil.rmtree(self.tmpdir)
            except Exception as e:
                print("Cannot remove %s due to the error:%s" %
                      (self.tmpdir, str(e)))
        else:
            errmsg = "%s has FAILED. Inspect files created in %s." \
                % (self._testMethodName, self.tmpdir)
            print(errmsg)

        os.chdir(self.home)

    def debug(self):
        print()
        print('id:     {}'.format(self.id))
        print('tmpdir: {}'.format(self.tmpdir))
        print('cwd:    {}'.format(os.getcwd()))
        print('home:   {}'.format(self.home))

    def find_all_file_loggers(self):
        for k,v in  logging.Logger.manager.loggerDict.items()  :
            # print('+ [%s] {%s} ' % (str.ljust( k, 20)  , str(v.__class__)[8:-2]) ) 
            if not isinstance(v, logging.PlaceHolder):
                for h in v.handlers :
                    if isinstance(h, logging.FileHandler):
                        print('+ [%s] {%s} ' % (str.ljust( k, 20)  , str(v.__class__)[8:-2]) ) 
                        print('     +++',str(h.__class__)[8:-2] )