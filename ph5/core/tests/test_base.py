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

    def tearDown(self):
        file_loggers = self.find_all_file_loggers()
        if file_loggers:
            # remove all file handlers
            for l, h in self.find_all_file_loggers():
                l.removeHandler(h)
        super(LogTestCase, self).tearDown()

    @staticmethod
    def find_all_file_loggers():
        file_logger_handlers = list()
        for k, v in logging.Logger.manager.loggerDict.items():
            if not isinstance(v, logging.PlaceHolder):
                for h in v.handlers:
                    if isinstance(h, logging.FileHandler):
                        file_logger_handlers.append((logging.getLogger(k), h))
        return file_logger_handlers


class TempDirTestCase(unittest.TestCase):
    total_error_failure = 0

    def setUp(self):
        """
        create tmpdir
        """
        self.home = os.getcwd()
        self.tmpdir = tempfile.mkdtemp(
            dir=os.path.join(self.home, "ph5/test_data/"))
        os.chdir(self.tmpdir)
        self.addCleanup(os.chdir, self.home)
        super(TempDirTestCase, self).setUp()

    def tearDown(self):
        super(TempDirTestCase, self).tearDown()
        current_total_error_failure = len(self._resultForDoCleanups.errors) + \
            len(self._resultForDoCleanups.failures)

        if current_total_error_failure == TempDirTestCase.total_error_failure:
            try:
                shutil.rmtree(self.tmpdir)
            except Exception as e:
                print("Cannot remove %s due to the error:%s" %
                      (self.tmpdir, str(e)))
        else:
            errmsg = "%s has FAILED. Inspect files created in %s." \
                % (self._testMethodName, self.tmpdir)
            print(errmsg)
            TempDirTestCase.total_error_failure = current_total_error_failure
        os.chdir(self.home)
