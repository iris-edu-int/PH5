'''
Tests for validation
'''

import unittest
import os
import logging
import sys

from mock import patch
from testfixtures import LogCapture

from ph5.core import ph5api
from ph5 import logger
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.utilities import validation, segd2ph5


class TestValidation_response(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestValidation_response, self).setUp()
        ph5path = os.path.join(self.home, "ph5/test_data/ph5")
        self.ph5API_object = ph5api.PH5(path=ph5path, nickname='master.ph5')

        self.resp_check_info = [
            {'n_i': 5, 'array': '002', 'sta': '0407',
             'cha_code': 'HHN', 'spr': 200, 'sprm': 1, 'cha_id': 1,
             'smodel': 'None CMG-3T', 'dmodel': 'None Q330'},
            {'n_i': 1, 'array': '008', 'sta': '8001',
             'cha_code': 'HLZ', 'spr': 100, 'sprm': 1, 'cha_id': 1,
             'smodel': 'cmg-3t', 'dmodel': 'rt130'},
            {'n_i': 4, 'array': '009', 'sta': '9001',
             'cha_code': 'DPZ', 'spr': 500, 'sprm': 1, 'cha_id': 1,
             'smodel': 'gs11v', 'dmodel': 'rt125a'}]

    def tearDown(self):
        self.ph5API_object.close()
        super(TestValidation_response, self).tearDown()

    def test_check_resp_data(self):
        checked_data_files = {}
        header = "array 008, station 8001, channel 1: "
        # data has been loaded for response file rt130_100_1_1
        validation.check_resp_data(
            self.ph5API_object.ph5,
            '/Experiment_g/Responses_g/rt130_100_1_1',
            header, checked_data_files, 1)
        self.assertEqual(checked_data_files,
                         {'rt130_100_1_1': ''})

        # data has NOT been loaded for response file rt130_200_1_1
        with self.assertRaises(Exception) as contxt:
            validation.check_resp_data(
                self.ph5API_object.ph5,
                '/Experiment_g/Responses_g/rt130_200_1_1',
                header, checked_data_files, 1)
        self.assertEqual(
            contxt.exception.message,
            ('%sResponse_t[1]:No response data loaded for '
             'rt130_200_1_1.' % header))
        self.assertEqual(
            checked_data_files,
            {'rt130_200_1_1': ('%sResponse_t[1]:No response data loaded for '
                               'rt130_200_1_1.' % header),
             'rt130_100_1_1': ''})

        # data has been loaded for response file cmg3t
        validation.check_resp_data(
            self.ph5API_object.ph5,
            '/Experiment_g/Responses_g/cmg3t',
            header, checked_data_files, 1)
        self.assertEqual(
            checked_data_files,
            {'rt130_200_1_1': ('%sResponse_t[1]:No response data loaded for '
                               'rt130_200_1_1.' % header),
             'rt130_100_1_1': '', 'cmg3t': ''})

        # data has NOT been loaded for response file cmg
        with self.assertRaises(Exception) as contxt:
            validation.check_resp_data(
                self.ph5API_object.ph5,
                '/Experiment_g/Responses_g/cmg',
                header, checked_data_files, 1)
        self.assertEqual(
            contxt.exception.message,
            '%sResponse_t[1]:No response data loaded for cmg.' % header)

        self.assertEqual(
            checked_data_files,
            {'rt130_200_1_1': ('%sResponse_t[1]:No response data loaded for '
                               'rt130_200_1_1.' % header),
             'cmg': ('%sResponse_t[1]:No response data loaded for cmg.'
                     % header),
             'rt130_100_1_1': '', 'cmg3t': ''})

    def test_check_metadatatoph5_format(self):
        errors = set()
        self.ph5API_object.read_response_t()

        info = next(item for item in self.resp_check_info if item["n_i"] == 4)
        header = "array 009, station 9001, channel 1: "
        info['dmodel_no_special_char'] = info['dmodel'].translate(None,
                                                                  ' ,/-=._')
        info['smodel_no_special_char'] = info['smodel'].translate(None,
                                                                  ' ,/-=._')

        # n_i=4: response_file_das_a has more than parts
        # => for sure not created by metadatatoph5
        # => return False, no err logged
        Response_t = self.ph5API_object.get_response_t_by_n_i(4)
        with LogCapture() as log:
            ret = validation.check_metadatatoph5_format(
                Response_t, info, header, errors, logger)
            self.assertFalse(ret)
            self.assertEqual(log.records, [])
            self.assertEqual(errors, set())

        # n_i=5 correct metadata format: 'NoneQ330_NoneCMG3T_200HHN'
        # => return True, no err logged
        Response_t = self.ph5API_object.get_response_t_by_n_i(5)
        info = next(item for item in self.resp_check_info if item["n_i"] == 5)
        info['dmodel_no_special_char'] = info['dmodel'].translate(None,
                                                                  ' ,/-=._')
        info['smodel_no_special_char'] = info['smodel'].translate(None,
                                                                  ' ,/-=._')
        header = "array 002, station 0407, channel 1: "
        with LogCapture() as log:
            ret = validation.check_metadatatoph5_format(
                Response_t, info, header, errors, logger)
            self.assertTrue(ret)
            self.assertEqual(log.records, [])
            self.assertEqual(errors, set())

        # n_i=5 sensor model mismatch => 2 parts correct
        # => for sure created by metadatatoph5
        # => return True, err logged for sensor model inconsistent

        Response_t['response_file_das_a'] = \
            '/Experiment_g/Responses_g/NoneQ330_CMG3T_200HHN'
        err = ("array 002, station 0407, channel 1: Response_t[5]:"
               "response_file_das_a 'NoneQ330_CMG3T_200HHN' is inconsistent "
               "with Array_t_002:sensor_model=None CMG-3T. Please check with "
               "metadatatoph5 format [das_model]_[sensor_model]_[sr][cha] "
               "(check doesn't include [cha]).")
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = validation.check_metadatatoph5_format(
                Response_t, info, header, errors, logger)
            self.assertTrue(ret)
            self.assertEqual(len(log.records), 1)
            self.assertEqual(log.records[0].msg, err)
            self.assertEqual(errors, set([(err, 'error')]))

        # n_i=5 sensor model and sample rate mismatch => only 1 part correct
        # => not sure created by metadatoph5
        # => return failed check for sensor model and sample rate
        errors = set()
        Response_t['response_file_das_a'] = \
            '/Experiment_g/Responses_g/NoneQ330_CMG3T_100HHN'
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = validation.check_metadatatoph5_format(
                Response_t, info, header, errors, logger)
            self.assertEqual(ret, ('', set(['spr', 'smodel'])))
            self.assertEqual(len(log.records), 0)
            self.assertEqual(errors, set())

        # n_i=5 response_file_das_a lack of 1 part, sensor model mismatch
        # => only 1 part correct
        # => not sure created by metadatatoph5
        # => return incomplete and failed check for sensor model
        Response_t['response_file_das_a'] = \
            '/Experiment_g/Responses_g/NoneQ330_CMG3T'
        with LogCapture() as log:
            ret = validation.check_metadatatoph5_format(
                Response_t, info, header, errors, logger)
            self.assertEqual(ret,  ('incomplete', set(['smodel'])))
            self.assertEqual(len(log.records), 0)
            self.assertEqual(errors, set())

        # n_i=5 response_file_das_a lack of 1 part
        # => 2 parts correct
        # => return True, log error for incomplete filename
        Response_t['response_file_das_a'] = \
            '/Experiment_g/Responses_g/NoneQ330_NoneCMG3T'
        err = ("array 002, station 0407, channel 1: Response_t[5]:"
               "response_file_das_a 'NoneQ330_NoneCMG3T' is incomplete. "
               "Please check with metadatatoph5 format "
               "[das_model]_[sensor_model]_[sr][cha] "
               "(check doesn't include [cha])."
               )
        with LogCapture() as log:
            ret = validation.check_metadatatoph5_format(
                Response_t, info, header, errors, logger)
            self.assertTrue(ret)
            self.assertEqual(len(log.records), 1)
            self.assertEqual(log.records[0].msg, err)
            self.assertEqual(errors, set([(err, 'error')]))

        errors = set()
        # complicated sensor model
        # => return True, no error logged
        Response_t['response_file_das_a'] = (
            '/Experiment_g/Responses_g/'
            'RT130_L28LB45Hz270VmsRc395OhmsRs2490Ohms_500DH2')
        info['smodel'] = ('L-28LB, 4.5 Hz, 27.0 V/m/s, '
                          'Rc=395 Ohms, Rs=2490 Ohms')
        info['dmodel'] = info['dmodel_no_special_char'] = 'RT130'
        info['spr'] = 500
        info['smodel_no_special_char'] = info['smodel'].translate(None,
                                                                  ' ,/-=._')
        with LogCapture() as log:
            ret = validation.check_metadatatoph5_format(
                Response_t, info, header, errors, logger)
            self.assertEqual(ret,  True)
            self.assertEqual(log.records, [])
            self.assertEqual(errors, set())

    def test_check_das_resp_load_format(self):
        errors = set()
        self.ph5API_object.read_response_t()
        Response_t = self.ph5API_object.get_response_t_by_n_i(4)
        info = next(item for item in self.resp_check_info if item["n_i"] == 4)
        info['dmodel_no_special_char'] = info['dmodel'].translate(None,
                                                                  ' ,/-=._')
        header = "array 009, station 9001, channel 1: "

        # n_i=4 response_das_file_name is 'rt125a_500_1_32'
        with LogCapture() as log:
            validation.check_das_resp_load_format(
                Response_t, info, header, errors, logger, True)
            self.assertEqual(len(log.records), 0)
            self.assertEqual(errors, set())

        # n_i=4: sample rate mismatch
        info['spr'] = 100
        err = ("array 009, station 9001, channel 1: Response_t[4]:"
               "response_file_das_a 'rt125a_500_1_32' is inconsistent "
               "with Array_t_009:sr=100. Please check with resp_load format "
               "[das_model]_[sr]_[srm]_[gain].")
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_das_resp_load_format(
                Response_t, info, header, errors, logger, False)
            self.assertEqual(log.records[0].msg, err)
            self.assertEqual(errors, set([(err, 'error')]))

        Response_t = self.ph5API_object.get_response_t_by_n_i(5)
        info = next(item for item in self.resp_check_info if item["n_i"] == 5)
        header = "array 002, station 0407, channel 1: "
        info['dmodel_no_special_char'] = info['dmodel'].translate(None,
                                                                  ' ,/-=._')
        # n_i=5 sensor model and sample rate mismatch
        errors = set()
        Response_t['response_file_das_a'] = \
            '/Experiment_g/Responses_g/NoneQ330_CMG3T_100HHN'
        err = ("array 002, station 0407, channel 1: Response_t[5]:"
               "response_file_das_a NoneQ330_CMG3T_100HHN is incomplete or "
               "inconsistent with "
               "Array_t_002:sr=200 Array_t_002:sensor_model=None CMG-3T "
               "Array_t_002:srm=1. Please check with resp_load format "
               "[das_model]_[sr]_[srm]_[gain] or metadatatoph5 format "
               "[das_model]_[sensor_model]_[sr][cha] "
               "(check doesn't include [cha]).")
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_das_resp_load_format(
                Response_t, info, header, errors, logger,
                ('', set(['spr', 'smodel']))
            )
            self.assertEqual(len(log.records), 1)
            self.assertEqual(log.records[0].msg, err)
            self.assertEqual(errors, set([(err, 'error')]))

        # n_i=5 sensor model mismatch,
        # metadatatoph5 format but lack of last part
        errors = set()
        Response_t['response_file_das_a'] = \
            '/Experiment_g/Responses_g/NoneQ330_CMG3T'
        err = ("array 002, station 0407, channel 1: "
               "Response_t[5]:response_file_das_a NoneQ330_CMG3T is "
               "incomplete or inconsistent with Array_t_002:sr=200 "
               "Array_t_002:sensor_model=None CMG-3T. "
               "Please check with resp_load format "
               "[das_model]_[sr]_[srm]_[gain] or metadatatoph5 format "
               "[das_model]_[sensor_model]_[sr][cha] "
               "(check doesn't include [cha]).")
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            validation.check_das_resp_load_format(
                Response_t, info, header, errors, logger,
                ('incomplete', set(['smodel']))
            )
            self.assertEqual(len(log.records), 1)
            self.assertEqual(log.records[0].msg, err)
            self.assertEqual(errors, set([(err, 'error')]))

        # response_file_das_a is blank but not log as error here
        # because it will return false for ph5tostationxml to throw err
        Response_t['response_file_das_a'] = ''
        errors = set()
        with LogCapture() as log:
            validation.check_das_resp_load_format(
                Response_t, info, header, errors, logger, True)
            self.assertEqual(log.records, [])
            self.assertEqual(errors, set([]))

    def test_check_sensor(self):
        errors = set()
        self.ph5API_object.read_response_t()
        Response_t = self.ph5API_object.get_response_t_by_n_i(4)
        info = next(item for item in self.resp_check_info if item["n_i"] == 4)
        info['smodel_no_special_char'] = info['smodel'].translate(None,
                                                                  ' ,/-=._')
        header = "array 009, station 9001, channel 1: "
        # n_i=4: response_sensor_file_name is 'gs11v'
        with LogCapture() as log:
            ret = validation.check_sensor(
                Response_t, info, header, errors, logger)
            self.assertIsNone(ret)
            self.assertEqual(log.records, [])
            self.assertEqual(errors, set([]))

        # n_i=4: response_sensor_file_name isn't 'cmg3t'
        info['smodel'] = info['smodel_no_special_char'] = 'cmg3t'
        err = ("array 009, station 9001, channel 1: Response_t[4]:"
               "response_file_sensor_a 'gs11v' is inconsistent with "
               "Array_t_009:sensor_model=cmg3t.")
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = validation.check_sensor(
                Response_t, info, header, errors, logger)
        self.assertFalse(ret)
        self.assertEqual(log.records[0].msg, err)
        self.assertEqual(errors, set([(err, 'error')]))

        errors = set()
        # n_i=4: response_sensor_file_name='', smodel=''
        Response_t['response_file_sensor_a'] = ''
        info['smodel'] = info['smodel_no_special_char'] = ''
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = validation.check_sensor(
                Response_t, info, header, errors, logger)
        self.assertFalse(ret)
        self.assertEqual(log.records, [])
        self.assertEqual(errors, set([]))

        errors = set()
        # n_i=4: response_sensor_file_name!='', smodel=''
        Response_t['response_file_sensor_a'] = \
            '/Experiment_g/Responses_g/gs11v'
        info['smodel'] = ''
        err = ("array 009, station 9001, channel 1: Response_t[4]:"
               "response_file_sensor_a 'gs11v' is inconsistent with "
               "Array_t_009:sensor_model=.")
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = validation.check_sensor(
                Response_t, info, header, errors, logger)
        self.assertFalse(ret)
        self.assertEqual(log.records[0].msg, err)
        self.assertEqual(errors, set([(err, 'error')]))

        errors = set()
        # n_i=4: response_sensor_file_name='', smodel!=''
        Response_t['response_file_sensor_a'] = ''
        info['smodel'] = 'gs11v'
        err = ('array 009, station 9001, channel 1: Response_t[4]:'
               'response_file_sensor_a is blank while sensor model exists.')
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = validation.check_sensor(
                Response_t, info, header, errors, logger)
        self.assertFalse(ret)
        self.assertEqual(log.records[0].msg, err)
        self.assertEqual(errors, set([(err, 'error')]))

    def test_check_response_info(self):
        self.ph5API_object.read_response_t()
        checked_data_files = {}
        errors = set()
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = validation.check_response_info(
                self.resp_check_info[2], self.ph5API_object,
                checked_data_files, errors, logger)
            self.assertEqual(ret, ('/Experiment_g/Responses_g/rt125a_500_1_32',
                                   '/Experiment_g/Responses_g/gs11v'))
            self.assertEqual(errors, set())
            self.assertEqual(log.records, [])

        info = next(item for item in self.resp_check_info if item["n_i"] == 4)
        info['spr'] = 100
        info['smodel'] = 'cmg3t'
        chckerrors = set(
            ["array 009 station 9001, channel 1: Response_t[4]:"
             "response_file_das_a 'rt125a_500_1_32' is inconsistent with "
             "Array_t_009:sr=100. Please check with resp_load format "
             "[das_model]_[sr]_[srm]_[gain].",
             "array 009 station 9001, channel 1: Response_t[4]:"
             "response_file_sensor_a 'gs11v' is inconsistent with "
             "Array_t_009:sensor_model=cmg3t."])
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = validation.check_response_info(
                info, self.ph5API_object, checked_data_files, errors, logger)
            self.assertEqual(ret, ('/Experiment_g/Responses_g/rt125a_500_1_32',
                                   '/Experiment_g/Responses_g/gs11v'))
            self.assertEqual(
                errors,
                {(errmsg, 'error') for errmsg in chckerrors})
            self.assertEqual({r.msg for r in log.records},
                             chckerrors)

        errors = set()
        info = next(item for item in self.resp_check_info if item["n_i"] == 5)
        info['dmodel'] = 'Q330'
        info['smodel'] = 'None/CMG3T'
        chckerrors = set(
            ["array 002 station 0407, channel 1: Response_t[5]:"
             "response_file_das_a 'NoneQ330_NoneCMG3T_200HHN' is inconsistent "
             "with Array_t_002:das_model=Q330. Please check with "
             "metadatatoph5 format [das_model]_[sensor_model]_[sr][cha] "
             "(check doesn't include [cha])."])
        with LogCapture() as log:
            log.setLevel(logging.WARNING)
            ret = validation.check_response_info(
                info, self.ph5API_object, checked_data_files, errors, logger)
            self.assertEqual(
                ret,
                ('/Experiment_g/Responses_g/NoneQ330_NoneCMG3T_200HHN', ''))
            self.assertEqual(
                errors,
                {(errmsg, 'error') for errmsg in chckerrors})
            self.assertEqual({r.msg for r in log.records},
                             chckerrors)

        response_t = self.ph5API_object.get_response_t_by_n_i(1)
        response_t['response_file_das_a'] = 'rt130_200_1_1'
        info = next(item for item in self.resp_check_info if item["n_i"] == 1)
        info['spr'] = 200
        ret = validation.check_response_info(
            info, self.ph5API_object, checked_data_files, errors, logger)
        self.assertEqual(
            ret,
            (False, ['array 008 station 8001, channel 1: Response_t[1]:'
                     'No response data loaded for rt130_200_1_1.']))

        info['n_i'] = 8
        ret = validation.check_response_info(
                info, self.ph5API_object, checked_data_files, errors, logger)
        self.assertEqual(ret,
                         (False, ['array 008 station 8001, channel 1: '
                                  'Response_t has no entry for n_i=8']))

    def test_check_response_unique_n_i(self):
        self.ph5API_object.read_response_t()
        response_t = self.ph5API_object.get_response_t_by_n_i(1)
        response_t['n_i'] = 2
        errors = set()
        validation.check_resp_unique_n_i(self.ph5API_object, errors)
        self.assertEqual(
            errors,
            {('Response_t n_i(s) duplicated: 2. '
              'Try to rerun resp_load to see if it fix the problem.',
              'error')})

    def test_check_has_response_filename(self):
        self.ph5API_object.read_response_t()
        has_response_file = validation.check_has_response_filename(
            self.ph5API_object.Response_t, [], None)
        self.assertTrue(has_response_file)


class TestValidation_no_response_filename(LogTestCase, TempDirTestCase):
    def tearDown(self):
        self.ph5.close()
        super(TestValidation_no_response_filename, self).tearDown()

    def test_check_has_response_filename(self):
        testargs = ['segdtoph5', '-n', 'master.ph5', '-U', '13N', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/fairfield/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        self.ph5 = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.ph5.read_response_t()
        has_response_file = validation.check_has_response_filename(
            self.ph5.Response_t, set(), None)
        self.assertEqual(has_response_file,
                         "Response table does not contain any response file "
                         "names. Check if resp_load has been run or if "
                         "metadatatoph5 input contained response information.")


class TestValidation_location(unittest.TestCase):
    def test_check_lat_lon_elev(self):
        station = {'location/X/value_d': 100.0,
                   'location/X/units_s': 'degrees',
                   'location/Y/value_d': 70.0,
                   'location/Y/units_s': 'degrees',
                   'location/Z/value_d': 1047,
                   'location/Z/units_s': 'm'}

        errors, warnings = validation.check_lat_lon_elev(station)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

        station = {'location/X/value_d': 190.0,
                   'location/X/units_s': '',
                   'location/Y/value_d': -100.0,
                   'location/Y/units_s': '',
                   'location/Z/value_d': 0.0,
                   'location/Z/units_s': ''}
        errors, warnings = validation.check_lat_lon_elev(station)
        self.assertEqual(
            errors,
            ['Channel longitude 190.0 not in range [-180,180]',
             'Channel latitude -100.0 not in range [-90,90]'])
        self.assertEqual(
            warnings,
            ['No Station location/X/units_s value found.',
             'No Station location/Y/units_s value found.',
             'Channel elevation seems to be 0. Is this correct???',
             'No Station location/Z/units_s value found.'])

        station = {'location/X/value_d': 0,
                   'location/X/units_s': '',
                   'location/Y/value_d': 0,
                   'location/Y/units_s': None,
                   'location/Z/value_d': 0,
                   'location/Z/units_s': 'unknown'}
        errors, warnings = validation.check_lat_lon_elev(station)
        self.assertEqual(errors, [])
        self.assertEqual(
            warnings,
            ['Channel longitude seems to be 0. Is this correct???',
             'No Station location/X/units_s value found.',
             'Channel latitude seems to be 0. Is this correct???',
             'No Station location/Y/units_s value found.',
             'location/Z/units_s is set as unknown. Consider'
             + ' updating this unit to m.',
             'Channel elevation seems to be 0. Is this correct???'])

        station = {'location/X/value_d': 0,
                   'location/X/units_s': '',
                   'location/Y/value_d': 0,
                   'location/Y/units_s': None,
                   'location/Z/value_d': 0,
                   'location/Z/units_s': None}
        errors, warnings = validation.check_lat_lon_elev(station)
        self.assertEqual(errors, [])
        self.assertEqual(
            warnings,
            ['Channel longitude seems to be 0. Is this correct???',
             'No Station location/X/units_s value found.',
             'Channel latitude seems to be 0. Is this correct???',
             'No Station location/Y/units_s value found.',
             'Channel elevation seems to be 0. Is this correct???',
             'No Station location/Z/units_s value found.'])


if __name__ == "__main__":
    unittest.main()
