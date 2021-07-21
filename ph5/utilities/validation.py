"""
common functions for validation
"""
import tables
import re


ERRORS = {'smodel': "Array_t_%(array)s:sensor_model=%(smodel)s",
          'dmodel': "Array_t_%(array)s:das_model=%(dmodel)s",
          'spr': "Array_t_%(array)s:sr=%(spr)s",
          'sprm': "Array_t_%(array)s:srm=%(sprm)s",
          'gain': "Array_t_%(array)s:gain=%(gain)s"}


def combine_errors(check_fail, incomplete_errmsg, info):
    parts_errmsg = ''
    if check_fail != set():
        parts_errmsg = "inconsistent with " + ' '.join(
            [ERRORS[k] for k in check_fail])
    errmsg = ' or '.join([incomplete_errmsg, parts_errmsg % info])
    return errmsg.strip(" or ")


def addLog(errmsg, unique_errors, logger=None, logType='error'):
    unique_errors.add((errmsg, logType))
    if logger is not None:
        if logType == 'error':
            logger.error(errmsg)
        if logType == 'warning':
            logger.warning(errmsg)


def check_resp_data(ph5table, path, header, checked_data_files, n_i):
    """
    Check if response data is loaded for the response filename
    :param ph5table: table ph5
    :param path: path filled in the response file name of response_t (str)
    :param header: string of array-station-channel to help users identify
            where the problem belong to (str)
    :param checked_data_files: set of resp filenames that check_response_info()
        has run for it
    :param n_i: response index
    :return: raise Exception if there is no response data
    """
    name = path.split('/')[-1]
    if name in checked_data_files.keys():
        if checked_data_files[name] != '':
            raise Exception(checked_data_files[name])
        else:
            return

    checked_data_files[name] = ''
    try:
        ph5table.get_node(ph5table.root.Experiment_g.Responses_g, name)
    except tables.NoSuchNodeError:
        errmsg = "%sResponse_t[%s]:No response data loaded for %s." % \
                 (header, n_i, name)
        checked_data_files[name] = errmsg
        raise Exception(errmsg)
    return


def check_metadatatoph5_format(Response_t, info, header, errors, logger):
    """
    Check response_file_das_a in response_t matches with info from
     station entry
    :param Response_t: response entry according to info[n_i]
    :param info: info needed from each station:
            dict {n_i, array, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
    :para header: string of array-station-channel to help user identify where
            the problem belong to (str)
    :para errors: list of errors
    :param logger: logger of the caller
    :return:
        if there are more than 3 parts return False
        if all (3) parts pass checks return True
        if 2 parts pass checks, decide that this is created from metadatatoph5
            return True and log as error
        if less than 2 parts pass checks return incomplete_errmsg, m_check_fail
            to be included if check for resp_load format also failed.
    """
    if Response_t['response_file_das_a'] == '':
        # blank response_file_das_a return False in check_response_info
        # to throw error
        return True
    response_fname = Response_t['response_file_das_a'].split('/')[-1]
    parts = response_fname.split('_')
    if len(parts) > 3:
        return False
    incomplete_errmsg = ''
    if len(parts) < 3:
        incomplete_errmsg = "incomplete"
    count_corr_parts = 0
    m_check_fail = set()
    try:
        if parts[0] == info['dmodel_no_special_char']:
            count_corr_parts += 1
        else:
            m_check_fail.add('dmodel')
        if parts[1] == info['smodel_no_special_char']:
            count_corr_parts += 1
        else:
            m_check_fail.add('smodel')
        sr = re.split(r'(\d+)', parts[2])[1]
        if sr == str(int(info['spr'])):
            count_corr_parts += 1
        else:
            m_check_fail.add('spr')
    except IndexError:
        pass
    if count_corr_parts >= 2:
        # at least 2 parts correct, decide this is created from resp_load
        if m_check_fail != set([]) or incomplete_errmsg != '':
            errmsg = combine_errors(m_check_fail, incomplete_errmsg, info)
            errmsg = ("{0}Response_t[{1}]:response_file_das_a '{2}' is {3}. "
                      "Please check with metadatatoph5 format "
                      "[das_model]_[sensor_model]_[sr][cha] "
                      "(check doesn't include [cha])."
                      ).format(header,
                               info['n_i'],
                               response_fname,
                               errmsg)
            addLog(errmsg, errors, logger, logType='error')
        return True
    else:
        # if less than 2 parts correct, return checks to be included if check
        # for resp_load format also failed.
        return incomplete_errmsg, m_check_fail


def check_das_resp_load_format(Response_t, info, header, errors, logger,
                               m_check_ret):
    """
     Check response_file_das_a in response_t matches with info from
      station entry
     :param Response_t: response entry according to info[n_i]
     :param info: info needed from each station:
            dict {n_i, array, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
     :param header: string of array-station-channel to help user identify where
             the problem belong to (str)
     :param errors: list of errors
     :param logger: logger of the caller
     :param m_check_ret: if incomplete_errmsg, parts_errmsg are return
        from check_metadatatoph5_format, they will be included if this check
        is also failed
     :log as error  and return for the following cases:
        + more than 4 parts
        + if 3 parts corrects, decide this is created from resp_load so
            errmsg only includes resp_load's checks and format
        + if less than 3 parts corrects, cannot decide this is created from
            resp_load or metadatatoph5, so errmsg includes resp_load's
            checks and formats and metadatatoph5's if m_check_ret!=True
     """
    if Response_t['response_file_das_a'] == '':
        # blank response_file_das_a return False in check_response_info
        # to throw error
        return True
    info['gain'] = Response_t['gain/value_i']
    response_fname = Response_t['response_file_das_a'].split('/')[-1]
    r_format = "resp_load format [das_model]_[sr]_[srm]_[gain]"
    m_format = ("metadatatoph5 format [das_model]_[sensor_model]_[sr][cha] "
                "(check doesn't include [cha])")
    parts = response_fname.split('_')
    if len(parts) > 4:
        errmsg = ("%sResponse_t[%s]:response_file_das_a '%s' has too many "
                  "parts. Please check with format %s or %s"
                  % (header, info['n_i'], response_fname, m_format, r_format))
        addLog(errmsg, errors, logger, logType='error')
        return
    incomplete_errmsg = ''
    if len(parts) < 4:
        incomplete_errmsg = "incomplete"
    count_corr_parts = 0
    r_check_fail = set()
    try:
        if parts[0] == info['dmodel_no_special_char']:
            count_corr_parts += 1
        else:
            r_check_fail.add('dmodel')
        if parts[1] == str(int(info['spr'])):
            count_corr_parts += 1
        else:
            r_check_fail.add('spr')
        if parts[2] == str(int(info['sprm'])):
            count_corr_parts += 1
        else:
            r_check_fail.add('sprm')
        if parts[3] == str(int(info['gain'])):
            count_corr_parts += 1
        else:
            r_check_fail.add('gain')
    except IndexError:
        pass

    if r_check_fail != set([]) or incomplete_errmsg != '':
        errmsg = combine_errors(r_check_fail, incomplete_errmsg, info)
        if count_corr_parts >= 3 or m_check_ret is False:
            # at least 3 parts correct, decide this is created from resp_load
            errmsg = ("{0}Response_t[{1}]:response_file_das_a '{2}' is {3}. "
                      "Please check with {4}."
                      ).format(header,
                               info['n_i'],
                               response_fname,
                               errmsg.strip(),
                               r_format)
        else:
            # if less than 3 parts correct, include the check and format
            # of checking metadatatoph5 format to error message
            if incomplete_errmsg != 'incomplete':
                incomplete_errmsg = m_check_ret[0]
            for c in m_check_ret[1]:
                r_check_fail.add(c)
            errmsg = combine_errors(r_check_fail, incomplete_errmsg, info)
            errmsg = ("{0}Response_t[{1}]:response_file_das_a {2} is {3}. "
                      "Please check with {4} or {5}."
                      ).format(header,
                               info['n_i'],
                               response_fname,
                               errmsg.strip(),
                               r_format,
                               m_format)
        addLog(errmsg, errors, logger, logType='error')


def check_sensor(Response_t, info, header, errors, logger):
    """
     Check response_file_sensor_a in response_t matches with info from
      station entry
     :param Response_t: response entry according to info[n_i]
     :param info: info needed from each station:
            dict {n_i, array, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
     :para header: string of array-station-channel to help user identify where
             the problem belong to (str)
     :para errors: list of errors
     :param logger: logger of the caller
     :Log as error for 2 cases:
        response_file_sensor_a is blank while sensor model exists.
        response_file_sensor_a not match with sensor model
     """
    response_fname = Response_t['response_file_sensor_a'].split('/')[-1]
    if info['smodel'] != '' and response_fname == '':
        errmsg = ("%sResponse_t[%s]:response_file_sensor_a is blank while "
                  "sensor model exists." % (header, info['n_i']))
        addLog(errmsg, errors, logger, logType='error')
        return
    if info['smodel_no_special_char'] != response_fname:
        errmsg = ("{0}Response_t[{1}]:response_file_sensor_a '{2}' is "
                  "inconsistent with {3}."
                  ).format(header,
                           info['n_i'],
                           response_fname,
                           ERRORS['smodel'] % info)
        addLog(errmsg, errors, logger, logType='error')
        return


def check_response_info(info, ph5, checked_data_files, errors, logger):
    """
    Check in response info for each station entry if the response filenames are
    correct (das filename created by metadata or das/sensor filename
    created by resp_load) and the response data are loaded.
    :param info: info needed from each station:
            dict {n_i, sta, cha_id, cha_code, dmodel, smodel, spr, sprm}
    :param ph5: ph5 object
    :param checked_data_files: set of resp filenames that check_response_info()
        has run for it
    :param errors: list of errors from caller
    :param logger: logger of the caller
    :return:
        False, list of error messages if no response data loaded
        (d_path, s_path) in which d_path and s_path are response paths for
            das or sensor if response data are loaded for the file name stated
            in response table
    """
    Response_t = ph5.get_response_t_by_n_i(info['n_i'])
    header = ("array {0} station {1}, channel {2}: ").format(info['array'],
                                                             info['sta'],
                                                             info['cha_id'])
    if Response_t is None:
        errmsg = ("%sResponse_t has no entry for n_i=%s"
                  % (header, info['n_i']))
        return False, [errmsg]
    if info['n_i'] == -1:
        # metadata no response signal
        errmsg = ("%sResponse_t[-1]:Metadata response with n_i=-1 has no "
                  "response data." % header)
        return False, [errmsg]

    info['dmodel_no_special_char'] = info['dmodel'].translate(None, ' ,/-=._')
    info['smodel_no_special_char'] = info['smodel'].translate(None, ' ,/-=._')
    m_check_ret = check_metadatatoph5_format(
        Response_t, info, header, errors, logger)

    if m_check_ret is not True:
        check_sensor(
            Response_t, info, header, errors, logger)

        check_das_resp_load_format(
            Response_t, info, header, errors, logger, m_check_ret)

    das_resp_path = Response_t['response_file_das_a']
    sens_resp_path = Response_t['response_file_sensor_a']
    data_errors = []

    if das_resp_path == '':
        errmsg = "%sresponse_file_das_a is blank." % header
        data_errors.append(errmsg)
    else:
        try:
            check_resp_data(ph5.ph5, das_resp_path, header,
                            checked_data_files, info['n_i'])
        except Exception as e:
            data_errors.append(str(e))
    if sens_resp_path != '':
        try:
            check_resp_data(ph5.ph5, sens_resp_path, header,
                            checked_data_files, info['n_i'])
        except Exception as e:
            data_errors.append(str(e))
    if data_errors != []:
        return False, data_errors
    return das_resp_path, sens_resp_path


def check_resp_unique_n_i(ph5, errors, logger=None):
    # check for duplicated n_i in response table
    n_i_list = [e['n_i'] for e in ph5.Response_t['rows']]
    dup_indexes = set([i for i in n_i_list
                       if n_i_list.count(i) > 1])
    if len(dup_indexes) != 0:
        errmsg = ("Response_t n_i(s) duplicated: %s. "
                  "Try to rerun resp_load to see if it fix the problem."
                  % ','.join(map(str, dup_indexes)))
        addLog(errmsg, errors, logger)
        return errmsg
    return True


def check_has_response_filename(Response_t, errors, logger):
    # check if Response table contain any response file name
    for entry in Response_t['rows']:
        if entry['response_file_das_a'] != '':
            return True
    errmsg = ("Response table does not contain any response file names. "
              "Check if resp_load has been run or if metadatatoph5 input "
              "contained response information.")
    addLog(errmsg, errors, logger)
    return errmsg


def check_lat_lon_elev(station):
    errors = []
    warnings = []
    if station['location/X/value_d'] == 0:
        warnings.append("Channel longitude seems to be 0. Is this correct???")
    if not -180 <= float(station['location/X/value_d']) <= 180:
        errors.append("Channel longitude %s not in range [-180,180]"
                      % station['location/X/value_d'])
    if station['location/X/units_s'] in [None, '']:
        warnings.append("No Station location/X/units_s value found.")

    if station['location/Y/value_d'] == 0:
        warnings.append("Channel latitude seems to be 0. Is this correct???")
    if not -90 <= float(station['location/Y/value_d']) <= 90:
        errors.append("Channel latitude %s not in range [-90,90]"
                      % station['location/Y/value_d'])
    if station['location/Y/units_s'] in [None, '']:
        warnings.append("No Station location/Y/units_s value found.")
    if station['location/Z/units_s'] in ['unknown', 'UNKNOWN', 'Unknown']:
        warnings.append("location/Z/units_s is set as unknown."
                        + " Consider updating this unit to m.")
    if station['location/Z/value_d'] == 0:
        warnings.append("Channel elevation seems to be 0. Is this correct???")
    if station['location/Z/units_s'] in [None, '']:
        warnings.append("No Station location/Z/units_s value found.")
    return errors, warnings
