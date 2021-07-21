'''
Tests for fix_srm
'''
import os
import sys
import unittest
import logging
import time
import shutil

import tables
from mock import patch
from testfixtures import LogCapture

from ph5.utilities import fix_srm
from ph5.core import ph5api, timedoy, experiment
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase

tdoy = timedoy.TimeDOY(epoch=time.time())
yeardoy = "{0:04d}{1:03d}".format(tdoy.dtobject.year, tdoy.dtobject.day)


def count_smr_0_1(filename):
    # count 'sample_rate_multiplier_i=0' and 'sample_rate_multiplier_i=0'
    # in filename
    with open(filename, 'r') as file:
        content = file.read()
        smr0_no = content.count('sample_rate_multiplier_i=0')
        smr1_no = content.count('sample_rate_multiplier_i=1')
        return smr0_no, smr1_no


class TestFixSRM(TempDirTestCase, LogTestCase):
    def test_set_logger(self):
        # check if FileHandler's filename is fix_srm.log
        fix_srm.set_logger()
        self.assertEqual(len(fix_srm.LOGGER.handlers), 1)
        self.assertIsInstance(fix_srm.LOGGER.handlers[0],
                              logging.FileHandler)
        self.assertEqual(fix_srm.LOGGER.handlers[0].baseFilename,
                         os.path.join(self.tmpdir, 'fix_srm.log'))

    def test_fix_srm_in_kef(self):
        # smr0daskef has 9 smr=0 and 0 smr=1
        smr0daskef = os.path.join(
            self.home, 'ph5/test_data/metadata/Das_t_1X1111.0.0_SRM0.kef')
        smr0_no, smr1_no = count_smr_0_1(smr0daskef)
        self.assertEqual(smr0_no, 9)
        self.assertEqual(smr1_no, 0)
        fixedfilepath = os.path.join(self.tmpdir, 'fixedfile.kef')
        datapath = '/Experiment_g/Receivers_g/Das_g_1X1111/Das_t'
        # fix_srm_in_kef() will created fixedfiles.kef with 0 smr=0 and 9 smr=1
        with LogCapture() as log:
            fix_srm.fix_srm_in_kef(smr0daskef, fixedfilepath, datapath)
        self.assertTrue(os.path.isfile(fixedfilepath))
        smr0_no, smr1_no = count_smr_0_1(fixedfilepath)
        self.assertEqual(smr0_no, 0)
        self.assertEqual(smr1_no, 9)
        self.assertEqual(
            log.records[0].msg,
            'Convert 9 sample_rate_multiplier_i=0 to 1 in %s and save in %s.'
            % (smr0daskef, fixedfilepath)
        )


def init_ph5(srcdir, destdir):
    '''
    1. copy all ph5 files from srcdir to destdir
    2. create ph5object from ph5 file in destdir
    3. initiate T2K for use in fix_srm's function
    '''
    for basename in os.listdir(srcdir):
        if basename.endswith('.ph5'):
            pathname = os.path.join(srcdir, basename)
            shutil.copy2(pathname, destdir)
    ph5object = ph5api.PH5(
        path=destdir, nickname='master.ph5', editmode=True)
    fix_srm.init_T2K(ph5object)
    return ph5object


class TestFixSRM_PH5Object(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.ph5object.ph5close()
        super(TestFixSRM_PH5Object, self).tearDown()

    def assert_delete_das(self, orgph5):
        self.ph5object = init_ph5(orgph5, self.tmpdir)
        with LogCapture() as log:
            ret = fix_srm.delete_das(self.ph5object, 'Das_t_1X1111',
                                     'master.ph5', self.tmpdir)
        backupfile = 'Das_t_1X1111_%s_00.kef' % yeardoy
        datapath = '/Experiment_g/Receivers_g/Das_g_1X1111/Das_t'
        self.assertEqual(log.records[-1].msg, 'Nuke %s.' % datapath)
        self.assertEqual(ret[0], backupfile)
        self.assertEqual(ret[1], datapath)
        self.assertIsInstance(ret[2], ph5api.PH5)
        self.ph5object = ret[2]
        # check if backupfile exist
        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, backupfile)))
        # check if das 1X1111's data has been removed from self.ph5_object
        das = self.ph5object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5object.ph5_g_receivers.setcurrent(das)
        self.assertEqual(self.ph5object.ph5_g_receivers.current_t_das.nrows,
                         0)

    def test_delete_das_pn4(self):
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')
        self.assert_delete_das(orgph5)

    def test_delete_das_pn3(self):
        # pn3 is the old format of ph5 in which column
        # 'sample_rate_multiplier_i' is missing
        # => check delete_das create ph5 containing column
        # 'sample_rate_multiplier_i'
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/array_das')
        self.assert_delete_das(orgph5)
        # check if key sample_rate_multiplier_i has been added
        self.assertIn(
            'sample_rate_multiplier_i',
            self.ph5object.ph5_g_receivers.current_t_das.colnames)

    def test_delete_das_pn3_minifile_not_exist(self):
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/array_das')
        self.ph5object = init_ph5(orgph5, self.tmpdir)
        # clear external_file_name_s in index table
        index_rows, keys = self.ph5object.ph5_g_receivers.read_index()
        self.ph5object.ph5_g_receivers.nuke_index_t()
        for i in index_rows:
            i['external_file_name_s'] = 'test_file'
            self.ph5object.ph5_g_receivers.populateIndex_t(i)

        with self.assertRaises(Exception) as contxt:
            fix_srm.delete_das(self.ph5object, 'Das_t_1X1111',
                               'master.ph5', self.tmpdir)
        self.assertEqual(
            contxt.exception.message,
            "external_file_name_s 'test_file' for DAS 1X1111 in index_t "
            "can't be found in %s." % self.tmpdir)

    def test_delete_das_pn3_das_notfound(self):
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/array_das')
        self.ph5object = init_ph5(orgph5, self.tmpdir)
        # clear external_file_name_s in index table
        index_rows, keys = self.ph5object.ph5_g_receivers.read_index()
        self.ph5object.ph5_g_receivers.nuke_index_t()
        for i in index_rows:
            i['serial_number_s'] = '1X1112'
            self.ph5object.ph5_g_receivers.populateIndex_t(i)

        with self.assertRaises(Exception) as contxt:
            fix_srm.delete_das(self.ph5object, 'Das_t_1X1111',
                               'master.ph5', self.tmpdir)
        self.assertEqual(
            contxt.exception.message,
            "DAS 1X1111 cannot be found in index table.")

    def test_delete_array(self):
        # For adding array to ph5 from kef file, kef2ph5 will create table for
        # it, so delete_array will completly delete array_t from ph5.
        # No difference between pn3 or p4
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')
        self.ph5object = init_ph5(orgph5, self.tmpdir)
        with LogCapture() as log:
            ret = fix_srm.delete_array(self.ph5object,
                                       array_name='Array_t_001')

        backupfile = 'Array_t_001_%s_00.kef' % yeardoy
        datapath = '/Experiment_g/Sorts_g/Array_t_001'
        # # check nuke log msg
        self.assertEqual(log.records[2].msg,
                         'Nuke %s.' % datapath)
        # # check returning backupfile's name for das
        self.assertEqual(ret, (backupfile, datapath))
        # check if backupfile exist
        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, backupfile)))
        # check if array's data has been removed from self.ph5_object
        with self.assertRaises(tables.NoSuchNodeError):
            self.ph5object.ph5_g_sorts.ph5.get_node(
                '/Experiment_g/Sorts_g', name='Array_t_001', classname='Table')

    def test_add_fixed_table(self):
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/array_das')
        self.ph5object = init_ph5(orgph5, self.tmpdir)

        # ------------- DAS -----------------
        # remove das 1X1111 from ph5_object
        backupfile, datapath, self.ph5object = fix_srm.delete_das(
            self.ph5object, 'Das_t_1X1111', 'master.ph5', self.tmpdir)
        # test adding das kef file to ph5 object
        shutil.copy2(
            os.path.join(self.home,
                         'ph5/test_data/metadata/Das_t_1X1111.0.0_SRM0.kef'),
            'keffile.kef')
        fix_srm.add_fixed_table(
            self.ph5object, 'master.ph5', self.tmpdir, 'keffile.kef')
        # check if das has been added
        das = self.ph5object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5object.ph5_g_receivers.setcurrent(das)
        self.assertEqual(self.ph5object.ph5_g_receivers.current_t_das.nrows,
                         9)

        # ------------- ARRAY -----------------
        fix_srm.delete_array(self.ph5object,  array_name='Array_t_001')
        # test adding array kef file to ph5 object
        shutil.copy2(
            os.path.join(
                self.home, 'ph5/test_data/metadata/Array_t_001_SMR0.kef'),
            'keffile.kef')
        fix_srm.add_fixed_table(
            self.ph5object, 'master.ph5', self.tmpdir, 'keffile.kef')
        # check if array has been added
        node = self.ph5object.ph5_g_sorts.ph5.get_node(
            '/Experiment_g/Sorts_g', name='Array_t_001', classname='Table')
        rows, keys = experiment.read_table(node)
        self.assertEqual(len(rows), 3)

    def assert_process(self, srm_txt):
        # --------------- DAS ----------------
        # before process(), throw srm error when running read_das()
        das = self.ph5object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5object.ph5_g_receivers.setcurrent(das)
        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5object.ph5_g_receivers.read_das()
        self.assertEqual(context.exception.errno, 7)
        self.assertEqual(
            context.exception.msg,
            ('Das_t_1X1111 has sample_rate_multiplier_i %s. '
             'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.'
             % srm_txt))
        # after process() for das_name=Das_t_1X1111
        # there are no more error when running read_das()
        with LogCapture():
            self.ph5object = fix_srm.process(self.ph5object,
                                             'master.ph5',
                                             self.tmpdir,
                                             das_name='Das_t_1X1111')
        self.ph5object.close()
        self.ph5object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=True)
        das = self.ph5object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5object.ph5_g_receivers.setcurrent(das)
        rows, keys = self.ph5object.ph5_g_receivers.read_das()
        self.assertEqual(len(rows), 9)
        self.assertIn('sample_rate_multiplier_i', keys)

        # ----------------- ARRAY -----------------
        # before process(), throw srm error when running read_arrays()
        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5object.ph5_g_sorts.read_arrays('Array_t_001')
        self.assertEqual(context.exception.errno, 7)
        self.assertEqual(
            context.exception.msg,
            ('Array_t_001 has sample_rate_multiplier_i %s. '
             'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.'
             % srm_txt))
        # after process() for array_name=Array_t_001
        # there are no more error when running read_arrays()
        with LogCapture():
            fix_srm.process(self.ph5object,
                            'master.ph5',
                            self.tmpdir,
                            array_name='Array_t_001')
        self.ph5object.close()
        self.ph5object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=False)
        rows, keys = self.ph5object.ph5_g_sorts.read_arrays('Array_t_001')
        self.assertEqual(len(rows), 3)
        self.assertIn('sample_rate_multiplier_i', keys)

    def test_process_srm0(self):
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')
        self.ph5object = init_ph5(orgph5, self.tmpdir)
        self.assert_process(srm_txt='with value 0')

    def test_process_nosrm(self):
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/array_das')
        self.ph5object = init_ph5(orgph5, self.tmpdir)
        self.assert_process(srm_txt='missing')

    def assert_main(self, srm_txt):
        # before running fix_srm, throw srm error when running read_das()
        das = self.ph5object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5object.ph5_g_receivers.setcurrent(das)
        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5object.ph5_g_receivers.read_das()
        self.assertEqual(context.exception.errno, 7)
        self.assertEqual(
            context.exception.msg,
            ('Das_t_1X1111 has sample_rate_multiplier_i %s. '
             'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.'
             % srm_txt))
        # before running fix_srm, throw srm error when running read_arrays()
        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5object.ph5_g_sorts.read_arrays('Array_t_001')
        self.assertEqual(context.exception.errno, 7)
        self.assertEqual(
            context.exception.msg,
            ('Array_t_001 has sample_rate_multiplier_i %s. '
             'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.'
             % srm_txt))
        self.ph5object.close()

        testargs = ['fix_srm', '-n', 'master.ph5']
        with patch.object(sys, 'argv', testargs):
            fix_srm.main()
        self.ph5object = ph5api.PH5(
            path=self.tmpdir, nickname='master.ph5', editmode=False)
        # after running fix_srm for the whole ph5
        # there are no more error when running read_das(),
        # das_t include column 'sample_rate_multiplier_i'
        das = self.ph5object.ph5_g_receivers.getdas_g('1X1111')
        self.ph5object.ph5_g_receivers.setcurrent(das)
        rows, keys = self.ph5object.ph5_g_receivers.read_das()
        self.assertEqual(len(rows), 9)
        self.assertIn('sample_rate_multiplier_i', keys)
        # there are no more error when running read_arrays()
        # array_t include column 'sample_rate_multiplier_i'
        rows, keys = self.ph5object.ph5_g_sorts.read_arrays('Array_t_001')
        self.assertEqual(len(rows), 3)
        self.assertIn('sample_rate_multiplier_i', keys)
        # check backup files
        indir = os.listdir(self.tmpdir)
        self.assertTrue('Das_t_1X1111_%s_00.kef' % yeardoy in indir)
        self.assertTrue('Array_t_001_%s_00.kef' % yeardoy in indir)

    def test_main_srm0(self):
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')
        self.ph5object = init_ph5(orgph5, self.tmpdir)
        self.assert_main(srm_txt='with value 0')

    def test_main_nosrm(self):
        orgph5 = os.path.join(
            self.home,
            'ph5/test_data/ph5_no_srm/array_das')
        self.ph5object = init_ph5(orgph5, self.tmpdir)
        self.assert_main(srm_txt='missing')


if __name__ == "__main__":
    unittest.main()
