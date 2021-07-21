# Derick Hess, Oct 2017
#
"""
Runs a set of checks on PH5 archive to test for
errors and make sure it is ready for archival at IRIS DMC
"""
from __future__ import print_function

import argparse
import logging
import re
import subprocess
import os
import sys
import copy

from ph5.core import ph5api
from ph5.utilities import validation

PROG_VERSION = "2021.141"
LOGGER = logging.getLogger(__name__)


class ValidationBlock(object):

    def __init__(self, heading="", info=None, warning=None, error=None):
        if info is None:
            info = []
        if warning is None:
            warning = []
        if error is None:
            error = []
        self.heading = heading
        self.info = info
        self.warning = warning
        self.error = error

    def write_to_log(self, log_file, level):
        log_file.write(self.heading)
        if self.error and (level == "INFO" or level == "WARNING" or
                           level == "ERROR"):
            for e in self.error:
                log_file.write("ERROR: {}\n".format(e))
        if self.warning and (level == "INFO" or level == "WARNING"):
            for w in self.warning:
                log_file.write("WARNING: {}\n".format(w))
        if self.info and level == "INFO":
            for i in self.info:
                log_file.write("INFO: {}\n".format(i))


class PH5ValidateException(Exception):
    pass


class PH5Validate(object):
    def __init__(self, ph5API_object, ph5path):
        self.ph5 = ph5API_object
        self.path = ph5path
        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()
        if not self.ph5.Experiment_t:
            self.ph5.read_experiment_t()

    def read_arrays(self, name):
        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)

    def read_events(self, name):
        if name is None:
            for n in self.ph5.Event_t_names:
                self.ph5.read_event_t(n)
        else:
            self.ph5.read_event_t(name)

    def validate_ph5_reportnum(self, reportnum_code):
        """
        Method for validating report number argument.
        :param reportnum_code: report number to validate
        :type: str
        :returns: True if report number code is valid
        :type: boolean
        """
        regex = re.compile(r"(^[\d\?\*]+$)")
        if '-' in reportnum_code:
            c1, c2 = reportnum_code.split('-', 1)
            if (re.match(regex, c1) and len(c1) <= 2
                and (len(c1) == 2 or '*' in c1)) and \
               (re.match(regex, c2) and len(c2) <= 3
                    and (len(c2) == 3 or '*' in c2)):
                return True
            else:
                return False
        else:
            return False

    def check_experiment_t_completeness(self, experiment_t):
        """
        Checks that the following are present in Experiment_t:
          #### NETWORK LEVEL CHECKS CHECKS
          - experiment_id_s
          - nickname_s
          - longname_s
          - PIs_s
          - institutions_s
          - summary_paragraph_s
        """
        info = []
        warning = []
        error = []
        if not experiment_t:
            error.append("Experiment_t does not exist. "
                         "run experiment_t_gen to create table")
            return info, warning, error
        if len(experiment_t) > 1:
            error.append("More than one entry found in experiment_t.")

        if experiment_t[0]['net_code_s'] in [None, '']:
            error.append("Network code was not found: "
                         "A 2 character network code is required.")
        elif not (1 <= len(experiment_t[0]['net_code_s']) <= 2):
            error.append("SEED network code not "
                         "between 1 and 2 characters.")
        elif not experiment_t[0]['net_code_s'][0].isdigit() and \
                experiment_t[0]['net_code_s'][0].upper() != "X" and \
                experiment_t[0]['net_code_s'][0].upper() != "Y" and \
                experiment_t[0]['net_code_s'][0].upper() != "Z":
            error.append("Network code is a permanent FDSN: "
                         "Network code should be a temporary code.")

        reportnum_code = experiment_t[0]['experiment_id_s']
        if not reportnum_code:
            error.append("Experiment ID was not found: "
                         "An experiment id (YY-XXX) is required.")

        if not self.validate_ph5_reportnum(reportnum_code):
            error.append('Invalid report number code {0}. '
                         'Must match pattern [0-9][0-9]-[0-9][0-9][0-9].'
                         .format(reportnum_code))

        if not experiment_t[0]['nickname_s']:
            error.append("Nickname was not found: "
                         "It is suggested you include a nickname "
                         "for your experiment")

        if not experiment_t[0]['longname_s']:
            warning.append("Long name was not found: "
                           "It is suggested you include a long name "
                           "for your experiment")

        if not experiment_t[0]['PIs_s']:
            warning.append("PIs were not found: "
                           "It is suggested you include the PIs "
                           "for your experiment ")

        if not experiment_t[0]['institutions_s']:
            warning.append("Institutions were not found: "
                           "It is suggested you include the institutions "
                           "for your experiment")

        if not experiment_t[0]['summary_paragraph_s']:
            warning.append("Summary Paragraph was not found: "
                           "It is suggested you include a short summary "
                           "paragraph describing the experiment or data")
        return info, warning, error

    def check_experiment_t_bounding_box(self, experiment_t):
        """
        Checks for the existence of an Experiment_t bounding box. Creates a
        suggested bounding box if one does not exists.
        """
        info = []
        warning = []
        error = []

        if not experiment_t:
            return info, warning, error
        if (experiment_t[0]['north_west_corner/X/value_d'] == 0.0):
            error.append("A bounding box was not detected: "
                         "A suggested bounding box has been calculated "
                         "and saved in 'experiment_t_bounding_box.kef'")
            max_lat = None
            min_lat = None
            max_lon = None
            min_lon = None

            array_names = sorted(self.ph5.Array_t_names)

            for array_name in array_names:
                self.read_arrays(array_name)
                arraybyid = self.ph5.Array_t[array_name]['byid']
                arrayorder = self.ph5.Array_t[array_name]['order']
                for ph5_station in arrayorder:
                    station_list = arraybyid.get(ph5_station)
                    for deployment in station_list:
                        station_len = len(station_list[deployment])
                        for st_num in range(0, station_len):

                            latitude = station_list[deployment][
                                st_num]['location/Y/value_d']
                            longitude = station_list[deployment][
                                st_num]['location/X/value_d']

                            if max_lat is None:
                                max_lat = latitude
                            elif latitude > max_lat:
                                max_lat = latitude
                            if min_lat is None:
                                min_lat = latitude
                            elif latitude < min_lat:
                                min_lat = latitude
                            if max_lon is None:
                                max_lon = longitude
                            elif longitude > max_lon:
                                max_lon = longitude
                            if min_lon is None:
                                min_lon = longitude
                            elif longitude < min_lon:
                                min_lon = longitude

            shot_lines = sorted(self.ph5.Event_t_names)

            for line in shot_lines:
                event_t = self.ph5.Event_t[line]['byid']
                for shot_id, _ in event_t.iteritems():
                    event_t = self.ph5.Event_t[
                        line]['byid'][shot_id]
                    latitude = event_t[
                        'location/Y/value_d']
                    longitude = event_t[
                        'location/X/value_d']
                    if max_lat is None:
                        max_lat = latitude
                    elif latitude > max_lat:
                        max_lat = latitude
                    if min_lat is None:
                        min_lat = latitude
                    elif latitude < min_lat:
                        min_lat = latitude
                    if max_lon is None:
                        max_lon = longitude
                    elif longitude > max_lon:
                        max_lon = longitude
                    if min_lon is None:
                        min_lon = longitude
                    elif longitude < min_lon:
                        min_lon = longitude

            process = subprocess.Popen(
                ("ph5tokef -n master.ph5 -p {0} -E >"
                 "experiment_t_bounding_box.kef"
                 .format(self.path)),
                shell=True,
                stdout=subprocess.PIPE)
            process.wait()
            new_kef = []
            with open("experiment_t_bounding_box.kef") as f:
                kef = f.readlines()
            for line in kef:
                if line.startswith("    north_west_corner/X/value_d="):
                    new_kef.append("    north_west_corner/X/value_d=" +
                                   str(min_lon) + "\n")
                elif line.startswith("    north_west_corner/Y/value_d="):
                    new_kef.append("    north_west_corner/Y/value_d=" +
                                   str(max_lat) + "\n")
                elif line.startswith("    south_east_corner/X/value_d="):
                    new_kef.append("    south_east_corner/X/value_d=" +
                                   str(max_lon) + "\n")
                elif line.startswith("    south_east_corner/Y/value_d"):
                    new_kef.append("    south_east_corner/Y/value_d=" +
                                   str(min_lat) + "\n")
                else:
                    new_kef.append(line)
            info.append("Created a suggested bounding box in file "
                        "'experiment_t_bounding_box.kef'")
            outfile = open("experiment_t_bounding_box.kef", 'w')
            for line in new_kef:
                outfile.write("%s" % line)

        return info, warning, error

    def check_experiment_t(self):
        """
        Checks Experiment_t table
        """
        LOGGER.info("Validating Experiment_t")
        experiment_t = self.ph5.Experiment_t['rows']

        validation_blocks = []
        info1, warning1, error1 = \
            self.check_experiment_t_completeness(experiment_t)
        info2, warning2, error2 = \
            self.check_experiment_t_bounding_box(experiment_t)
        if info1 or warning1 or error1 or \
           info2 or warning2 or error2:
            header = ("-=-=-=-=-=-=-=-=-\n"
                      "Experiment_t\n"
                      "{0} error, {1} warning, {2} info\n"
                      "-=-=-=-=-=-=-=-=-\n"
                      .format(len(error1) + len(error2),
                              len(warning1) + len(warning2),
                              len(info1) + len(info2)))
            info = info1 + info2
            warning = warning1 + warning2
            error = error1 + error2
            vb = ValidationBlock(heading=header, info=info, warning=warning,
                                 error=error)
            validation_blocks.append(vb)
        return validation_blocks

    def check_response_t(self):
        """
        This function only checks for general response errors.
        Response's errors for each station are checked in check_array_t()
        """
        LOGGER.info("Validating Response_t")
        header = ("-=-=-=-=-=-=-=-=-\n"
                  "Response_t\n"
                  "%s error, 0 warning, 0 info\n"
                  "-=-=-=-=-=-=-=-=-\n")
        self.ph5.read_response_t()
        errors = set()
        validation.check_has_response_filename(
            self.ph5.Response_t, errors, LOGGER)
        validation.check_resp_unique_n_i(self.ph5, errors, LOGGER)
        err = [e[0] for e in errors if e[1] == 'error']
        header = header % len(err)
        return [ValidationBlock(heading=header, error=err)]

    def check_station_completeness(self, station):
        """
        Checks that the following are present in Experiment_t:
          #### STATION LEVEL CHECKS
          - id_s
          - description_s
          - seed_station_name_s
            - check that 1 <= len(seed_station_name_s) <= 5
          #### CHANNEL LEVEL CHECKS CHECKS
          - seed_location_code_s
            - check that 0 <= len(seed_location_code_s) <= 2
          - seed_channel_code_s
            - check that 1 <= len(seed_channel_code_s) <= 3
          - seed_band_code_s
          - seed_instrument_code_s
          - seed_orientation_code_s
          - sample_rate_i
            - check that sample_rate_i > 0
          - sample_rate_multiplier
            - check that sample_rate_multiplier > 0
          - response_table_n_i
          #### CHANNEL LOCATION
          - location/X/value_d
          - location/Y/value_d
          - location/Z/value_d
          - location/Z/unit_i
          #### CHANNEL DEPLOY/PICKUP
          - deploy_time/epoch_l
          - pickup_time/epoch_l
            - check if deploy time is after pickup time
          #### CHANNEL SENSOR/DAS
          - das/serial_number_s
          - das/manufacturer_s
          - das/model_s
          - sensor/serial_number_s
          - sensor/manufacturer_s
          - sensor/model_s
        """
        info = []
        warning = []
        error = []
        # STATION LEVEL CHECKS CHECKS
        station_id = station['id_s']
        try:
            if not (0 <= int(station_id) <= 65535):
                error.append("Station ID '%s' not between 0 and 65535."
                             % station_id)
            elif int(station_id) > 32767:
                warning.append("Station ID '%s' is more than 32767. "
                               "Not compatible with SEGY revision 1."
                               % station_id)
        except ValueError:
            error.append("Station ID '%s' not a whole "
                         "number between 0 and 65535." % station_id)

        if not station['description_s']:
            warning.append("No station description found.")

        if not station['seed_station_name_s']:
            error.append("SEED station code required.")

        if not (1 <= len(station['seed_station_name_s']) <= 5):
            error.append("SEED station code not "
                         "between 1 and 5 characters.")

        # CHANNEL LEVEL CHECKS CHECKS
        if station['seed_location_code_s'] is None:
            error.append("SEED location code "
                         "required.")

        if not (0 <= len(station['seed_location_code_s']) <= 2):
            error.append("SEED location code not "
                         "between 0 and 2 characters.")

        if not station['seed_band_code_s']:
            error.append("SEED band code required.")

        if not station['seed_instrument_code_s']:
            error.append("SEED instrument code required.")

        if not station['seed_orientation_code_s']:
            error.append("SEED orientation code "
                         "required.")

        if station['sample_rate_i'] < 0:
            error.append("Sample rate = %s not positive." %
                         station['sample_rate_i'])
        elif station['sample_rate_i'] == 0:
            warning.append("Sample rate seems to be 0. Is this correct???")

        if ((int(station['sample_rate_multiplier_i']) !=
                station['sample_rate_multiplier_i'])
                or station['sample_rate_multiplier_i'] < 1):
            error.append("Sample rate multiplier = %s "
                         "is not an integer greater than 1."
                         % station['sample_rate_multiplier_i'])

        response_t = self.ph5.get_response_t_by_n_i(
            station['response_table_n_i'])
        if response_t is None:
            error.append("No Response table found. "
                         "Have you run resp_load yet?")

        # CHANNEL LOCATION
        e, w = validation.check_lat_lon_elev(station)
        error = error + e
        warning = warning + w
        # CHANNEL DEPLOY/PICKUP
        deploy_time = station['deploy_time/epoch_l']

        if deploy_time is None:
            error.append("No deploy_time value "
                         "found for channel.")

        pickup_time = station['pickup_time/epoch_l']

        if pickup_time is None:
            error.append("No pickup_time value "
                         "found for channel.")

        das_serial = station['das/serial_number_s']
        sensor_serial = station['sensor/serial_number_s']
        if deploy_time > pickup_time:
            error.append("Deploy time is after pickup time")

        # CHANNEL SENSOR/DAS
        channel_id = station['channel_number_i']
        if das_serial is None:
            error.append("Das serial number is missing.")

        if sensor_serial is None:
            warning.append("Sensor serial number is missing.")

        self.ph5.read_das_t(das_serial, reread=False)
        sample_rate = station['sample_rate_i']
        nodata_err = None
        if das_serial not in self.ph5.Das_t:
            error.append("No data found for das serial number {0}. "
                         "You may need to reload the raw "
                         "data for this station."
                         .format(str(das_serial)))
        dt = self.das_time[(das_serial, channel_id, sample_rate)]
        # add bound_errors if applicable
        if deploy_time == dt['min_deploy_time'][0]:
            try:
                warning.append(dt['min_deploy_time'][1])
            except IndexError:
                pass

        das_time_list = copy.copy(dt['time_windows'])

        # check for duplicates:
        item = (deploy_time, pickup_time, station_id)
        dups = [i for i, x in enumerate(das_time_list) if x == item]
        if len(dups) > 1:
            warning.append("Station %s [%s, %s] is repeated %s time(s)" %
                           (station_id, deploy_time, pickup_time, len(dups)-1))
            # delete all duplicates except for the last one
            del das_time_list[dups[0]:dups[-1]]

        index = das_time_list.index((deploy_time, pickup_time, station_id))

        overlaps = []
        # check if there is any overlap time for this das
        for t in das_time_list:
            if ((t[0] <= deploy_time < t[1]) or (t[0] < pickup_time <= t[1])):
                overlaps.append(t[2])

        if len(overlaps) > 1:
            error.append("Overlap time on station(s): %s" %
                         ", ".join(overlaps))

        try:
            # don't need to read das_t because it will be read in get_extent
            if (index <= (len(das_time_list) - 1)):
                # current deploy time
                check_start = das_time_list[index][0]
                if index == len(das_time_list) - 1:
                    # for last index, need to check if no data exist
                    # so check from curr deploy time to current pickup time
                    check_end = das_time_list[index][1]
                else:
                    # -- check data from current deploy time to
                    # next deploy time -1 (-1 to avoid include next deploy time
                    check_end = das_time_list[index+1][0] - 1
                i = 1
                # while loop to avoid using overlaping row
                while check_end < check_start:
                    i += 1
                    check_end = das_time_list[index+i][0] - 1
                try:
                    # clear das to make sure get_extent consider channel & sr
                    self.ph5.forget_das_t(das_serial)
                except AttributeError:
                    pass
                true_start, true_end =\
                    self.ph5.get_extent(das=das_serial,
                                        component=channel_id,
                                        start=check_start,
                                        end=check_end,
                                        sample_rate=sample_rate)

                if true_start is None and nodata_err is None:
                    # check nodata_err to avoid duplicate error
                    error.append(
                        "No data found for das serial number {0} during this "
                        "station's time. You may need to reload the raw "
                        "data for this station.".format(str(das_serial)))
                else:
                    # don't check deploy time because the time sent to
                    # get_extent() is limited from deploy time
                    if pickup_time < true_end:
                        time = int(true_end - pickup_time)
                        warning.append(
                            "Data exists after pickup time: %s seconds."
                            % time)
        except KeyError:
            try:  # avoid opening too many files
                self.ph5.forget_das_t(das_serial)
            except Exception:
                pass
            error.append("No data found for channel {0}. "
                         "Other channels seem to exist"
                         .format(str(channel_id)))

        if not station['sensor/manufacturer_s']:
            warning.append("Sensor manufacturer is "
                           "missing. Is this correct???")

        if not station['sensor/model_s']:
            warning.append("Sensor model is missing. "
                           "Is this correct???")

        if not station['das/manufacturer_s']:
            warning.append("DAS manufacturer is missing. "
                           "Is this correct???")

        if not station['das/model_s']:
            warning.append("DAS model is missing. "
                           "Is this correct???")

        return info, warning, error

    def analyze_time(self):
        """
        Analyze the array table to create dictionary self.das_time with key
        is a set of (das, channel, sample_rate)
        Each item's value includes
        * time_windows: a deploy-time-sorted list of all time windows
        of stations that match its key
        * min_deploy_time: [item1, item2]:
          item1: min_deploy_time value
          item2: error message if there is any data before the min deploy

        self.das_time will help check_station_completness with:
        * reporting error about data exits before the first deploy time
        * check overlaping time
        * correctly check data exist from a station pickup time to the
        next deploy time available
        """
        self.read_arrays(None)
        self.das_time = {}
        for array_name in self.ph5.Array_t_names:
            arraybyid = self.ph5.Array_t[array_name]['byid']
            for stations in arraybyid.values():
                for deployment in stations.values():
                    for stat in deployment:
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

        for key in self.das_time.keys():
            dt = self.das_time[key]
            dt['time_windows'].sort()
            d, c, spr = key
            dt['min_deploy_time'] = [dt['time_windows'][0][0]]
            dt['max_pickup_time'] = [max([t[1] for t in dt['time_windows']])]
            # look for data outside time border of each set
            true_deploy, true_pickup = self.ph5.get_extent(das=d,
                                                           component=c,
                                                           sample_rate=spr)
            if true_deploy is None:
                # No data found. But don't give warning here because it
                #  will be given in check_station_completness
                continue
            if true_deploy < dt['min_deploy_time'][0]:
                time = int(dt['min_deploy_time'][0] - true_deploy)
                warningmsg = "Data exists before deploy time: %s seconds." \
                    % time
                dt['min_deploy_time'].append(warningmsg)
            # Don't check Data exitsts after pickup time here
            # it will be check in check_station_completeness

    def check_array_t(self):
        LOGGER.info("Validating Array_t")
        validation_blocks = []
        checked_data_files = {}
        track_repeated = []
        if not self.ph5.Array_t_names:
            header = ("-=-=-=-=-=-=-=-=-\n"
                      "Array_t\n"
                      "-=-=-=-=-=-=-=-=-\n")
            msg = "Array_t table not found."
            vb = ValidationBlock(heading=header, error=[msg])
            validation_blocks.append(vb)
            LOGGER.error(msg)
        else:
            self.analyze_time()
            array_names = sorted(self.ph5.Array_t_names)
            for array_name in array_names:
                arraybyid = self.ph5.Array_t[array_name]['byid']
                arrayorder = self.ph5.Array_t[array_name]['order']
                for ph5_station in arrayorder:
                    station_list = arraybyid.get(ph5_station)
                    for deployment in station_list:
                        station_len = len(station_list[deployment])
                        for st_num in range(0, station_len):
                            station = station_list[deployment][st_num]
                            station_id = station['id_s']
                            channel_id = station['channel_number_i']
                            cha_code = (station['seed_band_code_s'] +
                                        station['seed_instrument_code_s'] +
                                        station['seed_orientation_code_s'])
                            resp_n_i = station['response_table_n_i']
                            das_model = station['das/model_s']
                            if das_model.startswith("ZLAND"):
                                sensor_model = ''
                            else:
                                sensor_model = station['sensor/model_s']
                            errors = set()
                            resp_info = {
                                'n_i': resp_n_i,
                                'array': array_name[8:],
                                'sta': station_id,
                                'cha_id': channel_id,
                                'cha_code': cha_code,
                                'dmodel': das_model,
                                'smodel': sensor_model,
                                'spr': station['sample_rate_i'],
                                'sprm': station['sample_rate_multiplier_i']
                            }

                            LOGGER.debug("Validating Station {0} Channel {1}"
                                         .format(str(station_id),
                                                 str(channel_id)))
                            info, warning, error = \
                                self.check_station_completeness(station)

                            check_info = validation.check_response_info(
                                resp_info,
                                self.ph5,
                                checked_data_files,
                                errors,
                                None)
                            if check_info[0] is False:
                                for errmsg in check_info[1]:
                                    errors.add((errmsg, 'error'))
                            error += [': '.join(e[0].split(': ')[1:])
                                      for e in errors if e[1] == 'error']
                            warning += [': '.join(w[0].split(': ')[1:])
                                        for w in errors if w[1] == 'warning']
                            if any("repeated" in w for w in warning):
                                item = (station_id, channel_id,
                                        station['deploy_time/epoch_l'],
                                        station['pickup_time/epoch_l'])
                                if item in track_repeated:
                                    # skip creating vb for repeated station
                                    continue
                                else:
                                    track_repeated.append(item)

                            if info or warning or error:
                                header = ("-=-=-=-=-=-=-=-=-\n"
                                          "Station {0} Channel {1}\n"
                                          "{2} error, {3} warning, "
                                          "{4} info\n"
                                          "-=-=-=-=-=-=-=-=-\n"
                                          .format(str(station_id),
                                                  str(channel_id),
                                                  len(error),
                                                  len(warning),
                                                  len(info)))
                                vb = ValidationBlock(heading=header,
                                                     info=info,
                                                     warning=warning,
                                                     error=error)
                                validation_blocks.append(vb)
        return validation_blocks

    def check_event_t_completeness(self, event):
        """
        Checks that the following are present in Event_t:
          #### EVENT CHECKS
          - id_s
          - description_s
          #### EVENT LOCATION
          - location/coordinate_system_s
          - location/projection_s
          - location/ellipsoid_s
          - location/description_s
          - location/X/value_d
          - location/Y/value_d
          - location/Z/value_d
          #### EVENT TIME
          - time/epoch_l
          - time/micro_seconds_i
          #### EVENT SIZE
          - size/value_d
          - size/units_s
          #### EVENT DEPTH
          - depth/value_d
          - depth/units_s
        """
        info = []
        warning = []
        error = []
        # EVENT CHECKS
        if not event['id_s']:
            error.append("Event id is missing.")
        else:
            try:
                if not (0 <= int(event['id_s']) <= 65535):
                    error.append("Event ID '%s' not between 0 and 65535."
                                 % event['id_s'])
                elif int(event['id_s']) > 32767:
                    warning.append("Event ID '%s' is more than 32767. "
                                   "Not compatible with SEGY revision 1."
                                   % event['id_s'])
            except ValueError:
                error.append("Event ID '%s' not a whole "
                             "number between 0 and 65535." % event['id_s'])

        if not event['description_s']:
            warning.append("Event description is missing.")
        # EVENT LOCATION
        # removed check for coordinate_system_s, projection_s,
        # projection_s , ellipsoid_s , description_s
        # because they are not required and most of PIs do not fill them out
        if event['location/X/value_d'] == 0:
            error.append("Event location/X/value_d "
                         "'longitude' seems to be 0. "
                         "Is this correct???")
        if event['location/X/units_s'] in [None, '']:
            warning.append("No Event location/X/units_s value "
                           "found.")

        if event['location/Y/value_d'] == 0:
            error.append("Event location/Y/value_d "
                         "'latitude' seems to be 0. "
                         "Is this correct???")
        if event['location/Y/units_s'] in [None, '']:
            warning.append("No Event location/Y/units_s value "
                           "found.")

        if not event['location/Z/value_d']:
            error.append("No Event location/Z/value_d value "
                         "found.")
        if event['location/Z/units_s'] in [None, '']:
            warning.append("No Event location/Z/units_s value "
                           "found.")
        if event['location/Z/units_s'] in ['unknown', 'UNKNOWN']:
            warning.append("Event location/Z/units_s has a value of UNKNOWN. "
                           "Please update this value.")
        # EVENT TIME
        if event['time/epoch_l'] is None:
            error.append("No Event time/epoch_l value found.")
        if event['time/micro_seconds_i'] is None:
            error.append("No Event time/micro_seconds_i value "
                         "found.")
        # EVENT SIZE
        if event['size/value_d'] is None:
            warning.append("No Event size/value_d value found.")
        if event['size/units_s'] is None:
            warning.append("No Event size/units_s value found.")
        # EVENT DEPTH
        if event['depth/value_d'] is None:
            warning.append("No Event depth/value_d value found.")
        if event['depth/units_s'] is None:
            warning.append("No Event depth/units_s value found.")

        return info, warning, error

    def check_event_t(self):
        LOGGER.info("Validating Event_t")
        validation_blocks = []
        info = []
        warning = []
        error = []
        self.ph5.read_event_t_names()
        if not self.ph5.Event_t_names:
            header = ("-=-=-=-=-=-=-=-=-\n"
                      "Event_t\n"
                      "-=-=-=-=-=-=-=-=-\n"
                      .format())
            msg = ("Event_t table not found. "
                   "Did this experiment have shots???")
            LOGGER.warning(msg)
            vb = ValidationBlock(heading=header, warning=[msg])
            validation_blocks.append(vb)
        else:
            shot_lines = sorted(self.ph5.Event_t_names)
            for shot_line in shot_lines:
                self.ph5.read_event_t(shot_line)
                event_t = self.ph5.Event_t[shot_line]['byid']
                for _, event in event_t.items():
                    LOGGER.debug("Validating Event {0}"
                                 .format(str(event['id_s'])))
                    info, warning, error = \
                        self.check_event_t_completeness(event)
                    if info or warning or error:
                        header = ("-=-=-=-=-=-=-=-=-\n"
                                  "Event_t {0}\n"
                                  "{1} error, {2} warning, {3} info\n"
                                  "-=-=-=-=-=-=-=-=-\n"
                                  .format(event['id_s'],
                                          len(error),
                                          len(warning),
                                          len(info)))
                        vb = ValidationBlock(heading=header,
                                             info=info,
                                             warning=warning,
                                             error=error)
                        validation_blocks.append(vb)
        return validation_blocks


def get_args():
    parser = argparse.ArgumentParser(
        description='Runs set of checks on PH5 archvive',
        usage=('Version: %s ph5_validate '
               '--nickname="Master_PH5_file" [options]'
               % (PROG_VERSION)))

    parser.add_argument(
        "-n", "--nickname", action="store", default="master.ph5",
        type=str, metavar="nickname")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-l", "--level", action="store", default="WARNING",
        type=str, choices=('ERROR', 'WARNING', 'INFO'),
        help=("Level of logging detail. Choose from ERROR, WARNING, or INFO"))

    parser.add_argument("-o", "--outfile", action="store",
                        default="ph5_validate.log", type=str,
                        help=("Path to outfile where logging details are. "
                              "Default is ph5_validate.log.")
                        )

    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose logging.")

    args = parser.parse_args()
    PH5 = args.nickname
    if not os.path.exists(PH5) and not os.path.exists(PH5 + '.ph5'):
        LOGGER.error("{0} not found.".format(PH5))
        sys.exit()
    if args.verbose is True:
        LOGGER.parent.handlers[0].setLevel(logging.DEBUG)
    # Set up logging
    # Write log to file
    ch = logging.FileHandler(args.outfile)
    level = args.level
    if level == "ERROR":
        ch.setLevel(logging.ERROR)
    elif level == "WARNING":
        ch.setLevel(logging.WARNING)
    elif level == "INFO":
        ch.setLevel(logging.INFO)
    LOGGER.addHandler(ch)

    return args


def main():
    try:
        args = get_args()
        ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname)
        ph5validate = PH5Validate(ph5API_object,
                                  args.ph5path)
        validation_blocks = []
        validation_blocks.extend(ph5validate.check_experiment_t())
        validation_blocks.extend(ph5validate.check_array_t())
        validation_blocks.extend(ph5validate.check_response_t())
        validation_blocks.extend(ph5validate.check_event_t())
        with open(args.outfile, "w") as log_file:
            for vb in validation_blocks:
                vb.write_to_log(log_file,
                                args.level)
        ph5API_object.close()
        sys.stdout.write("\nWarnings, Errors and suggestions "
                         "written to logfile: %s\n" % args.outfile)
    except ph5api.APIError as err:
        LOGGER.error(err)
    except PH5ValidateException as err:
        LOGGER.error(err)
    except Exception as e:
        LOGGER.error(e)


if __name__ == '__main__':
    main()
