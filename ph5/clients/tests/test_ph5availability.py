"""
unit tests for ph5availability
"""

import unittest
import sys
import os
import logging

from mock import patch
from testfixtures import OutputCapture, LogCapture

from ph5.clients import ph5availability
from ph5.core import ph5api
from ph5.core.tests.test_base import LogTestCase, TempDirTestCase
from ph5.clients.ph5toms import PH5toMSeed


def checkTupleAlmostEqualIn(tup, tupList, place):
    """
    check if a tuple in a list of tuples in which float items only
    need to be almost equal
    :type tup: tuple
    :param tup: tuple to be checked
    :type tupList: list of tuples
    :para tupList: list of tuples that tup need to be check with
    :place: decimal places to round the values to compare
    """
    for T in tupList:
        length = len(tup)
        if length != len(T):
            continue
        for i in range(length):
            if type(tup[i]) is float:
                if round(tup[i], place) != round(T[i], place):
                    break
            else:
                if tup[i] != T[i]:
                    break
            if i == length - 1:
                return True
    return False


def checkFieldsMatch(fieldNames, fieldsList, dictList):
    """
    check if given fieldslist match the dict dictList at field fieldNames
    :type fieldsName: list of str
    :param fieldsName: list of field names that their values are to be compared
       with items in dictList
    :type fieldsList: list of tuple
    :para fieldsList: list of tuple of fields' values
    :type dictList: list of dictionary
    :para dictList: list of dictionary to be compared with
    """
    if len(fieldsList) != len(dictList):
        return False
    for d in dictList:
        arow = ()
        for i in range(len(fieldNames)):
            arow += (d[fieldNames[i]], )
        if arow not in fieldsList:
            return False
        fieldsList.remove(arow)
    return True


class TestPH5Availability(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5Availability, self).setUp()
        self.ph5test_path = os.path.join(self.home, 'ph5/test_data/ph5')
        self.ph5_object = ph5api.PH5(path=self.ph5test_path,
                                     nickname='master.ph5')
        self.availability = ph5availability.PH5Availability(self.ph5_object)

    def tearDown(self):
        self.ph5_object.close()
        super(TestPH5Availability, self).tearDown()

    def test_get_slc(self):
        # should return ALL available
        # station location and channels
        ret = self.availability.get_slc()
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # Should return only station 8001
        ret = self.availability.get_slc(station='8001')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 3 entries
        self.assertEqual(3, len(ret))
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)

        # Should return only station 500
        ret = self.availability.get_slc(station='5??')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 3 entries
        self.assertEqual(3, len(ret))
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)

        # Should return stations 500 and 9001 channel DPZ
        ret = self.availability.get_slc(channel='DPZ')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 2 entries
        self.assertEqual(2, len(ret))
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # Should return stations 500 and 9001 channel
        # all channels starting with DP
        ret = self.availability.get_slc(channel='DP?')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 4 entries
        self.assertEqual(4, len(ret))
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return all stations and channels
        # because they all have same loc
        ret = self.availability.get_slc(location='')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return all stations and channels
        # because they are all on or after start time
        ret = self.availability.get_slc(starttime=1463568480)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return all stations and channels
        # because they all contain data before end time
        ret = self.availability.get_slc(endtime=1550850240)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return all stations and channels
        # because they are all contain data between start and end time
        ret = self.availability.get_slc(starttime=1463568480,
                                        endtime=1550850240)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return no stations
        # because they all end before start time
        ret = self.availability.get_slc(starttime=1741880232)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

        # should return no stations
        # because they all start after end time
        ret = self.availability.get_slc(endtime=637342632)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

        # should return
        # station 0407 and all channels
        ret = self.availability.get_slc(
            station='0407',
            location='',
            channel='*',
            starttime=1545085229)
        # return type should be list
        self.assertTrue(type(ret) is list)
        self.assertEqual(3, len(ret))
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)

        # should return all stations
        # should return all stations and channels
        # because they are all contain data between start and end time
        ret = self.availability.get_slc(
            station='*',
            location='',
            channel='*',
            starttime=1463568480,
            endtime=1550850240)
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 10 entries
        self.assertEqual(10, len(ret))
        # check for expected tuple values
        self.assertTrue(('500', '', 'DP1') in ret)
        self.assertTrue(('500', '', 'DP2') in ret)
        self.assertTrue(('500', '', 'DPZ') in ret)
        self.assertTrue(('0407', '', 'HHN') in ret)
        self.assertTrue(('0407', '', 'LHN') in ret)
        self.assertTrue(('0407', '', 'LOG') in ret)
        self.assertTrue(('8001', '', 'HL1') in ret)
        self.assertTrue(('8001', '', 'HL2') in ret)
        self.assertTrue(('8001', '', 'HLZ') in ret)
        self.assertTrue(('9001', '', 'DPZ') in ret)

        # should return nothing
        ret = self.availability.get_slc(station='99999')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

        # should return nothing
        ret = self.availability.get_slc(station='8001',
                                        channel='XYZ')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

        # should return nothing
        ret = self.availability.get_slc(station='9001',
                                        channel='HHN')
        # return type should be list
        self.assertTrue(type(ret) is list)
        # there should be 0 entries
        self.assertEqual(0, len(ret))

    def test_get_availability_extent(self):
        # expected to return all extent information
        ret = self.availability.get_availability_extent()
        # There are 10 channels all with data
        # so expect 10 entries
        self.assertEqual(10, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189) in ret)
        self.assertTrue(('8001', '', 'HL1',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HL2',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HLZ',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'HHN', 1545085230.917, 1545085240.9220002), ret, 2))
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'LHN', 1545085230.681998, 1545085240.691998), ret, 2))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205) in ret)
        self.assertTrue(('500', '', 'DP1',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DP2',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

        # get extent for 9001. A station with gaps
        # large time range encompassing trace
        ret = self.availability.get_availability_extent(
            station='9001',
            channel='DPZ',
            location='',
            starttime=1,
            endtime=2530985583)
        # expect 1 entry because only 1 channel
        # within time range was requested
        self.assertEqual(1, len(ret))
        # expected entry
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189) in ret)

        # same request but with sample rate included
        ret = self.availability.get_availability_extent(
            station='9001',
            channel='DPZ',
            location='',
            starttime=1,
            endtime=2530985583,
            include_sample_rate=True)
        # expect 1 entry because only 1 channel
        # within time range was requested
        self.assertEqual(1, len(ret))
        # expected entry with sample_rate included
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189,
                         500.0) in ret)
        #                 250.0) in ret)

        # Check LOG channel
        ret = self.availability.get_availability_extent(
            station='0407',
            channel='LOG',
            location='',
            starttime=1545088205,
            endtime=1545088205)
        # expect 1 entry because only 1 channel
        # within time range was requested
        self.assertEqual(1, len(ret))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205) in ret)

        # Check LOG channel with sample rate
        ret = self.availability.get_availability_extent(
            station='0407',
            channel='LOG',
            location='',
            starttime=1545088205,
            endtime=1545088205,
            include_sample_rate=True)
        # expect 1 entry because only 1 channel
        # within time range was requested
        self.assertEqual(1, len(ret))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205, 0.0) in ret)

        # get all DPZ channels
        ret = self.availability.get_availability_extent(
            station='*',
            channel='DPZ',
            location='',
            starttime=1,
            endtime=2530985583)
        # there are 2 DPZ channels in the time range
        self.assertEqual(2, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189) in ret)
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

        # get matching all locations ''
        # expected to return all extent information
        ret = self.availability.get_availability_extent(
            station='*',
            channel='*',
            location='',
            starttime=1,
            endtime=2530985583
        )
        # There are 10 channels all with data
        # so expect 10 entries
        self.assertEqual(10, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550850189) in ret)
        self.assertTrue(('8001', '', 'HL1',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HL2',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HLZ',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'HHN', 1545085230.917, 1545085240.9220002), ret, 2))
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'LHN', 1545085230.681998, 1545085240.691998), ret, 2))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205) in ret)
        self.assertTrue(('500', '', 'DP1',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DP2',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

        # get matching all locations '01'
        # expected to return none
        ret = self.availability.get_availability_extent(
            station='*',
            channel='*',
            location='01',
            starttime=1,
            endtime=2530985583
        )
        # There are 0 channels with data
        # so expect 0 entries
        self.assertFalse(ret)

        # expected to return none
        ret = self.availability.get_availability_extent(
            station='12345',
            channel='*',
            location='*',
            starttime=1,
            endtime=2530985583
        )
        # There are 0 channels with data
        # so expect 0 entries
        self.assertFalse(ret)

        # expected to return none
        ret = self.availability.get_availability_extent(
            station='8001',
            channel='*',
            location='*',
            starttime=1502294400.38,
            endtime=1502294460.38
        )
        # There are 0 channels with data
        # so expect 0 entries
        self.assertFalse(ret)

        # expected to raise error
        self.assertRaises(
            ValueError,
            self.availability.get_availability_extent,
            '*', '*', '*', None, 1502294460.38)

    def test_get_availability(self):
        # expected to return all availability information
        ret = self.availability.get_availability()
        # There are 10 channels all with data
        # but 9001 has 8 gaps so expect 18 entries
        self.assertEqual(18, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550849949) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550849973, 1550849974) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850003, 1550850009) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850033, 1550850034) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850060, 1550850068) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850093, 1550850094) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850123, 1550850129) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850153, 1550850154) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850183, 1550850189) in ret)
        self.assertTrue(('8001', '', 'HL1',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HL2',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(('8001', '', 'HLZ',
                         1463568480, 1463568517.88) in ret)
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'HHN', 1545085230.917, 1545085240.9220002), ret, 2))
        self.assertTrue(checkTupleAlmostEqualIn(
            ('0407', '', 'LHN', 1545085230.681998, 1545085240.691998), ret, 2))
        self.assertTrue(('0407', '', 'LOG',
                         1545088205, 1545088205) in ret)
        self.assertTrue(('500', '', 'DP1',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DP2',
                         1502294400.38, 1502294460.38) in ret)
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

        # expected to return all availability information
        # for 9001
        ret = self.availability.get_availability(
            station='9001', channel='DPZ',
            location='', starttime=1550849943,
            endtime=1550850189)
        # 9001 has 8 gaps so expect 9 entries
        self.assertEqual(9, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849943, 1550849949) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550849973, 1550849974) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850003, 1550850009) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850033, 1550850034) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850060, 1550850068) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850093, 1550850094) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850123, 1550850129) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850153, 1550850154) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850183, 1550850189) in ret)

        # expected to return partial information
        # for 9001 based on times requested
        ret = self.availability.get_availability(
            station='9001', channel='DPZ',
            location='', starttime=1550849973,
            endtime=1550850005)
        # 9001 for this time range has 1 gap
        self.assertEqual(2, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550849973, 1550849974) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850003, 1550850005) in ret)

        # expected to return partial information
        # for 9001 based on times requested
        ret = self.availability.get_availability(
            station='9001', channel='DPZ',
            location='', starttime=1550850060,
            endtime=1550850154)
        # 9001 for this time range has 3 gaps
        self.assertEqual(4, len(ret))
        self.assertTrue(('9001', '', 'DPZ',
                         1550850060, 1550850068) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850093, 1550850094) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850123, 1550850129) in ret)
        self.assertTrue(('9001', '', 'DPZ',
                         1550850153, 1550850154) in ret)

        # expected to return no gaps
        # for 500 all data in channel DPZ
        ret = self.availability.get_availability(
            station='500', channel='DPZ',
            location='', starttime=1502294400.38,
            endtime=1502294460.38)
        # 500 DPZ has 2 windows but no gaps
        self.assertEqual(1, len(ret))
        self.assertTrue(('500', '', 'DPZ',
                         1502294400.38, 1502294460.38) in ret)

    def test_get_availability_percentage(self):
        # should return 100% and 0 gaps
        ret = self.availability.get_availability_percentage(
            '500',
            '',
            'DP1',
            1502294400.38,
            1502294460.38)
        self.assertTrue(isinstance(ret, tuple))
        self.assertEqual(1.0, ret[0])
        self.assertEqual(0, ret[1])

        # should return 14.63% and 8 gaps
        ret = self.availability.get_availability_percentage(
            '9001',
            '',
            'DPZ',
            1550849943,
            1550850189)
        self.assertTrue(isinstance(ret, tuple))
        self.assertAlmostEquals(0.14634146341, ret[0], 4)
        self.assertEqual(8, ret[1])

        # should return 11.67% and 2 gaps
        ret = self.availability.get_availability_percentage(
            '9001',
            '',
            'DPZ',
            1550849943,
            1550850003)
        self.assertTrue(isinstance(ret, tuple))
        self.assertAlmostEquals(0.1167, ret[0], 3)
        self.assertEqual(2, ret[1])

        # should return 97.13% and 2 gaps
        ret = self.availability.get_availability_percentage(
            '8001',
            '',
            'HLZ',
            1463568479,
            1463568518)
        self.assertTrue(isinstance(ret, tuple))
        self.assertAlmostEquals(0.9713, ret[0], 4)
        self.assertEqual(2, ret[1])

        # should return 0% and 0 gaps
        ret = self.availability.get_availability_percentage(
            '9001',
            '',
            'DP1',
            1463568479,
            1463568518)
        self.assertTrue(isinstance(ret, tuple))
        self.assertEqual(0.0, ret[0])
        self.assertEqual(0, ret[1])

        # should return 0% and 0 gaps
        ret = self.availability.get_availability_percentage(
            '12345',
            '',
            'XYZ',
            1463568479,
            1463568518)
        self.assertTrue(isinstance(ret, tuple))
        self.assertEqual(0.0, ret[0])
        self.assertEqual(0, ret[1])

        # should return 0% and 0 gaps
        ret = self.availability.get_availability_percentage(
            '8001',
            '',
            'HLZ',
            1550849943,
            1550850183)
        self.assertTrue(isinstance(ret, tuple))
        self.assertEqual(0.0, ret[0])
        self.assertEqual(0, ret[1])

    def test_has_data(self):
        # assumes all for everything
        # should return true
        self.assertTrue(
            self.availability.has_data())

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='*'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='8001'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='0407'))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='9999'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='*'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='???'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='HHN'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='LOG'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                channel='DP1'))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='XYZ'))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='DP9'))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                location='01'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                location=''))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='0407',
                location=''))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='0407',
                location='01'))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='8001',
                channel='HL?',
                location=''))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='8001',
                channel='HLZ',
                location=''))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='8001',
                channel='XYZ',
                location=''))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                starttime=1463568480))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                starttime=1550849929))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                starttime=1615652704))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                endtime=1463568489))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                endtime=605809504))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='*',
                location='',
                channel='???',
                starttime=605809504,
                endtime=1741883104))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='8001',
                location='',
                channel='HL2',
                starttime=605809504,
                endtime=1741883104))

        # should return true
        self.assertTrue(
            self.availability.has_data(
                station='0407',
                location='',
                channel='LOG',
                starttime=605809504,
                endtime=1741883104))

        # should return false
        self.assertFalse(
            self.availability.has_data(
                station='500',
                location='',
                channel='LOG',
                starttime=605809504,
                endtime=1741883104))

    def test_get_args(self):
        with OutputCapture():
            with self.assertRaises(SystemExit):
                ph5availability.get_args([])
            with self.assertRaises(SystemExit):
                ph5availability.get_args(['-n', 'master.ph5'])
            with self.assertRaises(SystemExit):
                ph5availability.get_args(
                    ['-n', 'master.ph5', '-p', self.ph5test_path])
            # test false args
            with self.assertRaises(SystemExit):
                ph5availability.get_args(
                    ['-n', 'master.ph5', '-p', self.ph5test_path,
                     '-a', '0', '-T'])
        # test default args
        ret = vars(ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0']))
        expect = {
            'array_t_': None, 'format': None, 'start_time': None,
            'output_file': None, 'avail': 0, 'end_time': None,
            'sta_id_list': [], 'ph5path': self.ph5test_path,
            'samplerate': False, 'nickname': 'master.ph5', 'sta_list': [],
            'channel': [], 'location': None}
        self.assertDictEqual(ret, expect)
        # test correct args received
        ret = vars(ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0',
             '-s', '2017-08-09T16:00:00.380000',
             '-e', '2017-08-09T16:01:00.380000', '--station', '500,0407',
             '--station_id', '500,0407', '-l', '00', '-c', 'DP1', '-S',
             '-A', '1', '-F', 't', '-o', 'extent.txt']))
        expect = {
            'array_t_': 1, 'format': 't', 'ph5path': self.ph5test_path,
            'output_file': 'extent.txt', 'avail': 0,
            'start_time': '2017-08-09T16:00:00.380000',
            'end_time': '2017-08-09T16:01:00.380000',
            'sta_id_list': '500,0407', 'sta_list': '500,0407',
            'samplerate': True, 'nickname': 'master.ph5',
            'channel': 'DP1', 'location': '00'}
        self.assertDictEqual(ret, expect)

    def test_analyze_args(self):
        A = self.availability
        # test wrong format channel
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0',
             '-c', '1 2 3'])
        self.assertRaises(
            ph5availability.PH5AvailabilityError, A.analyze_args, args)

        # test wrong format location: len > 2
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0',
             '-l', 'Oaa'])
        self.assertRaises(
            ph5availability.PH5AvailabilityError, A.analyze_args, args)

        # test wrong format location: invalid character
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0',
             '-l', 'O^'])
        self.assertRaises(
            ph5availability.PH5AvailabilityError, A.analyze_args, args)

        # test wrong format station
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0',
             '--station', 'o-g'])
        self.assertRaises(
            ph5availability.PH5AvailabilityError, A.analyze_args, args)

        # test wrong avail:5
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '5'])
        self.assertRaises(
            ph5availability.PH5AvailabilityError, A.analyze_args, args)

        # given -o but avail not 2 or 3
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path,
             '-a', '0', '-o', 'test'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.OFILE, None)

        # given -o, avail=2 but no format given
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path,
             '-a', '2', '-o', 'test'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertIsNotNone(A.OFILE)

        # test default args
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.stations, ['*'])
        self.assertEqual(A.locations, ['*'])
        self.assertEqual(A.channels, ['*'])
        self.assertEqual(A.starttime, None)
        self.assertEqual(A.endtime, None)
        self.assertEqual(A.array, None)
        self.assertEqual(A.avail, 0)
        self.assertEqual(A.SR_included, False)
        self.assertEqual(A.OFILE, None)

        # test wildcard station, location, channel
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0',
             '--station', '*', '-l', '*', '-c', '*'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.stations, ['*'])
        self.assertEqual(A.locations, ['*'])
        self.assertEqual(A.channels, ['*'])

        # test wildcard station, location, channel
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0',
             '--station_id', '?001', '-l', '??', '-c', 'DP?'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.stations, ['?001'])
        self.assertEqual(A.locations, ['??'])
        self.assertEqual(A.channels, ['DP?'])

        # test args are assigned correctly,
        # a=0, check if SR_included=False, OFILE=None
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '0',
             '-s', '2017-08-09T16:00:00.380000',
             '-e', '2017-08-09T16:01:00.380000', '--station', '500,0407',
             '-l', '00', '-c', 'DP1', '-S',
             '-A', '1', '-F', 't', '-o', 'extent.txt'])
        ret = A.analyze_args(args)
        self.assertEqual(ret, True)
        self.assertEqual(A.stations, ['500', '0407'])
        self.assertEqual(A.locations, ['00'])
        self.assertEqual(A.channels, ['DP1'])
        self.assertEqual(A.starttime, 1502294400.38)
        self.assertEqual(A.endtime, 1502294460.38)
        self.assertEqual(A.array, 1)
        self.assertEqual(A.avail, 0)
        # SR_included only True when avail =2 or 3
        self.assertEqual(A.SR_included, False)
        self.assertEqual(A.OFILE, None)

        # same args, with avail=2, check if SR_included=True
        args = ph5availability.get_args(
            ['-n', 'master.ph5', '-p', self.ph5test_path, '-a', '2',
             '-S', '-F', 't', '-o', 'extent.txt'])
        ret = A.analyze_args(args)
        self.assertEqual(A.SR_included, True)
        self.assertEqual(A.OFILE.name, 'extent.txt')
        self.assertEqual(A.OFILE.closed, False)

    def test_main(self):
        # wrong path entered
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    'some/bad/path', '-a', '0']
        with patch.object(sys, 'argv', testargs):
            with self.assertRaises(SystemExit):
                ph5availability.main()

        # test has_data station with data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '0', '--station',
                    '500', '--channel', 'DP1']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare("True")

        # test has_data station with data all channels
        # expect to return True 3 times, once for each channel
        # master_PH5_file without extension
        testargs = ['ph5availability', '-n', 'master', '-p',
                    self.ph5test_path, '-a', '0', '--station',
                    '500', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare("True")

        # test has_data station with no data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '0', '--station',
                    '9576', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('False')

        # test has_data station list data, no data,
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '0', '--station',
                    '9001,91234', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('True')

        # test has_data with start time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '0', '-s',
                    '2017-08-09T16:00:00.380000', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('True')

        # test has_data with end time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '0', '-e',
                    '2019-02-22T15:43:09.000000', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('True')

        # test has_data with time range having data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '0',
                    '-s', '2019-02-22T15:39:03.000000',
                    '-e', '2019-02-22T15:43:09.000000', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('True')

        # test has_data with time range having no data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '0',
                    '-s', '2017-08-09T16:01:01.0',
                    '-e', '2018-12-17T22:20:30.0', '--channel', '*']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('False')

        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '0', '-A', '2']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('True')

        # ------------------------------------------------------------ #
        # test get_slc with station
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '1', '--station', '0407']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare("[('0407', '', 'HHN'), ('0407', '', 'LHN'), "
                            "('0407', '', 'LOG')]")

        # test get_slc with channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '1', '-c', 'LOG']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare("[('0407', '', 'LOG')]")

        # test get_slc with time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '1',
                    '-s', '2019-02-22T15:39:03.000000',
                    '-e', '2019-02-22T15:43:09.000000']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare("[('9001', '', 'DPZ')]")

        # test get_slc with array
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '1', '-A', '2']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare("[('0407', '', 'HHN')]")

        # ------------------------------------------------------------ #
        # test get_availability with station
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '2', '--station', '0407']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "#n s     l  c   q                    earliest"
                    "                      latest\n"
                    "AA 0407  -- HHN   2018-12-17T22:20:30.917000Z"
                    " 2018-12-17T22:20:40.922000Z\n"
                    "AA 0407  -- LHN   2018-12-17T22:20:30.681998Z"
                    " 2018-12-17T22:20:40.691998Z\n"
                    "AA 0407  -- LOG   2018-12-17T23:10:05.000000Z"
                    " 2018-12-17T23:10:05.000000Z")

        # test get_availability with channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '2', '-c', 'LOG']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "#n s     l  c   q                    earliest"
                    "                      latest\n"
                    "AA 0407  -- LOG   2018-12-17T23:10:05.000000Z"
                    " 2018-12-17T23:10:05.000000Z")

        # test get_availability with time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '2',
                    '-s', '2018-12-17T23:10:05.0',
                    '-e', '2019-02-22T15:39:03.1']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "#n s     l  c   q                    earliest"
                    "                      latest\n"
                    "AA 0407  -- LOG   2018-12-17T23:10:05.000000Z"
                    " 2018-12-17T23:10:05.000000Z\n"
                    "AA 9001  -- DPZ   2019-02-22T15:39:03.000000Z"
                    " 2019-02-22T15:39:03.099999Z")

        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '2', '-A', '4']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "#n s     l  c   q                    earliest"
                    "                      latest\n"
                    "AA 0407  -- LOG   2018-12-17T23:10:05.000000Z"
                    " 2018-12-17T23:10:05.000000Z")

        # ------------------------------------------------------------ #
        # test get_availability_extent with station
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3', '--station', '9001']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "#n s     l  c   q                    earliest"
                    "                      latest\n"
                    "AA 9001  -- DPZ   2019-02-22T15:39:03.000000Z"
                    " 2019-02-22T15:43:09.000000Z")

        # test get_availability_extent with channel
        # if wrong format is stated, still print out tuple result with
        # a warning
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3', '-c', 'DP2', '-F', 'k']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "[('500', '', 'DP2', 1502294400.38, 1502294460.38)]")

        # test get_availability_extent with time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3', '-S',
                    '-s', '2019-02-22T15:39:04.1',
                    '-e', '2019-02-22T15:39:07.1']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "#n s     l  c   q sample-rate                    earliest"
                    "                      latest\n"
                    "AA 9001  -- DPZ         500.0 2019-02-22T15:39:04.099999Z"
                    " 2019-02-22T15:39:07.099999Z")

        # test get_availability_extent with wildcard station, location, channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3',
                    '--station', '?001', '-l', '*', '-c', 'DP?']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "#n s     l  c   q                    earliest"
                    "                      latest\n"
                    "AA 9001  -- DPZ   2019-02-22T15:39:03.000000Z"
                    " 2019-02-22T15:43:09.000000Z")

        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3', '-A', '4']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(
                    "#n s     l  c   q                    earliest"
                    "                      latest\n"
                    "AA 0407  -- LOG   2018-12-17T23:10:05.000000Z"
                    " 2018-12-17T23:10:05.000000Z")

        # ------------------------------------------------------------ #
        # test get_availability_percentage with station, no channel
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '4', '--station', '9001']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                with LogCapture() as log:
                    log.setLevel(logging.ERROR)
                    ph5availability.main()
                    out.compare('')
                    self.assertEqual(log.records[0].msg,
                                     "get_availability_percentage requires "
                                     "providing exact station/channel.")
        # test get_availability_percentage with channel, no station
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '4', '-c', 'DP2']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                with LogCapture() as log:
                    log.setLevel(logging.ERROR)
                    ph5availability.main()
                    out.compare('')
                    self.assertEqual(log.records[0].msg,
                                     "get_availability_percentage requires "
                                     "providing exact station/channel.")

        # test get_availability_percentage with channel, station=*
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '4', '-c', 'DP2',
                    '--station', '*']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                with LogCapture() as log:
                    log.setLevel(logging.ERROR)
                    ph5availability.main()
                    out.compare('')
                    self.assertEqual(log.records[0].msg,
                                     "get_availability_percentage requires "
                                     "providing exact station/channel.")

        # test get_availability_percentage with channel, station=*
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '4', '-c', 'DP1',
                    '--station', '500']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('[1.0, 0]')

        # test get_availability_percentage with station, channel, time
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '4', '--station', '9001',
                    '-s', '2019-02-22T15:39:03.0', '-c', 'DPZ',
                    '-e', '2019-02-22T15:40:03.0']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('[0.11666666666666667, 2]')
        # test get_availability_percentage with station, channel, time, and
        # array not match with other parameters
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '4', '-A', '3',
                    '--station', '0407', '-c', 'HHN']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare('[0.0, 0]')

        # ------------------------------------------------------------ #
        # test extent and text format
        # should return 10 channels
        # should match slc_full.txt from test data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3',
                    '-F', 't', '-S']
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.txt'),
                  'r') as content_file:
            content = content_file.read().strip()
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(content)

        # test extent and geocsv format
        # should return 10 channels
        # should match slc_full_geocsv.csv from test data
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3',
                    '-F', 'g', '-S']
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.csv'),
                  'r') as content_file:
            content = content_file.read().strip()
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(content)

        # test extent and text format
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3',
                    '-F', 't', '-S']
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.txt'),
                  'r') as content_file:
            content = content_file.read().strip()
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                out.compare(content)

        self.maxDiff = None
        # test extent and sync format
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3',
                    '-F', 's', '-S']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                output = out.captured.strip()

        i1 = output.find('\n')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.sync'),
                  'r') as content_file:
            content = content_file.read().strip()

        i2 = content.find('\n')
        self.assertMultiLineEqual(output[i1:], content[i2:])

        # test extent and json format
        testargs = ['ph5availability', '-n', 'master.ph5', '-p',
                    self.ph5test_path, '-a', '3',
                    '-F', 'j', '-S']
        with patch.object(sys, 'argv', testargs):
            with OutputCapture() as out:
                ph5availability.main()
                output = out.captured.strip()
        i1 = output.find('"datasources"')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.json'),
                  'r') as content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertMultiLineEqual(output[i1:], content[i2:])

    def test_convert_time(self):
        # convert list with epoch times at 3, 4
        ret = self.availability.convert_time(
            ['500', '', 'DP2', 1502294400.38, 1502294460.38])
        self.assertEqual(['500', '', 'DP2', '2017-08-09T16:00:00.380000Z',
                          '2017-08-09T16:01:00.380000Z'], ret)

        # convert list with FDSN time at 3, 4
        ret = self.availability.convert_time(
                    ['500', '', 'DP2', '2017-08-09T16:00:00.380000Z',
                     '2017-08-09T16:01:00.380000Z'])
        self.assertEqual(['500', '', 'DP2', '2017-08-09T16:00:00.380000Z',
                          '2017-08-09T16:01:00.380000Z'], ret)

        # convert list with epoch times at 2,3: wrong format
        self.assertRaises(
            ph5availability.PH5AvailabilityError,
            self.availability.convert_time,
            ['500', 'DP2', 1502294400.38, 1502294460.38])

        # send tuple instead of list to convert time
        self.assertRaises(
            ph5availability.PH5AvailabilityError,
            self.availability.convert_time,
            ('500', '', 'DP2', 1502294400.38, 1502294460.38))

    def test_get_channel(self):
        # get channel from station that lacks of info for channel
        ret = self.availability.get_channel({})
        self.assertEqual('DPX', ret)

        # get channel from station with enough info
        ret = self.availability.get_channel(
            {'seed_band_code_s': 'L', 'seed_instrument_code_s': 'O',
             'seed_orientation_code_s': 'G'})
        self.assertEqual('LOG', ret)

    def test_get_slc_info(self):
        arrayorder, arraybyid = self.availability.get_array_order_id(
            'Array_t_001')
        st = arraybyid['500'][1][0]

        # get any (sta,loc,chan) value from the st passed
        ret = self.availability.get_slc_info(st, '*', '*', '*')
        self.assertEqual(('500', '', 'DP1'), ret)
        # channel DP1 in st
        ret = self.availability.get_slc_info(st, '*', '*', 'DP1')
        self.assertEqual(('500', '', 'DP1'), ret)
        # station 500 in st
        ret = self.availability.get_slc_info(st, '500', '*', '*')
        self.assertEqual(('500', '', 'DP1'), ret)
        # channel DP2 not in st
        ret = self.availability.get_slc_info(st, '*', '*', 'DP2')
        self.assertEqual(-1, ret)
        # station 0407 not in st
        ret = self.availability.get_slc_info(st, '0407', '*', '*')
        self.assertEqual(-1, ret)
        # location 00 not in st
        ret = self.availability.get_slc_info(st, '*', '00', '*')
        self.assertEqual(-1, ret)

        # st without 'seed_station_name_s'
        st = {'id_s': '500'}
        ret = self.availability.get_slc_info(st, '500', '*', '*')
        self.assertEqual(('500', '', 'DPX'), ret)

        # st without station info
        st = {}
        self.assertRaises(
            ph5availability.PH5AvailabilityError,
            self.availability.get_slc_info, st, '500', '*', '*')

    def test_get_start(self):
        ret = self.availability.get_start(
            {'time/epoch_l': 1502294400, 'time/micro_seconds_i': 380000})
        self.assertEqual(1502294400.38, ret)

    def test_get_end(self):
        # samplerate != 0
        ret = self.availability.get_end(
            {'sample_count_i': 15000}, 1502294400.38, 500)
        self.assertEqual(1502294430.38, ret)

        # samplerate == 0
        ret = self.availability.get_end(
            {'sample_count_i': 15000}, 1502294400.38, 0)
        self.assertEqual(1502294400.38, ret)

    def test_get_sample_rate(self):
        # sample_rate_i != 0
        ret = self.availability.get_sample_rate(
            {'sample_rate_i': 100, 'sample_rate_multiplier_i': 1})
        self.assertEqual(100, ret)

        # sample_rate_i == 0
        ret = self.availability.get_sample_rate(
            {'sample_rate_i': 0, 'sample_rate_multiplier_i': 1})
        self.assertEqual(0, ret)

    def test_get_time_das_t(self):
        # start=None, end=None; no component, sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', None, None)
        self.assertEqual(1502294400.38, ret[0])
        self.assertEqual(1502294460.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0001',), ('Data_a_0002',), ('Data_a_0003',),
             ('Data_a_0004',), ('Data_a_0005',), ('Data_a_0006',)],
            ret[2]))
        # have start, end=None; no component, sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', 1502294431.38, None)
        self.assertEqual(1502294430.38, ret[0])
        self.assertEqual(1502294460.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0002', ), ('Data_a_0004', ), ('Data_a_0006', )],
            ret[2]))
        # start=None, have End; no component, sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', None, 1502294430)
        self.assertEqual(1502294400.38, ret[0])
        self.assertEqual(1502294430.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0001', ), ('Data_a_0003', ), ('Data_a_0005', )],
            ret[2]))
        # have start, end; no component, sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', 1502294431.38, 1502294455.38)
        self.assertEqual(1502294430.38, ret[0])
        self.assertEqual(1502294460.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0002', ), ('Data_a_0004', ), ('Data_a_0006', )],
            ret[2]))
        # start=None, end=None; have component, no sample_rate
        ret = self.availability.get_time_das_t(
            '3X500', None, None, 1)
        self.assertEqual(1502294400.38, ret[0])
        self.assertEqual(1502294460.38, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_0001', ), ('Data_a_0002', )],
            ret[2]))
        # start=None, end=None; have component, sample_rate
        ret = self.availability.get_time_das_t(
            '5553', None, None, 1, 100)
        self.assertEqual(1545085230.681998, ret[0])
        self.assertEqual(1545085240.691998, ret[1])
        self.assertTrue(checkFieldsMatch(
            ['array_name_data_a'],
            [('Data_a_00002', )],
            ret[2]))
        # start > latest
        ret = self.availability.get_time_das_t(
                    '5553', 1545085241.0, None, 1, 100)
        self.assertEqual(-1, ret)
        # end < earliest
        ret = self.availability.get_time_das_t(
                    '5553', None, 1545085230.0, 1, 100)
        self.assertEqual(-1, ret)
        # start=None, end=None; no component, have sample_rate
        self.assertRaises(
            ph5availability.PH5AvailabilityError,
            self.availability.get_time_das_t,
            '5553', None, None, None, 100)
        self.assertEqual(-1, ret)
        # start=None, end=None; have component, have false sample_rate
        ret = self.availability.get_time_das_t(
            '5553', None, None, 1, 500)
        self.assertEqual(-1, ret)

    def test_get_sampleNos_gapOverlap(self):
        st = {'deploy_time/micro_seconds_i': 0,
              'deploy_time/epoch_l': 1550849940,
              'pickup_time/epoch_l': 1550850240,
              'pickup_time/micro_seconds_i': 0}

        # 3 gaps inside
        das_t = [{'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849943},  # end: 1550849949
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849973},  # end: 1550849974
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550850003},  # end: 1550850009
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550850033}]  # end: 1550850034

        ret = self.availability.get_sampleNos_gapOverlap(
            das_t, 1550849943.0, 1550850034.0, None, None, 500, st)
        self.assertEqual((45500, 7000, 3), ret)

        # 1 gap bw traces 3 & 4; 1 at the beginning; 1 at the end
        das_t = [{'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849943},  # end: 1550849949
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849949},  # end: 1550849950
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849950},  # end: 1550849956
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550850033}]  # end: 1550850034
        ret = self.availability.get_sampleNos_gapOverlap(
            das_t, 1550849943.0, 1550850034.0, 1550849942, 1550850035, 500, st)
        self.assertEqual((46500, 7000, 3), ret)

        # 1 overlap bw traces 2 & 3; 1 gap bw 3 & 4;
        # 1 at beginning, 1 at the end
        das_t = [{'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849943},  # end: 1550849949
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849949},  # end: 1550849950
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 3000, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550849947},  # end: 1550849953
                 {'time/micro_seconds_i': 0, 'sample_rate_i': 500,
                  'sample_count_i': 500, 'sample_rate_multiplier_i': 1,
                  'time/epoch_l': 1550850033}]  # end: 1550850034
        ret = self.availability.get_sampleNos_gapOverlap(
            das_t, 1550849943.0, 1550850034.0, 1550849942, 1550850035, 500, st)
        self.assertEqual((46500, 7000.0, 4), ret)

    def test_get_array_order_id(self):
        ret = self.availability.get_array_order_id('Array_t_009')
        self.assertEqual(['9001'], ret[0])
        self.assertTrue(1, len(ret[1]))
        self.assertTrue('9001' in ret[1].keys())

        # array_name not exist
        self.assertRaises(
            ph5availability.PH5AvailabilityError,
            self.availability.get_array_order_id,
            'Array_t_010')

    def test_get_text_report(self):
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_text_report(result).strip()
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.txt'),
                  'r') as content_file:
            content = content_file.read().strip()
        self.assertMultiLineEqual(ret, content)

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1,
            include_sample_rate=True)
        ret = self.availability.get_text_report(result).strip()
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/avail_time.txt'),
                  'r') as content_file:
            content = content_file.read().strip()
        self.assertMultiLineEqual(ret, content)

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1)
        ret = self.availability.get_text_report(result).strip()
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/avail_time_noSR.txt'),
                  'r') as content_file:
            content = content_file.read().strip()
        self.assertMultiLineEqual(ret, content)

    def test_print_report(self):
        self.availability.OFILE = None
        with OutputCapture() as out:
            self.availability.print_report("this is a text line")
            out.compare("this is a text line")

        self.availability.OFILE = open("test", 'w')
        with OutputCapture() as out:
            self.availability.print_report("this is a text line")
            out.compare("")
        self.assertTrue(self.availability.OFILE.closed)
        with open('test', 'r') as content_file:
            content = content_file.read().strip()
        self.assertEqual(content, "this is a text line")

    def test_get_geoCSV_report(self):
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_geoCSV_report(result).strip()
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.csv'),
                  'r') as content_file:
            content = content_file.read().strip()
        self.assertMultiLineEqual(ret, content)

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1,
            include_sample_rate=True)
        ret = self.availability.get_geoCSV_report(result).strip()
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/avail_time.csv'),
                  'r') as content_file:
            content = content_file.read().strip()
        self.assertMultiLineEqual(ret, content)

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1)
        ret = self.availability.get_geoCSV_report(result).strip()
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/avail_time_noSR.csv'),
                  'r') as content_file:
            content = content_file.read().strip()
        self.assertMultiLineEqual(ret, content)

    def test_get_sync_report(self):
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_sync_report(result).strip()
        i1 = ret.find('\n')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.sync'),
                  'r') as content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertMultiLineEqual(ret[i1:], content[i2:])

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1,
            include_sample_rate=True)
        ret = self.availability.get_sync_report(result).strip()
        i1 = ret.find('\n')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/avail_time.sync'),
                  'r'
                  ) as content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertMultiLineEqual(ret[i1:], content[i2:])

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1)
        ret = self.availability.get_sync_report(result).strip()
        i1 = ret.find('\n')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/avail_time_noSR.sync'),
                  'r') as content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertMultiLineEqual(ret[i1:], content[i2:])

    def test_get_json_report(self):
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_json_report(result).strip()
        i1 = ret.find('"datasources"')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.json'),
                  'r') as content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertMultiLineEqual(ret[i1:], content[i2:])

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1,
            include_sample_rate=True)
        ret = self.availability.get_json_report(result).strip()
        i1 = ret.find('"datasources"')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/avail_time.json'),
                  'r') as content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertMultiLineEqual(ret[i1:], content[i2:])

        result = self.availability.get_availability(
            starttime=1545088205.0, endtime=1550849943.1)
        ret = self.availability.get_json_report(result).strip()
        i1 = ret.find('"datasources"')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/avail_time_noSR.json'),
                  'r') as content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertMultiLineEqual(ret[i1:], content[i2:])

        # wrong format result
        result = [('0407', 'LOG', 1545088205.0, 1545088205.0)]
        self.assertRaises(
            ph5availability.PH5AvailabilityError,
            self.availability.get_json_report,
            result)

    def test_get_report(self):
        result = self.availability.get_availability_extent(
            include_sample_rate=True)
        ret = self.availability.get_report(result, format='t').strip()
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.txt'),
                  'r') as content_file:
            content = content_file.read().strip()
        self.assertMultiLineEqual(ret, content)

        ret = self.availability.get_report(result, format='g').strip()
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.csv'),
                  'r') as content_file:
            content = content_file.read().strip()
        self.assertMultiLineEqual(ret, content)

        ret = self.availability.get_report(result, format='s').strip()
        i1 = ret.find('\n')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.sync'),
                  'r') as content_file:
            content = content_file.read().strip()
        i2 = content.find('\n')
        self.assertMultiLineEqual(ret[i1:], content[i2:])

        ret = self.availability.get_report(result, format='j').strip()
        i1 = ret.find('"datasources"')
        with open(os.path.join(self.home,
                               'ph5/test_data/metadata/extent_full.json'),
                  'r') as content_file:
            content = content_file.read().strip()
        i2 = content.find('"datasources"')
        self.assertMultiLineEqual(ret[i1:], content[i2:])

        with LogCapture() as log:
            ret = self.availability.get_report(result, format='k')
            self.assertEqual(ret, result)
            self.assertEqual(log.records[0].msg,
                             "The entered format k is not supported.")


class TestPH5AvailabilitySampleRate(LogTestCase, TempDirTestCase):
    def setUp(self):
        super(TestPH5AvailabilitySampleRate, self).setUp()

        self.ph5test_path_sr = os.path.join(self.home,
                                            'ph5/test_data/ph5/samplerate')
        self.ph5_sr = ph5api.PH5(path=self.ph5test_path_sr,
                                 nickname='master.ph5')
        self.sr_avail = ph5availability.PH5Availability(self.ph5_sr)

    def tearDown(self):
        self.ph5_sr.close()
        super(TestPH5AvailabilitySampleRate, self).tearDown()

    def test_ms_samplerate(self):
        ph5toms = PH5toMSeed(self.ph5_sr)
        ph5toms.process_all()
        cuts = ph5toms.create_cut_list()
        for cut in cuts:
            trace = ph5toms.create_trace(cut)
            if trace is not None:
                self.assertEqual(trace[0].stats.station, '10075')

    def test_availability_samplerate(self):
        with LogCapture() as log:
            ret = self.sr_avail.get_availability(station='10075',
                                                 channel='*',
                                                 starttime=None,
                                                 endtime=None,
                                                 include_sample_rate=True)
            self.assertEqual(6, len(ret))
            self.assertIsNotNone(log)
        # Checks the sample rate of the test data set
        self.assertEqual(500.0, ret[0][5])
        ret2 = self.sr_avail.get_availability_extent(station='10075',
                                                     channel='*',
                                                     starttime=None,
                                                     endtime=None,
                                                     include_sample_rate=True)
        self.assertEqual(3, len(ret2))
        self.assertEqual(500.0, ret2[0][5])
        with LogCapture() as log2:
            ret2 = self.sr_avail.get_availability_extent(station='10075',
                                                         channel='*',
                                                         starttime=None,
                                                         endtime=None)
            self.assertIsNotNone(log2)


class TestPH5AvailabilitySampleRate_error(LogTestCase, TempDirTestCase):
    def test_availability_error(self):
        self.ph5_path_eror = os.path.join(self.home,
                                          'ph5/test_data/ph5/samplerate/error')
        self.ph5_sr_error = ph5api.PH5(path=self.ph5_path_eror,
                                       nickname='master.ph5')
        self.avail_error = ph5availability.PH5Availability(self.ph5_sr_error)
        with LogCapture() as log_error:
            self.avail_error.get_availability(station='10075',
                                              channel='*',
                                              starttime=None,
                                              endtime=None,
                                              include_sample_rate=True)
            self.assertEqual(log_error.records[1].msg,
                             'DAS and Array Table sample rates do'
                             ' not match, DAS table sample rates'
                             ' do not match. Data must be'
                             ' updated.')
        self.ph5_sr_error.close()


class TestAvailability_DateRange(LogTestCase, TempDirTestCase):
    # Verifies that the availability services is
    # outputting a time stamp based on metadata epoch
    # rather than the timeseries data that is past
    # the metadta epoch. Test is asso
    def test_CompareMS_Availability(self):
        self.ph5path = os.path.join(self.home,
                                    'ph5/test_data/ph5/availability_extent')
        self.ph5_object = ph5api.PH5(path=self.ph5path,
                                     nickname='master.ph5')
        self.avail = ph5availability.PH5Availability(self.ph5_object)
        tt = self.avail.get_availability(station='8001',
                                         channel='HLZ',
                                         starttime=None,
                                         endtime=None,
                                         include_sample_rate=True)
        self.assertEqual(tt[0][3], 1463568490)
        self.assertEqual(tt[0][4], 1463568500)
        self.ph5_object.close()


class TestCompareMS_Availability(LogTestCase, TempDirTestCase):
    def test_CompareMS_Availability(self):
        self.ph5path = os.path.join(self.home,
                                    'ph5/test_data/ph5/availability')
        self.ph5_object = ph5api.PH5(path=self.ph5path,
                                     nickname='master.ph5')
        self.avail = ph5availability.PH5Availability(self.ph5_object)
        tt = self.avail.get_availability(station='10075',
                                         channel='*',
                                         starttime=None,
                                         endtime=None,
                                         include_sample_rate=True)
        ph5toms = PH5toMSeed(self.ph5_object)
        ph5toms.process_all()
        cuts = ph5toms.create_cut_list()
        i = 0
        for cut in cuts:
            trace = ph5toms.create_trace(cut)

            if trace is not None:
                if i >= 1:
                    self.assertEqual(tt[i][3],
                                     round(trace[0].stats.starttime))
                    self.assertEqual(tt[i][4],
                                     round(trace[0].stats.endtime))
                i = i+1
        self.ph5_object.close()


class TestPH5Availability_SMR(LogTestCase, TempDirTestCase):
    def assert_main(self, testargs, errmsg):
        with patch.object(sys, 'argv', testargs):
            with LogCapture() as log:
                log.setLevel(logging.ERROR)
                ph5availability.main()
        self.assertEqual(len(log.records), 1)
        self.assertEqual(log.records[0].msg, errmsg)

    def test_main_no_srm(self):
        '''
        test column sample_rate_multiplier_i missing
        '''
        # Both Array_t and Das_t missing srm, but Array_t will be checked first
        # get_array_order_id() will throw error when it reads array
        nosrmpath = os.path.join(self.home,
                                 'ph5/test_data/ph5_no_srm/array_das')
        testargs = ['ph5availability', '-n', 'master.ph5', '-p', nosrmpath,
                    '-a', '2', '--station', '1111']
        self.assert_main(
            testargs,
            'Array_t_001 has sample_rate_multiplier_i missing. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

        # Only Das_t missing srm (this doesn't happen in reality but need to
        # test to see if it works)

        # query_das_t() inside get_availability will throw error
        nosrmpath = os.path.join(self.home,
                                 'ph5/test_data/ph5_no_srm/das')
        testargs = ['ph5availability', '-n', 'master.ph5', '-p', nosrmpath,
                    '-a', '2', '--station', '1111']
        self.assert_main(
            testargs,
            'Das_t_1X1111 has sample_rate_multiplier_i missing. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

        # get_time_das_t() inside has_data will throw error
        testargs = ['ph5availability', '-n', 'master.ph5', '-p', nosrmpath,
                    '-a', '0']
        self.assert_main(
            testargs,
            'Das_t_1X1111 has sample_rate_multiplier_i missing. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

    def test_main_srm0(self):
        '''
        test column sample_rate_multiplier_i=0,
        '''
        # Both Array_t and Das_t missing srm, but Array_t will be checked first
        # get_array_order_id() will throw error when it reads array
        nosrmpath = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/array_das')

        testargs = ['ph5availability', '-n', 'master.ph5', '-p', nosrmpath,
                    '-a', '2', '--station', '1111']
        self.assert_main(
            testargs,
            'Array_t_001 has sample_rate_multiplier_i with value 0. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

        # Only Das_t missing srm (this doesn't happen in reality but need to
        # test to see if it works)

        # query_das_t() inside get_availability will throw error
        nosrmpath = os.path.join(
            self.home,
            'ph5/test_data/ph5/sampleratemultiplier0/das')
        testargs = ['ph5availability', '-n', 'master.ph5', '-p', nosrmpath,
                    '-a', '2', '--station', '1111']
        self.assert_main(
            testargs,
            'Das_t_1X1111 has sample_rate_multiplier_i with value 0. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')

        # get_time_das_t() inside has_data will throw error
        testargs = ['ph5availability', '-n', 'master.ph5', '-p', nosrmpath,
                    '-a', '0']
        self.assert_main(
            testargs,
            'Das_t_1X1111 has sample_rate_multiplier_i with value 0. '
            'Please run fix_srm to fix sample_rate_multiplier_i for PH5 data.')


if __name__ == "__main__":
    unittest.main()
