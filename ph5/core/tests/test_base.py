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
    def setUp(self):
        # enable propagating to higher loggers
        logger.propagate = 1
        # disable writing log to console
        logger.removeHandler(ch)
        # add StringIO handler to prevent message "No handlers could be found"
        log = StringIO()
        self.newch = logging.StreamHandler(log)
        logger.addHandler(self.newch)

    def tearDown(self):
        # disable propagating to higher loggers
        logger.propagate = 0
        # revert logger handler
        logger.removeHandler(self.newch)
        logger.addHandler(ch)


class TempDirTestCase(LogTestCase):

    def setUp(self):
        """
        create tmpdir
        """
        super(TempDirTestCase, self).setUp()
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp(dir=self.home + "/ph5/test_data/")
        os.chdir(self.tmpdir)

    def tearDown(self):
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
        super(TempDirTestCase, self).tearDown()