# Derick Hess, Feb 2019
# Tim Ronan, Oct 2020

"""
Implements IRIS webservice style extent and query
for data availability in a PH5 archive.
"""

import os
import sys
import logging
import argparse
import datetime as dt
import time
from uuid import uuid4
from argparse import RawTextHelpFormatter

from ph5.core import ph5api, ph5utils, timedoy, experiment

PROG_VERSION = '2020.282'
LOGGER = logging.getLogger(__name__)


f_id = {'sta': 0, 'loc': 1, 'chan': 2,
        'earliest': 3, 'latest': 4, 'sRate': 5}


class PH5AvailabilityError(Exception):
    """Exception raised when there is a problem with the request."
    """
    pass


class PH5Availability(object):
    """
    Availability methods for Ph5 archive
    """

    def __init__(self, ph5API_object):
        """
        Initializes PH5Availability
        :type  :class core.ph5api
        :param object containg PH5 instance
        TODO: ADD ALL PARAMATERS NEEDED
        """
        self.ph5 = ph5API_object
        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()
        if not self.ph5.Experiment_t:
            self.ph5.read_experiment_t()
            self.netcode = self.ph5.Experiment_t['rows'][0]['net_code_s']
        self.array = None
        self.sta_len = 1
        self.tim_len = 27
        self.avail = 2
        return

    def analyze_args(self, args):
        try:
            self.station_ids = ph5utils.parse_ph5_componentid(args.sta_id_list)
            if self.station_ids:
                self.stations = self.station_ids
            else:
                self.stations = ph5utils.parse_seed_station(args.sta_list)
            if not self.stations:
                self.stations = ["*"]
            self.locations = ph5utils.parse_seed_location(args.location)
            if not self.locations:
                self.locations = ["*"]
            self.channels = ph5utils.parse_seed_channel(args.channel)
            if not self.channels:
                self.channels = ["*"]

            self.starttime = ph5utils.parse_date(args.start_time)
            self.endtime = ph5utils.parse_date(args.end_time)
        except ValueError as e:
            raise PH5AvailabilityError(e)

        if self.starttime:
            self.starttime = (self.starttime -
                              dt.datetime.fromtimestamp(0)).total_seconds()

        if self.endtime:
            self.endtime = (self.endtime -
                            dt.datetime.fromtimestamp(0)).total_seconds()

        self.array = args.array_t_
        if args.avail not in [0, 1, 2, 3, 4]:
            raise PH5AvailabilityError(
                "There is no avail option '%s'. Please run "
                "ph5availability -h for more information.")

        self.avail = args.avail

        self.SR_included = False
        if args.samplerate:
            if self.avail in [2, 3]:
                self.SR_included = True

        self.format = args.format
        if self.format and self.avail not in [2, 3]:
            LOGGER.warning("Format only apply for avail modes 2 or 3.")
        elif not self.format:
            self.format = "t"  # default to text format

        # define OFILE to write output
        o_filename = args.output_file
        self.OFILE = None
        if o_filename is not None:
            if self.avail not in [2, 3]:
                LOGGER.warning("Print to file only apply for aval 2 or 3.")
            elif self.format is None:
                LOGGER.warning("No format given.")
            else:
                self.OFILE = open(o_filename, 'w')

        return True

    def get_channel(self, st_data):
        if 'seed_band_code_s' in st_data:
            band_code = st_data['seed_band_code_s']
        else:
            band_code = "D"
        if 'seed_instrument_code_s' in st_data:
            instrument_code = st_data['seed_instrument_code_s']
        else:
            instrument_code = "P"
        if 'seed_orientation_code_s' in st_data:
            orientation_code = st_data['seed_orientation_code_s']
        else:
            orientation_code = "X"

        seed_cha_code = band_code + instrument_code + orientation_code

        return seed_cha_code

    def get_slc_info(self, st_data, station, location, channel):
        ph5_seed_station = ''
        ph5_loc = ''
        ph5_channel = ''
        if 'seed_station_name_s' in st_data:
            ph5_seed_station = st_data['seed_station_name_s']
        elif 'id_s' in st_data:
            ph5_seed_station = st_data['id_s']
        else:
            raise PH5AvailabilityError(
                "PH5 data lacks of station information.")
        if len(ph5_seed_station) > self.sta_len:
            # get the max len of station for space in report
            self.sta_len = len(ph5_seed_station)

        if not ph5utils.does_pattern_exists(
           [station], ph5_seed_station):
            return -1

        ph5_channel = self.get_channel(st_data)
        if not ph5utils.does_pattern_exists(
           [channel], ph5_channel):
            return -1

        if 'seed_location_code_s' in st_data:
            ph5_loc = st_data['seed_location_code_s']
        else:
            ph5_loc = ""
        if not ph5utils.does_pattern_exists(
           [location], ph5_loc):
            return -1

        return ph5_seed_station, ph5_loc, ph5_channel

    def get_array_order_id(self, array_name):
        self.ph5.read_array_t(array_name)
        try:
            arraybyid = self.ph5.Array_t[array_name]['byid']
            arrayorder = self.ph5.Array_t[array_name]['order']
        except KeyError:
            raise PH5AvailabilityError(
                "There is no array table '%s'." % array_name)

        return arrayorder, arraybyid

    def get_time_das_t(self, das, start, end,
                       component=None, sample_rate=None):
        """
        para das: name of das
        para start: start time, can be none
        para end: end time, can be none
        component: channel number, default none
        sample_rate: default none
        return
           + earliest_epoch, latest epoch: time range for channel
           + new_das_t: list of data for das in the given time range(start-end)
                (all channel or only the channel required)
        if component and sample_rate=None, doesn't care about channel,
        this function only for checking if the start and end time given is
        in the time range of this das or not. Useful only when channel is *
        for has data so don't need to check each channel.
        """
        s = 0 if start is None else start
        e = 32509613590 if end is None else end
        if start is None and end is None:
            rangestr = ""
        elif start is None:
            rangestr = " before %s " % end
        elif end is None:
            rangestr = " after %s " % start
        else:
            rangestr = " in range %s - %s " % (start, end)

        if sample_rate is not None:
            if component is None:
                raise PH5AvailabilityError(
                    "get_time_das_t requires component when "
                    "sample_rate is given")

            Das_t = self.ph5.query_das_t(
                das,
                chan=component,
                start_epoch=s,
                stop_epoch=e,
                sample_rate=sample_rate)
            if not Das_t:
                LOGGER.warning(
                    "No Das table found for %s %s for "
                    "component: %s, samplerate:%s"
                    % (das, rangestr, component, sample_rate))
                return -1
        else:
            # include all channelnum and sample_rate
            self.ph5.read_das_t(das, s, e, reread=False)
            if das not in self.ph5.Das_t:
                LOGGER.warning("No Das table found for %s %s"
                               % (das, rangestr))
                return -1
            Das_t = self.ph5.Das_t[das]['rows']

            if component is not None:
                # include all sample_rate
                Das_t = ph5api.filter_das_t(Das_t, component)
        new_das_t = sorted(Das_t, key=lambda k: k['time/epoch_l'])

        # if not new_das_t:
        #    LOGGER.warning("No Das table found for %s %s" % (das, rangestr))
        #    self.ph5.forget_das_t(das)
        #    return -1

        earliest_epoch = self.get_start(new_das_t[0])

        latest_epoch_start = self.get_start(new_das_t[-1])
        true_sample_rate = self.get_sample_rate(new_das_t[-1])
        latest_epoch = self.get_end(new_das_t[-1], latest_epoch_start,
                                    true_sample_rate)

        # don't need to compare start with latest_epoch (following lines)
        # because this case has been filtered out with read_das_t()
        # and query_das_t => comment out to exclude from testing
        # if start is not None and start > latest_epoch:
        #    self.ph5.forget_das_t(das)
        #    return -1
        #  for the case end = time/epoch_l if there is time/micro_seconds_i,
        #  this seem to not be considered correctly in ph5
        if end is not None and end < earliest_epoch:
            self.ph5.forget_das_t(das)
            return -1
        self.ph5.forget_das_t(das)
        return earliest_epoch, latest_epoch, new_das_t

    def get_slc(self, station='*', location='*', channel='*',
                starttime=None, endtime=None, include_sample_rate=False):
        """
        Get a list of tuples [(sta, loc, cha),...] containing information
        on what streams are included in PH5.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: list(tuple(str, str, str, str))
        :returns: A list of tuples [(station, location, channel)...]
            containing information on what streams are included in PH5 archive.
        """
        slc = []

        array_names = sorted(self.ph5.Array_t_names)
        for array_name in array_names:
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
            ret = self.get_array_order_id(array_name)

            arrayorder, arraybyid = ret

            for ph5_station in arrayorder:

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]
                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue
                        ph5_seed_station, ph5_loc, ph5_channel = ret

                        ph5_das = st['das/serial_number_s']
                        ph5_channum = st['channel_number_i']
                        ph5_sample_rate = self.get_sample_rate(st)
                        tup = (ph5_seed_station,
                               ph5_loc, ph5_channel)
                        if tup not in slc:
                            ret = self.get_time_das_t(
                                ph5_das, starttime, endtime,
                                ph5_channum, ph5_sample_rate)
                            if ret == -1:
                                continue
                            slc.append(tup)

        return slc

    def get_availability_extent(self, station='*', location='*',
                                channel='*', starttime=None, endtime=None,
                                include_sample_rate=False):
        """
        Get a list of tuples [(station, location, channel,
        early, end)] containing data extent info for time series
        included in PH5.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: list(tuple(str, str, str, str, float, float))
        :returns: A list of tuples [(station, location, channel,
            early, end)...] containing data extent info for time series
            included in PH5 archive
        NOTE! ph5api as a get_extent() method that works on the channel level.
        Leverage this
        """
        availability_extents = []
        self.das_time = {}
        sr_mismatch = False
        empty_times = True
        self.SR_included = include_sample_rate
        if starttime or endtime:
            if not (starttime and endtime):
                raise ValueError("if start or end, both are required")

        array_names = sorted(self.ph5.Array_t_names)

        for array_name in array_names:
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
            ret = self.get_array_order_id(array_name)

            arrayorder, arraybyid = ret

            for ph5_station in arrayorder:

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    # Build a for loop to solve for the das time extent
                    # The first loop is necessary to determine full time
                    # extent
                    for st_num in range(0, station_len):
                        stat = station_list[deployment][st_num]
                        d = stat['das/serial_number_s']
                        c = stat['channel_number_i']
                        spr = stat['sample_rate_i']
                        key = (d, c, spr)
                        if key not in self.das_time.keys():
                            self.das_time[key] = {'time_windows': []}
                        self.das_time[key]['time_windows'].append(
                            (stat['deploy_time/epoch_l'],
                             stat['pickup_time/epoch_l'],
                             stat['id_s']))
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]

                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue
                        ph5_seed_station, ph5_loc, ph5_channel = ret
                        ph5das = st['das/serial_number_s']
                        chanum = st['channel_number_i']
                        # Seem to be replacing a channel time with a
                        # stationtime. Replace in DAS group
                        ph5_start_epoch = st['deploy_time/epoch_l']
                        ph5_stop_epoch = st['pickup_time/epoch_l']
                        ph5_sample_rate = st['sample_rate_i']
                        ph5_multiplier = st['sample_rate_multiplier_i']
                        samplerate_return = None
                        Das_t = self.ph5.query_das_t(
                            ph5das,
                            chan=chanum,
                            start_epoch=ph5_start_epoch,
                            stop_epoch=ph5_stop_epoch,
                            sample_rate=ph5_sample_rate,
                            sample_rate_multiplier=ph5_multiplier,
                            check_samplerate=False)
                        # Find key that corresponds to the das
                        for key in self.das_time.keys():
                            if (key[0] == ph5das and
                               key[1] == chanum and
                               key[2] == ph5_sample_rate):
                                dt = self.das_time[key]
                                dt['time_windows'].sort()
                                start_chan_epoch = dt['time_windows'][0][0]
                                end_chan_epoch = dt['time_windows'][-1][1]
                        for das in Das_t:
                            if das['sample_rate_i'] == st['sample_rate_i']:
                                samplerate_return = das['sample_rate_i']
                                psr = das['sample_rate_i']
                                early, end = self.ph5.get_extent(ph5das,
                                                                 chanum,
                                                                 psr,
                                                                 starttime,
                                                                 endtime
                                                                 )
                                empty_times = False
                            else:
                                continue
                        if empty_times is True:
                            for i, das in enumerate(Das_t):
                                # Checks to see if all DAS tables have same SR
                                sr_prev = Das_t[i-1]['sample_rate_i']
                                if das['sample_rate_i'] != sr_prev:
                                    sr_mismatch = True
                            try:
                                if sr_mismatch is True:
                                    LOGGER.error('DAS and Array Table sample' +
                                                 ' rates do not match, DAS' +
                                                 ' table sample rates do not' +
                                                 ' match. Data must be'
                                                 ' updated.')
                                    return
                                else:
                                    # Uses SR if consistent
                                    samplerate_return = das['sample_rate_i']
                                    psr = das['sample_rate_i']
                                    LOGGER.warning('Using sample rate from' +
                                                   ' DAS Table. Sample rates' +
                                                   ' in DAS and Array tables' +
                                                   ' are not consistent.')
                                    early, end = self.ph5.get_extent(ph5das,
                                                                     chanum,
                                                                     psr,
                                                                     starttime,
                                                                     endtime
                                                                     )
                            except(UnboundLocalError):
                                continue
                        if early is None or end is None:
                            continue
                        # trim user defined time range if it extends beyond the
                        # deploy/pickup times
                        # Logic to fix the deploy time error
                        if starttime is not None and early < starttime:
                            early = starttime
                        if endtime is not None and endtime < end:
                            end = endtime
                        # Start channel trim
                        if float(early) < float(start_chan_epoch):
                            early = start_chan_epoch
                        if float(end) > float(end_chan_epoch):
                            end = end_chan_epoch
                        # End of channel trim
                        if early is None or end is None:
                            return None
                        if not include_sample_rate:
                            tup = (ph5_seed_station, ph5_loc, ph5_channel,
                                   early, end)
                        else:
                            if samplerate_return is not None:
                                tup = (ph5_seed_station, ph5_loc, ph5_channel,
                                       early, end,
                                       float(samplerate_return))
                            else:
                                tup = (ph5_seed_station, ph5_loc, ph5_channel,
                                       early, end, float(psr)
                                       )
                        availability_extents.append(tup)

        return availability_extents

    def get_availability(self, station='*', location='*',
                         channel='*', starttime=None, endtime=None,
                         include_sample_rate=False):
        """
        Get a list of tuples [(station, location, channel,
        starttime, endtime),...] containing data availability info for
        time series included in the tsindex database.
        If ``include_sample_rate=True``, then a tuple containing the sample
        rate [(sta, loc, cha, start, end, sample_rate),...] is returned.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: :class:`~obspy.core.utcdatetime.UTCDateTime`
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :type include_sample_rate: bool
        :param include_sample_rate: If ``include_sample_rate=True``, then
            a tuple containing the sample rate [(sta, loc, cha,
            start, end, sample_rate),...] is returned.
        :rtype: list(tuple(str, str, str, str, str, str))
        :returns: A list of tuples [(station, location, channel,
            earliest, latest)...] representing contiguous time spans for
            selected channels and time ranges.
        NOTE! ph5api as a get_availability()
        method that works on the channel level. Leverage this
        """
        availability = []
        time = []
        sr_mismatch = False
        empty_times = True
        self.das_time = {}
        self.SR_included = include_sample_rate
        array_names = sorted(self.ph5.Array_t_names)
        for array_name in array_names:
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
            ret = self.get_array_order_id(array_name)

            arrayorder, arraybyid = ret

            for ph5_station in arrayorder:

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    # Build a for loop to solve for the das time extent
                    # The first loop is necessary to determine full time
                    # extent
                    for st_num in range(0, station_len):
                        stat = station_list[deployment][st_num]
                        d = stat['das/serial_number_s']
                        c = stat['channel_number_i']
                        spr = stat['sample_rate_i']
                        key = (d, c, spr)
                        if key not in self.das_time.keys():
                            self.das_time[key] = {'time_windows': []}
                        self.das_time[key]['time_windows'].append(
                            (stat['deploy_time/epoch_l'],
                             stat['pickup_time/epoch_l'],
                             stat['id_s']))
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]
                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue
                        ph5_seed_station, ph5_loc, ph5_channel = ret
                        ph5_das = st['das/serial_number_s']
                        channum = st['channel_number_i']
                        ph5_start_epoch = st['deploy_time/epoch_l']
                        ph5_stop_epoch = st['pickup_time/epoch_l']
                        ph5_sample_rate = st['sample_rate_i']
                        ph5_multiplier = st['sample_rate_multiplier_i']
                        Das_t = self.ph5.query_das_t(
                            ph5_das,
                            chan=channum,
                            start_epoch=ph5_start_epoch,
                            stop_epoch=ph5_stop_epoch,
                            sample_rate=ph5_sample_rate,
                            sample_rate_multiplier=ph5_multiplier,
                            check_samplerate=False)
                        # Find key that corresponds to the das
                        for key in self.das_time.keys():
                            if (key[0] == ph5_das and
                               key[1] == channum and
                               key[2] == ph5_sample_rate):
                                dt = self.das_time[key]
                                dt['time_windows'].sort()
                                start_chan_epoch = dt['time_windows'][0][0]
                                end_chan_epoch = dt['time_windows'][-1][1]
                        for das in Das_t:
                            # Does Array.sr == DAS.sr? If so use sr
                            if das['sample_rate_i'] == st['sample_rate_i']:
                                samplerate_return = das['sample_rate_i']
                                ph5_sr = das['sample_rate_i']
                                time = self.ph5.get_availability(ph5_das,
                                                                 ph5_sr,
                                                                 channum,
                                                                 starttime,
                                                                 endtime)
                                empty_times = False
                            else:
                                continue
                        if empty_times is True:
                            for i, das in enumerate(Das_t):
                                # IF DAS.SR != Array.SR, USe DAS.SR if match
                                # Checks to see if all DAS tables have same SR
                                sr_prev = Das_t[i-1]['sample_rate_i']
                                if das['sample_rate_i'] != sr_prev:
                                    sr_mismatch = True
                            try:
                                if sr_mismatch is True:
                                    # Else throw warning and fail
                                    LOGGER.error('DAS and Array Table sample' +
                                                 ' rates do not match, DAS' +
                                                 ' table sample rates do not' +
                                                 ' match. Data must be'
                                                 ' updated.')
                                    return
                                else:
                                    # Uses SR if consistent
                                    samplerate_return = das['sample_rate_i']
                                    ph5_sr = das['sample_rate_i']
                                    LOGGER.warning('Using sample rate from' +
                                                   ' DAS Table. Sample rates' +
                                                   ' in DAS and Array tables' +
                                                   ' are not consistent.')
                                    time = self.ph5.get_availability(ph5_das,
                                                                     ph5_sr,
                                                                     channum,
                                                                     starttime,
                                                                     endtime)
                            except(UnboundLocalError):
                                continue
                        if time is None:
                            continue
                        for T in time:
                            start = T[1] if T[1] > starttime \
                                or starttime is None else starttime
                            end = T[2] if T[2] < endtime \
                                or endtime is None else endtime
                            if float(start) < float(start_chan_epoch):
                                start = start_chan_epoch
                            if float(end) > float(end_chan_epoch):
                                end = end_chan_epoch
                            if T[1] is None or T[2] is None:
                                return None
                            if include_sample_rate:
                                if samplerate_return is not None:
                                    availability.append((
                                        ph5_seed_station, ph5_loc, ph5_channel,
                                        start, end, float(samplerate_return)))
                                elif(T[0] is None):
                                    availability.append((
                                        ph5_seed_station, ph5_loc, ph5_channel,
                                        start, end, float(ph5_sr)))
                                else:
                                    availability.append((
                                        ph5_seed_station, ph5_loc, ph5_channel,
                                        start, end, float(T[0])))
                            else:
                                availability.append((
                                    ph5_seed_station, ph5_loc, ph5_channel,
                                    start, end))
        return availability

    def get_start(self, das_t):
        return float(das_t['time/epoch_l']) + \
            float(das_t['time/micro_seconds_i'])/1000000

    def get_end(self, das_t, start, samplerate):
        if samplerate != 0:
            duration = float(das_t['sample_count_i']) / samplerate
        else:
            duration = 0
        return start + duration

    def get_sample_rate(self, st):
        if st['sample_rate_i'] == 0:
            return 0
        return float(st['sample_rate_i']) / \
            float(st['sample_rate_multiplier_i'])

    def get_sampleNos_gapOverlap(self, das_t, earliest, latest, start, end,
                                 sample_rate, st):
        """
        time range: (start, end); use use (earliest, latest) if not given
        das_t: only have the traces in the time range
        earliest: earliest time of traces in das_t
        latest: latest time of traces in das_t
        all the parameters are already processed before sending to
        get_sampleNos_gapOverlap() => no need to check or calc. again
        return:
           + expected_sampleNo: number of samples expected for the time range
           + sampleNo: number of samples recorded for the time range
           + gapOverlap: total gaps and overlaps in the time range
               gap: end time of one trace < start time of next trace
                    start < start time of first trace
                    end > end time of last trace
               overlap: end time of one trace > start time of next trace
        """
        if start is None:
            start = earliest
        if end is None:
            end = latest
        # calculate expected_sampleNo
        gapOverlap = 0
        if start < earliest:
            gapOverlap += 1
        if latest < end:
            gapOverlap += 1
        else:
            latest = end

        expected_sampleNo = (end - start) * sample_rate

        sampleNo = 0
        i = -1
        for i in range(len(das_t) - 1):
            sampleNo += das_t[i]['sample_count_i']
            start_time = self.get_start(das_t[i])
            end_time = self.get_end(das_t[i], start_time, sample_rate)
            next_start_time = self.get_start(das_t[i+1])
            if end_time != next_start_time:
                gapOverlap += 1

        i += 1
        try:
            # the last trace may not be the whole trace
            start_time = self.get_start(das_t[i])
            if start_time < latest:
                end_time = self.get_end(das_t[i], start_time, sample_rate)
                if latest < end_time:
                    end_time = latest
                sampleNo += sample_rate * (end_time - start_time)

        except IndexError:
            pass

        return expected_sampleNo, sampleNo, gapOverlap

    def get_availability_percentage(self, station,
                                    location, channel,
                                    starttime, endtime,
                                    include_sample_rate=False):
        """
        Get percentage of available data.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
        :type location: str
        :param location: Location code of requested data (e.g. "").
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: tuple(float, int)
        :returns: Tuple of percentage of available data (``0.0`` to ``1.0``)
            and number of gaps/overlaps.
        """

        allp = station + channel

        if '*' in allp or '?' in allp:
            raise PH5AvailabilityError(
                "get_availability_percentage requires providing exact "
                "station/channel.")

        sampleNo = 0
        expected_sampleNo = 0
        gapOverlap = 0
        array_names = sorted(self.ph5.Array_t_names)

        for array_name in array_names:
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
            ret = self.get_array_order_id(array_name)

            arrayorder, arraybyid = ret

            for ph5_station in arrayorder:
                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]

                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue

                        ph5_das = st['das/serial_number_s']
                        ph5_sample_rate = self.get_sample_rate(st)
                        ph5_channum = st['channel_number_i']

                        ret = self.get_time_das_t(
                            ph5_das, starttime, endtime,
                            ph5_channum, ph5_sample_rate)
                        if ret == -1:
                            continue
                        ph5_earliest, ph5_latest, das_t = ret

                        ret = self.get_sampleNos_gapOverlap(
                            das_t, ph5_earliest, ph5_latest,
                            starttime, endtime, ph5_sample_rate, st)

                        expected_sampleNo += ret[0]
                        sampleNo += ret[1]
                        gapOverlap += ret[2]
        if sampleNo == 0:
            sampleResult = 0.0
            if self.array is not None:
                LOGGER.warning(
                    "The availability percentage is 0.0. It may result from "
                    "the given array not match with the station and channel. "
                    "Array isn't needed to get the availability percentage.")
        else:
            sampleResult = sampleNo / expected_sampleNo

        return (sampleResult, gapOverlap)

    def has_data(self, station='*', location='*',
                 channel='*', starttime=None, endtime=None,
                 include_sample_rate=False):
        """
        Return whether there is data for a specified station,
        location, channel, starttime, and endtime combination.
        :type station: str
        :param station: Station code of requested data (e.g. "ANMO").
            Wildcards '*' and '?' are supported.
        :type location: str
        :param location: Location code of requested data (e.g. "").
            Wildcards '*' and '?' are supported.
        :type channel: str
        :param channel: Channel code of requested data (e.g. "HHZ").
            Wildcards '*' and '?' are supported.
        :type starttime: float
        :param starttime: Start of requested time window as epoch in seconds
        :type endtime: float
        :param endtime: End of requested time window as epoch in seconds
        :rtype: bool
        :returns: Returns ``True`` if there is data in Ph5 for a given
            station, location, channel, starttime, endtime.
        """
        array_names = sorted(self.ph5.Array_t_names)

        for array_name in array_names:
            if self.array is not None:
                a_n = int(array_name.split('_')[2])
                if self.array != a_n:
                    continue
            ret = self.get_array_order_id(array_name)

            arrayorder, arraybyid = ret

            for ph5_station in arrayorder:

                station_list = arraybyid.get(ph5_station)

                for deployment in station_list:
                    station_len = len(station_list[deployment])
                    for st_num in range(0, station_len):
                        st = station_list[deployment][st_num]
                        ret = self.get_slc_info(st, station, location, channel)
                        if ret == -1:
                            continue

                        ph5_das = st['das/serial_number_s']
                        ph5_channum = st['channel_number_i']

                        if channel == "*":
                            ret = self.get_time_das_t(
                                ph5_das, starttime, endtime)
                        else:
                            ph5_sample_rate = self.get_sample_rate(st)
                            ph5_sample_rate = self.get_sample_rate(st)
                            ret = self.get_time_das_t(
                                ph5_das, starttime, endtime,
                                component=ph5_channum,
                                sample_rate=ph5_sample_rate)
                        if ret == -1:
                            continue
                        ph5_earliest, ph5_latest, das_t = ret

                        for d in das_t:
                            if d['sample_count_i'] > 0:
                                return True
                            elif d['sample_rate_i'] == 0:
                                ref = self.ph5.ph5_g_receivers.\
                                    find_trace_ref(
                                        d['array_name_data_a'].strip())
                                if ref.nrows > 0:
                                    return True
                        self.ph5.forget_das_t(ph5_das)

        return False

    def print_report(self, text):
        if self.OFILE is None:
            print(text)
        else:
            self.OFILE.write(text + "\n")
            self.OFILE.close()

    def get_report(self, result, format):
        if format == 's':
            return self.get_sync_report(result)
        elif format == 'g':
            return self.get_geoCSV_report(result)
        elif format == 't':
            return self.get_text_report(result)
        elif format == 'j':
            return self.get_json_report(result)
        else:
            LOGGER.warning("The entered format %s is not supported." % format)
            return result

    def get_sync_report(self, result):
        """
        Link for Format:
        http://www.iris.washington.edu/bud_stuff/goat/syncformat.html
        """
        # header line
        today = dt.datetime.now()
        year = today.year
        day_of_year = (today - dt.datetime(today.year, 1, 1)).days + 1
        date = "%s,%s" % (year, day_of_year)
        s = "%s|%s" % ('PIC', date)

        # Time Span Lines
        template = [self.netcode] + [''] * 15
        for r in result:
            template[1] = r[f_id['sta']]
            template[2] = r[f_id['loc']]
            template[3] = r[f_id['chan']]
            t = timedoy.epoch2passcal(r[f_id['earliest']])
            template[4] = t[:-4].replace(":", ",", 2)
            t = timedoy.epoch2passcal(r[f_id['latest']])
            template[5] = t[:-4].replace(":", ",", 2)
            if self.SR_included:
                if r[f_id['sRate']] == 0:
                    template[7] = "000.0"
                else:
                    template[7] = str(r[f_id['sRate']])
            # template[13] = 'primary'

            s += "\n" + "|".join(template)
        return s

    def get_geoCSV_report(self, result):
        """
        Link for Format:
        http://geows.ds.iris.edu/documents/GeoCSV.pdf
        Example: Minimal IRIS Station Example
        """
        dataset = "#dataset: GeoCSV 2.0"
        delim = "#delimiter: |"
        field_unit = "#field_unit: unitless | unitless | unitless | "\
            "unitless | unitless"
        field_type = "#field_type: string | string | string | string | "\
            "string"
        header = "network|station|location|channel|quality"

        if self.SR_included:
            field_unit += " | hertz"
            field_type += " | float"
            header += "|sample_rate"

        field_unit += " | ISO_8601 | ISO_8601"
        field_type += " | datetime | datetime"
        header += "|earliest|latest"

        s = ""
        if result is None:
            return None
        for r in result:
            r = list(r)
            r = self.convert_time(r)

            try:
                # remove 0 prefix station name
                sta = str(int(str(r[f_id['sta']])))
            except Exception:
                # in case station name is not a number
                sta = f_id['sta']
            row = [self.netcode, sta, r[f_id['loc']],
                   r[f_id['chan']], '']
            if self.SR_included:
                row += [str(int(r[f_id['sRate']]))]
            row += [r[f_id['earliest']], r[f_id['latest']]]

            s += "\n" + "|".join(row)

        ret = dataset + "\n" + delim + "\n" + field_unit + "\n" \
            + field_type + "\n" + header + s

        return ret

    def get_text_report(self, result):
        s = ""
        for r in result:
            r = list(r)
            r = self.convert_time(r)

            s += "\n" + self.netcode + " "

            s += r[f_id['sta']].ljust(self.sta_len) + "  "

            loc = r[f_id['loc']] if r[f_id['loc']] != '' else '--'
            s += loc + " "

            s += r[f_id['chan']] + " "

            s += "  "
            if self.SR_included:
                if r[f_id['sRate']] == 0:
                    r[f_id['sRate']] = "000.0"
                s += str(r[f_id['sRate']]).rjust(len('sample-rate')) + " "

            s += r[f_id['earliest']] + " "
            s += r[f_id['latest']]

        header = "#n " + "s".ljust(self.sta_len) + "  l  c   q "
        if self.SR_included:
            header += "sample-rate "
        header += "earliest".rjust(self.tim_len) + " " + \
            "latest".rjust(self.tim_len)

        ret = header + s
        return ret

    def get_json_report(self, result):
        today = dt.datetime.now()
        now_tdoy = timedoy.TimeDOY(epoch=time.mktime(today.timetuple()))
        header = '"created":"%s","datasources":' \
            % now_tdoy.getFdsnTime()

        arow = '"net":"%(net)s","sta":"%(sta)s","loc":"%(loc)s",'\
            '"cha":"%(chan)s","quality":"",'
        if self.SR_included:
            arow += '"sample_rate":%(sRate)s,'
        arow += '"timespans":[%(tspan)s]'
        rows = []
        tspan = []
        try:
            for i in range(len(result)):
                if i != 0 and result[i-1][:3] != result[i][:3]:
                    # add row and reset tspan for previous stat, loc, chan
                    # when there is any changes
                    r = result[i-1]
                    v = {"net": self.netcode, "sta": r[f_id['sta']],
                         "loc": r[f_id['loc']], "chan": r[f_id['chan']],
                         "tspan": ','.join(tspan)}
                    if self.SR_included:
                        v['sRate'] = r[f_id['sRate']]

                    rows.append("{%s}" % (arow % v))

                    tspan = []
                # add timespan for current processed row
                r = list(result[i])
                r = self.convert_time(r)

                tspan.append('["%s","%s"]' %
                             (r[f_id['earliest']], r[f_id['latest']]))
        except Exception:
            raise PH5AvailabilityError(
                "Wrong format result sent to get_json_report.")

        if tspan != []:
            r = result[-1]
            v = {"net": self.netcode, "sta": r[f_id['sta']],
                 "loc": r[f_id['loc']], "chan": r[f_id['chan']],
                 "tspan": ','.join(tspan)}
            if self.SR_included:
                v['sRate'] = r[f_id['sRate']]

            rows.append("{%s}" % arow % v)

        ret = '{%s[\n%s\n]}' % (header, ',\n'.join(rows))

        return ret

    def convert_time(self, r):
        """
        given a row in the result,
         if have epoch times on 2,3: convert them to Fdsn
         if have Fdsn times on 2,3: return row as it is
         otherwise return -1
        """
        fmt = ("%Y-%m-%dT%H:%M:%S.%fZ")
        try:
            earliest = dt.datetime.strptime(r[f_id['earliest']], fmt)
            latest = dt.datetime.strptime(r[f_id['latest']], fmt)
            return r
        except TypeError:
            pass
        try:
            # availability/availability_extent
            earliest = timedoy.TimeDOY(epoch=r[f_id['earliest']])
            earliest = earliest.getFdsnTime() + "Z"
            latest = timedoy.TimeDOY(epoch=r[f_id['latest']])
            latest = latest.getFdsnTime() + "Z"
            r[f_id['earliest']] = earliest
            r[f_id['latest']] = latest
        except TypeError:
            raise PH5AvailabilityError(
                "convert_time receives list as parameter.")
        except Exception:
            errmsg = "The list sent to convert_time does not have epoch "\
                "times at %s and %s" % (f_id['earliest'], f_id['latest'])
            raise PH5AvailabilityError(errmsg)

        return r

    def process_all(self):
        AVAIL = {0: self.has_data, 1: self.get_slc,
                 2: self.get_availability, 3: self.get_availability_extent,
                 4: self.get_availability_percentage}
        result = []
        has_data = False
        for st in self.stations:
            for ch in self.channels:
                for loc in self.locations:
                    avail = AVAIL[self.avail](
                        st, loc, ch, self.starttime, self.endtime,
                        self.SR_included)
                    if isinstance(avail, bool):
                        if avail:
                            has_data = True
                    else:
                        result += avail
        if self.avail == 0:
            print(has_data)
            return
        elif self.avail not in [2, 3] or self.format is None:
            print(result)
            return

        report = self.get_report(result, format=self.format)

        if isinstance(report, str):
            self.print_report(report)
        else:
            print(result)


def get_args(args):
    """
    Parses command line arguments and returns arg_parse object
    :rtype: :class argparse
    :returns: Returns arge parse class object
    """

    sentinel_dict = {}

    def _preprocess_sysargv(argv):
        inputs = []
        for arg in argv:
            # handles case where values contain --, otherwise they will
            # be interpreted as arguments.
            if '--,' in arg or ',--' in arg or arg == '--':
                sentinel = uuid4().hex
                key = '%s' % sentinel
                sentinel_dict[key] = arg
                inputs.append(sentinel)
            else:
                inputs.append(arg)
        return inputs

    def _postprocess_sysargv(v):
        if v in sentinel_dict:
            return sentinel_dict.get(v)
        else:
            return v

    parser = argparse.ArgumentParser(
        description='Get data availability form PH5',
        formatter_class=RawTextHelpFormatter,
        usage='Version: {0} ph5availability '
              '--nickname="Master_PH5_file" [options]'.format(PROG_VERSION))
    parser.add_argument(
        "-n", "--nickname", action="store",
        type=str, metavar="nickname", default="master.ph5")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-s", "--start_time", action="store",
        type=str, dest="start_time", metavar="start_time", default=None,
        help=("Time formats are YYYY:DOY:HH:MM:SS.ss or "
              "YYYY-mm-ddTHH:MM:SS.ss (ISO-8601)"))

    parser.add_argument(
        "-e", "--endtime", action="store",
        type=str, dest="end_time", metavar="end_time", default=None,
        help=("Time formats are YYYY:DOY:HH:MM:SS.ss or "
              "YYYY-mm-ddTHH:MM:SS.ss (ISO-8601)"))

    parser.add_argument(
        "--station", action="store", dest="sta_list",
        help="Comma separated list of SEED station id's",
        metavar="sta_list", type=str, default=[])

    parser.add_argument(
        "--station_id", action="store", dest="sta_id_list",
        help="Comma separated list of PH5 station id's",
        metavar="sta_id_list", type=str, default=[])

    parser.add_argument(
        '-l', '--location', type=_postprocess_sysargv,
        help="Select one or more SEED location identifier. "
        "Use -- for 'Blank' location IDs (ID's containing 2 spaces). "
        "Accepts wildcards and lists.")

    parser.add_argument(
        '-c', "--channel", action="store",
        type=str, dest="channel",
        help="Comma separated list of SEED channels to extract",
        metavar="channel", default=[])

    parser.add_argument(
        "-S", "--srate", action="store_true",
        dest="samplerate",
        help="Sample Rate included",
        default=False)

    parser.add_argument(
        "-A", "--Array_t_", dest="array_t_", metavar="n", type=int,
        help=("Dump /Experiment_g/Sorts_g/Array_t_[n] to a kef file."),
        default=None)

    parser.add_argument(
        "-a", "--avail", action="store",
        type=int, dest="avail",
        help=("Availability of data: 0: has_data, 1: slc, 2: availability, "
              "3: availability_extent, 4: availability_percentage"),
        metavar="avail", default=0, required=True)

    parser.add_argument(
        "-F", "-f", "--format", action="store", dest="format",
        help=("Format for availability's report:\n  t: text, s: sync, "
              "g: geocsv, j: json"),
        metavar="format", type=str, default=None)

    parser.add_argument(
        "-o", "--outfile", dest="output_file", metavar="output_file",
        help=("The output file to be saved at. Only applies when avail is "
              "set to 2 or 3."), default=None)

    return parser.parse_args(_preprocess_sysargv(args))


def main():
    """
    Main method for use for command line program
    """
    args = get_args(sys.argv[1:])
    if args.nickname[-3:] == 'ph5':
        ph5file = os.path.join(args.ph5path, args.nickname)
    else:
        ph5file = os.path.join(args.ph5path, args.nickname + '.ph5')
        args.nickname += '.ph5'

    if not os.path.exists(ph5file):
        LOGGER.error("{0} not found.\n".format(ph5file))
        sys.exit(-1)
    try:
        ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)
        availability = PH5Availability(ph5API_object)
        availability.analyze_args(args)

        availability.process_all()

    except ph5api.APIError as err:
        LOGGER.error(err.msg)
    except experiment.HDF5InteractionError as err:
        LOGGER.error(err.msg)
    except PH5AvailabilityError as err:
        LOGGER.error(str(err))
    except Exception as err:
        LOGGER.error(str(err))

    ph5API_object.close()


if __name__ == '__main__':
    main()
