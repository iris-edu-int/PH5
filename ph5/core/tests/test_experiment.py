'''
Tests for experiment
'''
import os
import unittest

from ph5.core import ph5api, experiment
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase


class TestExperiment_srm(TempDirTestCase, LogTestCase):
    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestExperiment_srm, self).tearDown()

    def set_current_das(self, das_sn):
        das = self.ph5_object.ph5_g_receivers.getdas_g(das_sn)
        self.ph5_object.ph5_g_receivers.setcurrent(das)

    def test_read_das_srm0(self):
        # test read_das with sample_rate_multiplier_i=0
        # => raise error if run with default ignore_srm=False
        # => pass assert_read_das() if ignore_srm=True

        ph5path = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')
        self.ph5_object = ph5api.PH5(path=ph5path, nickname='master.ph5')

        self.set_current_das('1X1111')
        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5_object.ph5_g_receivers.read_das()
        self.assertEqual(context.exception.errno, 7)
        self.assertEqual(
            context.exception.msg,
            ('Das_t_1X1111 has sample_rate_multiplier_i with value 0. '
             'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.'
             ))

        # same condition but with ignore_srm=True, read_das return no error
        ret, keys = self.ph5_object.ph5_g_receivers.read_das(ignore_srm=True)
        self.assertEqual(len(ret), 9)

    def test_read_das_nosrm(self):
        # test read_das with sample_rate_multiplier_i missing
        # => raise error if run with default ignore_srm=False
        # => pass assert_read_das() if ignore_srm=True

        nosrmpath = os.path.join(self.home,
                                 'ph5/test_data/ph5_no_srm/array_das')
        self.ph5_object = ph5api.PH5(path=nosrmpath, nickname='master.ph5')
        self.set_current_das('1X1111')
        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5_object.ph5_g_receivers.read_das()
        self.assertEqual(context.exception.errno, 7)
        self.assertEqual(
            context.exception.msg,
            ('Das_t_1X1111 has sample_rate_multiplier_i missing. '
             'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.'
             ))

        # same condition but with ignore_srm=True, read_das return no error
        ret, keys = self.ph5_object.ph5_g_receivers.read_das(ignore_srm=True)
        self.assertEqual(len(ret), 9)

    def test_read_arrays_srm0(self):
        # test read_arrays with sample_rate_multiplier_i=0
        # => raise error if run with default ignore_srm=False
        # => pass assert_read_array() if ignore_srm=True
        ph5path = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')
        self.ph5_object = ph5api.PH5(path=ph5path, nickname='master.ph5')

        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5_object.ph5_g_sorts.read_arrays('Array_t_001')
        self.assertEqual(context.exception.errno, 7)
        self.assertEqual(
            context.exception.msg,
            ('Array_t_001 has sample_rate_multiplier_i with value 0. '
             'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.'
             ))

        # same condition but with ignore_srm=True, read_arrays return no error
        ret, keys = self.ph5_object.ph5_g_sorts.read_arrays(
            'Array_t_001', ignore_srm=True)
        self.assertEqual(len(ret), 3)

    def test_read_arrays_nosrm(self):
        # test read_arrays with sample_rate_multiplier_i missing
        # => raise error if run with default ignore_srm=False
        # => pass assert_read_das() if ignore_srm=True

        nosrmpath = os.path.join(self.home,
                                 'ph5/test_data/ph5_no_srm/array_das')
        self.ph5_object = ph5api.PH5(path=nosrmpath, nickname='master.ph5')
        with self.assertRaises(experiment.HDF5InteractionError) as context:
            self.ph5_object.ph5_g_sorts.read_arrays('Array_t_001')
        self.assertEqual(context.exception.errno, 7)
        self.assertEqual(
            context.exception.msg,
            ('Array_t_001 has sample_rate_multiplier_i missing. '
             'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.'
             ))

        # same condition but with ignore_srm=True, read_arrays return no error
        ret, keys = self.ph5_object.ph5_g_sorts.read_arrays(
            'Array_t_001', ignore_srm=True)
        self.assertEqual(len(ret), 3)

    def test_read_arrays_ph5_t_array_tabletype(self):
        # ph5_t_array normally has type dict
        # when more than one array_t(s) are added to ph5 with keftoph5,
        # it has type table which will raise IndexError
        # when trying to get the node from ph5_t_array
        # => if it raise IndexError, force it to be a dict

        path = os.path.join(self.home,
                            'ph5/test_data/ph5_w_ph5_t_array_tabletype')
        self.ph5_object = ph5api.PH5(path=path, nickname='master.ph5')
        ret, keys = self.ph5_object.ph5_g_sorts.read_arrays('Array_t_002')
        self.assertEqual(len(ret), 1)
        self.assertEqual(len(keys), 38)


if __name__ == "__main__":
    unittest.main()
