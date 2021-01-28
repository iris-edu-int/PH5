'''
Tests for ph5validate
'''
import unittest
import os
import sys
import logging
import shutil
from StringIO import StringIO

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.utilities import ph5validate, segd2ph5, nuke_table, kef2ph5
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase, kef_to_ph5


class TestPH5Validate_response_info(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5Validate_response_info, self).setUp()
        # copy ph5 data and tweak sensor model and sample rate in array 9
        # to test for inconsistencies between filenames and info
        orgph5path = os.path.join(self.home, "ph5/test_data/ph5")
        shutil.copy(os.path.join(orgph5path, 'master.ph5'),
                    os.path.join(self.tmpdir, 'master.ph5'))
        shutil.copy(os.path.join(orgph5path, 'miniPH5_00001.ph5'),
                    os.path.join(self.tmpdir, 'miniPH5_00001.ph5'))
        testargs = ['delete_table', '-n', 'master.ph5', '-A', '9']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                f = StringIO('y')
                sys.stdin = f
                nuke_table.main()
                f.close()
        kefpath = os.path.join(
            self.home,
            'ph5/test_data/metadata/array_9_test_resp_filename.kef')
        testargs = ['keftoph5', '-n', 'master.ph5', '-k', kefpath]
        with patch.object(sys, 'argv', testargs):
            kef2ph5.main()

        self.ph5API_object = ph5api.PH5(path=self.tmpdir,
                                        nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(self.ph5API_object, '.')

    def tearDown(self):
        self.ph5API_object.close()
        super(TestPH5Validate_response_info, self).tearDown()

    def test_check_array_t(self):
        # change response_file_sensor_a to
        # test for No response data loaded for gs11
        response_t = self.ph5validate.ph5.get_response_t_by_n_i(4)
        response_t['response_file_sensor_a'] = '/Experiment_g/Responses_g/gs11'
        with LogCapture():
            ret = self.ph5validate.check_array_t()
        for r in ret:
            if 'Station 9001' in r.heading:
                self.assertEqual(r.heading,
                                 "-=-=-=-=-=-=-=-=-\n"
                                 "Station 9001 Channel 1\n"
                                 "4 error, 1 warning, 0 info\n"
                                 "-=-=-=-=-=-=-=-=-\n"
                                 )
                # this error causes by changing samplerate
                errors = [
                    "No data found for das serial number 12183 during "
                    "this station's time. You may need to reload the "
                    "raw data for this station.",
                    'Response_t[4]:No response data loaded for gs11.',
                    "Response_t[4]:response_file_das_a 'rt125a_500_1_32' is "
                    "incomplete or inconsistent with "
                    "Array_t_009:sensor_model=cmg3t "
                    "Array_t_009:das_model=rt125a Array_t_009:sr=100 "
                    "Array_t_009:srm=1 Array_t_009:gain=32 "
                    "Array_t_009:cha=DPZ. Please check with format "
                    "[das_model]_[sr]_[srm]_[gain] or "
                    "[das_model]_[sensor_model]_[sr][cha].",
                    "Response_t[4]:response_file_sensor_a 'gs11' is "
                    "inconsistent with Array_t_009:sensor_model=cmg3t."]
                self.assertEqual(
                    set(r.error),
                    set(errors))
                self.assertEqual(
                    r.warning,
                    ['No station description found.'])
            if 'Station 0407 Channel -2' in r.heading:
                self.assertEqual(r.heading,
                                 "-=-=-=-=-=-=-=-=-\n"
                                 "Station 0407 Channel -2\n"
                                 "1 error, 2 warning, 0 info\n"
                                 "-=-=-=-=-=-=-=-=-\n"
                                 )
                self.assertEqual(
                    r.error,
                    ['Response_t[-1]:'
                     'Metadata response with n_i=-1 has no response data.'])
                # sample rate for station 0407 in array 4 is 0
                self.assertEqual(
                    r.warning,
                    ['No station description found.',
                     'Sample rate seems to be <= 0. Is this correct???'])


class TestPh5Validate_main_detect_data(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5Validate_main_detect_data, self).setUp()
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data'),
            ['rt125a/das_t_12183.kef', 'metadata/array_t_9_validate.kef'],
            das_sn_list=['12183'])

    def test_main(self):
        # test invalid level
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARN']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                self.assertRaises(SystemExit, ph5validate.main)
                output = out.captured.strip().split('\n')
        self.assertEqual(
            output[1],
            "ph5_validate: error: argument -l/--level: invalid choice: "
            "'WARN' (choose from 'ERROR', 'WARNING', 'INFO')")

        # test WARNING level
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARNING']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                ph5validate.main()
        with open('ph5_validate.log') as f:
            all_logs = f.read().split("-=-=-=-=-=-=-=-=-\n")

        self.assertEqual(
            all_logs[2],
            'ERROR: Experiment_t does not exist. '
            'run experiment_t_gen to create table\n')
        self.assertEqual(
            all_logs[3],
            'Station 9001 Channel 1\n2 error, 3 warning, 0 info\n')
        self.assertEqual(
            all_logs[4],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists before deploy time: 7 seconds.\n'
            'WARNING: Station 9001 [1550849950, 1550850034] is repeated '
            '2 time(s)\n')
        self.assertEqual(
            all_logs[5],
            'Station 9002 Channel 1\n2 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[6],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists after pickup time: 36 seconds.\n')
        self.assertEqual(
            all_logs[7],
            'Station 9003 Channel 1\n2 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[8],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n'
            'WARNING: No station description found.\n'
            'WARNING: Data exists after pickup time: 2 seconds.\n')

        # test ERROR level
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'ERROR']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture():
                ph5validate.main()
        with open('ph5_validate.log') as f:
            all_logs = f.read().split("-=-=-=-=-=-=-=-=-\n")

        self.assertEqual(
            all_logs[2],
            'ERROR: Experiment_t does not exist. '
            'run experiment_t_gen to create table\n')
        self.assertEqual(
            all_logs[3],
            'Station 9001 Channel 1\n2 error, 3 warning, 0 info\n')
        self.assertEqual(
            all_logs[4],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n')
        self.assertEqual(
            all_logs[5],
            'Station 9002 Channel 1\n2 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[6],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n')
        self.assertEqual(
            all_logs[7],
            'Station 9003 Channel 1\n2 error, 2 warning, 0 info\n')
        self.assertEqual(
            all_logs[8],
            'ERROR: No Response table found. Have you run resp_load yet?\n'
            'ERROR: Response_t has no entry for n_i=7\n')

    def test_get_args(self):
        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARN']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                self.assertRaises(SystemExit, ph5validate.get_args)
        output = out.captured.strip().split('\n')
        self.assertEqual(
            output[1],
            "ph5_validate: error: argument -l/--level: invalid choice: "
            "'WARN' (choose from 'ERROR', 'WARNING', 'INFO')")

        testargs = ['ph5_validate', '-n', 'master.ph5', '-p', self.tmpdir,
                    '-l', 'WARNING']
        with patch.object(sys, 'argv', testargs):
            ret = ph5validate.get_args()
        self.assertEqual(ret.level, 'WARNING')
        self.assertEqual(ret.nickname, 'master.ph5')
        self.assertEqual(ret.outfile, 'ph5_validate.log')
        self.assertEqual(ret.ph5path, self.tmpdir)
        self.assertEqual(ret.verbose, False)


class TestPh5Validate_detect_data(TempDirTestCase, LogTestCase):
    def setUp(self):
        super(TestPh5Validate_detect_data, self).setUp()
        kef_to_ph5(
            self.tmpdir, 'master.ph5',
            os.path.join(self.home, 'ph5/test_data'),
            ['rt125a/das_t_12183.kef', 'metadata/array_t_9_validate.kef'],
            das_sn_list=['12183'])
        self.ph5_object = ph5api.PH5(path=self.tmpdir, nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(
            self.ph5_object, self.tmpdir)

    def tearDown(self):
        self.ph5_object.ph5close()
        super(TestPh5Validate_detect_data, self).tearDown()

    def test_check_array_t(self):
        """
        check log messages, das_time and validation block return
        """
        with LogCapture() as log:
            log.setLevel(logging.INFO)
            vb = self.ph5validate.check_array_t()

        self.assertEqual(log.records[0].msg, "Validating Array_t")

        self.assertEqual(
            self.ph5validate.das_time,
            {('12183', 1, 500):
                {'max_pickup_time': [1550850187],
                 'time_windows': [(1550849950, 1550850034, '9001'),
                                  (1550849950, 1550850034, '9001'),
                                  (1550849950, 1550850034, '9001'),
                                  (1550850043, 1550850093, '9002'),
                                  (1550850125, 1550850187, '9003')],
                 'min_deploy_time':
                     [1550849950,
                      'Data exists before deploy time: 7 seconds.']}}
        )

        self.assertEqual(vb[0].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9001 Channel 1\n'
                         '2 error, 3 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[0].info, [])
        self.assertEqual(
            vb[0].warning,
            ['No station description found.',
             'Data exists before deploy time: 7 seconds.',
             'Station 9001 [1550849950, 1550850034] is repeated 2 time(s)'])
        self.assertEqual(
            vb[0].error,
            ['No Response table found. Have you run resp_load yet?',
             'Response_t has no entry for n_i=7']
        )

        self.assertEqual(vb[1].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9002 Channel 1\n'
                         '2 error, 2 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[1].info, [])
        self.assertEqual(
            vb[1].warning,
            ['No station description found.',
             'Data exists after pickup time: 36 seconds.'])
        self.assertEqual(
            vb[1].error,
            ['No Response table found. Have you run resp_load yet?',
             'Response_t has no entry for n_i=7']
        )

        self.assertEqual(vb[2].heading,
                         '-=-=-=-=-=-=-=-=-\nStation 9003 Channel 1\n'
                         '2 error, 2 warning, 0 info\n-=-=-=-=-=-=-=-=-\n')
        self.assertEqual(vb[2].info, [])
        self.assertEqual(
            vb[2].warning,
            ['No station description found.',
             'Data exists after pickup time: 2 seconds.'])
        self.assertEqual(
            vb[2].error,
            ['No Response table found. Have you run resp_load yet?',
             'Response_t has no entry for n_i=7']
        )

    def test_analyze_time(self):
        """
        + check if das_time created has all time and station info
        + check if it catch the case data exists before the whole time range
        """
        self.ph5validate.analyze_time()
        self.assertEqual(self.ph5validate.das_time.keys(), [('12183', 1, 500)])
        Dtime = self.ph5validate.das_time[('12183', 1, 500)]

        # 3 different deploy time
        self.assertEqual(len(Dtime['time_windows']), 5)

        # station 9001
        self.assertEqual(Dtime['time_windows'][0],
                         (1550849950, 1550850034, '9001'))
        self.assertEqual(Dtime['time_windows'][1],
                         (1550849950, 1550850034, '9001'))
        self.assertEqual(Dtime['time_windows'][2],
                         (1550849950, 1550850034, '9001'))
        # station 9002
        self.assertEqual(Dtime['time_windows'][3],
                         (1550850043, 1550850093, '9002'))
        # station 9003
        self.assertEqual(Dtime['time_windows'][4],
                         (1550850125, 1550850187, '9003'))

        self.assertEqual(Dtime['min_deploy_time'],
                         [1550849950,
                          'Data exists before deploy time: 7 seconds.'])

    def test_check_station_completeness(self):
        self.ph5validate.das_time = {
            ('12183', 1, 500):
            {'time_windows': [(1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550849950, 1550850034, '9001'),
                              (1550850043, 1550850093, '9002'),
                              (1550850125, 1550850187, '9003')],
             'min_deploy_time': [1550849950,
                                 'Data exists before deploy time: 7 seconds.'],
             }
        }

        self.ph5validate.read_arrays('Array_t_009')
        arraybyid = self.ph5validate.ph5.Array_t['Array_t_009']['byid']
        DT = self.ph5validate.das_time[('12183', 1, 500)]

        # check lon/lat not in range
        # check warning data exist before min_deploy_time
        station = arraybyid.get('9001')[1][0]
        station['location/X/value_d'] = 190.0
        station['location/X/units_s'] = 'degrees'
        station['location/Y/value_d'] = -100.0
        station['location/Y/units_s'] = 'degrees'
        station['location/Z/value_d'] = 1403
        station['location/Z/units_s'] = 'm'
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertEqual(
            warnings,
            ['No station description found.',
             'Data exists before deploy time: 7 seconds.',
             'Station 9001 [1550849950, 1550850034] is repeated 3 time(s)'])
        errors = ret[2]
        self.assertEqual(
            errors,
            ['No Response table found. Have you run resp_load yet?',
             'Channel longitude 190.0 not in range [-180,180]',
             'Channel latitude -100.0 not in range [-90,90]'])
        # check lon/lat = 0, no units, no elevation value
        # check warning data after pickup time
        station = arraybyid.get('9002')[1][0]
        station['location/X/value_d'] = 0
        station['location/X/units_s'] = ''
        station['location/Y/value_d'] = 0
        station['location/Y/units_s'] = None
        station['location/Z/value_d'] = None
        station['location/Z/units_s'] = ''
        ret = self.ph5validate.check_station_completeness(station)
        warnings = ret[1]
        self.assertEqual(
            warnings,
            ['No station description found.',
             'Channel longitude seems to be 0. Is this correct???',
             'No Station location/X/units_s value found.',
             'Channel latitude seems to be 0. Is this correct???',
             'No Station location/Y/units_s value found.',
             'No Station location/Z/units_s value found.',
             'Data exists after pickup time: 36 seconds.'])
        errors = ret[2]
        self.assertEqual(
            errors,
            ['No Response table found. Have you run resp_load yet?'])

        # check error overlaping
        # => change deploy time of the 3rd station
        DT['time_windows'][5] = (1550850090, 1550850187, '9003')
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn('Overlap time on station(s): 9002, 9003', errors)

        # check no data found for array's time
        # => change array's time to where there is no data
        station = arraybyid.get('9003')[1][0]
        station['deploy_time/epoch_l'] = 1550850190
        station['pickup_time/epoch_l'] = 1550850191
        DT['time_windows'][5] = (1550850190, 1550850191, '9003')
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 12183 during this "
                      "station's time. You may need to reload the raw data "
                      "for this station.",
                      errors)
        # check no data found errors
        station = arraybyid.get('9002')[1][0]
        station['das/serial_number_s'] = '1218'
        self.ph5validate.das_time[
            ('1218', 1, 500)] = self.ph5validate.das_time[('12183', 1, 500)]
        ret = self.ph5validate.check_station_completeness(station)
        errors = ret[2]
        self.assertIn("No data found for das serial number 1218. "
                      "You may need to reload the raw data for this station.",
                      errors)


class TestPH5Validate_no_response_filename(LogTestCase, TempDirTestCase):
    def tearDown(self):
        self.ph5API_object.close()
        super(TestPH5Validate_no_response_filename, self).tearDown()

    def test_check_response_t(self):
        testargs = ['segdtoph5', '-n', 'master.ph5', '-U', '13N', '-r',
                    os.path.join(self.home,
                                 'ph5/test_data/segd/3ch.fcnt')]
        with patch.object(sys, 'argv', testargs):
            segd2ph5.main()
        self.ph5API_object = ph5api.PH5(path=self.tmpdir,
                                        nickname='master.ph5')
        self.ph5validate = ph5validate.PH5Validate(self.ph5API_object, '.')
        with LogCapture() as log:
            log.setLevel(logging.ERROR)
            ret = self.ph5validate.check_response_t()
            self.assertEqual(
                ret[0].error,
                ["Response table does not contain any response file names. "
                 "Check if resp_load has been run or if metadatatoph5 input "
                 "contained response information."])
            self.assertEqual(
                log.records[0].msg,
                "Response table does not contain any response file names. "
                "Check if resp_load has been run or if metadatatoph5 input "
                "contained response information.")


if __name__ == "__main__":
    unittest.main()
