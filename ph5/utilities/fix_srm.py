#
# Lan Dam, November 2020
#

import argparse
import os
import sys
import logging
import tables

from ph5.core import ph5api, experiment, columns
from ph5.utilities import nuke_table, kef2ph5 as K2T, tabletokef as T2K
from ph5 import LOGGING_FORMAT

PROG_VERSION = '2021.159'
LOGGER = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("fix_srm --nickname ph5-file-prefix [options]")

    parser.description = ("Change sample_rate_multiplier_i=0 to 1 "
                          "Or adding sample_rate_multiplier_i=1 in case "
                          "the field is missing in"
                          "Das table(s) or Array table(s). \nVersion: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="ph5_file_prefix",
                        help="The ph5 file prefix (experiment nickname).",
                        metavar="ph5_file_prefix", required=True)

    parser.add_argument("-p", "--path", dest="ph5_path",
                        help="Path to ph5 files. Default to current "
                             "directory.",
                        metavar="ph5_path", default=".")

    args = parser.parse_args()
    ph5 = args.ph5_file_prefix
    path = args.ph5_path
    return ph5, path


def set_logger():
    """
    Setting logger's format and filehandler
    """

    # set filehandler
    ch = logging.FileHandler("fix_srm.log")
    ch.setLevel(logging.INFO)
    # Add formatter
    formatter = logging.Formatter(LOGGING_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)


def init_T2K(ph5object):
    T2K.LOGGER = LOGGER
    nuke_table.LOGGER = LOGGER
    T2K.init_local()
    T2K.EX = ph5object
    nuke_table.NO_BACKUP = False


def reformat_das_t(ph5object, das_sn, ph5, path):
    '''
    remove das_t and reformat from ph3 to pn4
    :param ph5object: ph5 object where the das table will be deleted
    :param das_sn: serial number of das to be deleted Ex: '1X1111'
            Ex: 'Das_t_1X1111'
    :param ph5: name of ph5 file (str)
    :param path: path to ph5 file (str)
    :return
        backupfile: name of the kef file to backup the deleted table (str)
        datapath: path to the table in ph5 structure
        ph5object: ph5 object of which das table has been deleted
    '''
    # get mini_file that keep the passed das's data
    index_rows, keys = ph5object.ph5_g_receivers.read_index()

    mini_filename = None
    for i in index_rows:
        if i['serial_number_s'] == das_sn:
            mini_filename = i['external_file_name_s']
            break
    if mini_filename is None:
        raise Exception("DAS %s cannot be found in index table." % das_sn)

    if not os.path.exists(os.path.join(path, mini_filename)):
        raise Exception("external_file_name_s '%s' for DAS %s in index_t "
                        "can't be found in %s." %
                        (mini_filename, das_sn, path))

    # open mini ph5 file to reformat das_t from pn3 to pn4
    # because das_t is read-only when opened from ph5object
    exrec = experiment.ExperimentGroup(nickname=mini_filename,
                                       currentpath=path)
    exrec.ph5open(True)
    exrec.initgroup()
    # remove das_t and re-initialize das_t with pn4's structure
    das_t = exrec.ph5_g_receivers.ph5.get_node(
        '/Experiment_g/Receivers_g/Das_g_%s' % das_sn,
        name='Das_t',
        classname='Table')
    das_t.remove()
    experiment.initialize_table(
        exrec.ph5_g_receivers.ph5,
        '/Experiment_g/Receivers_g/Das_g_%s' % das_sn,
        'Das_t',
        columns.Data, expectedrows=1000)
    exrec.ph5close()
    # The changes have happened on exrec, NOT on ph5object.
    # Now need to close and re-open ph5object to update all those changes.
    ph5object.close()
    ph5object = ph5api.PH5(path=path, nickname=ph5, editmode=True)

    # ph5object has been reopened, need to return for uses afterward
    return ph5object


def delete_das(ph5object, das_name, ph5, path):
    """
    Delete das table identified by das_name from ph5object
    :param ph5object: ph5 object where the das table will be deleted
    :param das_name: string to identify das table to be deleted
            Ex: 'Das_t_1X1111'
    :param ph5: name of ph5 file (str)
    :param path: path to ph5 file (str)
    :return
        backupfile: name of the kef file to backup the deleted table (str)
        datapath: path to the table in ph5 structure
        ph5object: ph5 object of which das table has been deleted
    """
    das_sn = das_name.replace("Das_t_", "")
    das = ph5object.ph5_g_receivers.getdas_g(das_sn)
    if das is None:
        raise Exception('DAS %s not exist.' % das_sn)
    ph5object.ph5_g_receivers.setcurrent(das)
    das, das_keys = experiment.read_table(
        ph5object.ph5_g_receivers.current_t_das)
    das_t = T2K.Rows_Keys(das, das_keys)
    datapath = '/Experiment_g/Receivers_g/Das_g_{0}/Das_t'.format(das_sn)
    backupfile = nuke_table.backup(
        das_name,
        datapath,
        das_t)
    if 'sample_rate_multiplier_i' not in das_keys:
        ph5object = reformat_das_t(ph5object, das_sn, ph5, path)
    else:
        ph5object.ph5_g_receivers.nuke_das_t(das_sn)
    LOGGER.info('Nuke {0}.'.format(datapath))
    return backupfile, datapath, ph5object


def delete_array(ph5object, array_name):
    """
    Delete array table identified by array_name from ph5object
    :param ph5object: ph5 object where the array table will be deleted
    :param array_name: string to identify array table to be deleted.
            Ex: 'Array_t_001'
    :return
        backupfile: name of the kef file to backup the deleted table(str)
        datapath: path to the table in ph5 structure
    """
    array_id = int(array_name.replace('Array_t_', ''))
    try:
        array, array_keys = ph5object.ph5_g_sorts.read_arrays(array_name,
                                                              ignore_srm=True)
    except tables.exceptions.NoSuchNodeError:
        raise Exception('Array %s not exist.' % array_name)
    array_t = T2K.Rows_Keys(array, array_keys)
    datapath = '/Experiment_g/Sorts_g/{0}'.format(array_name)
    backupfile = nuke_table.backup(
        array_name,
        datapath,
        array_t)
    ph5object.ph5_g_sorts.nuke_array_t(array_id)
    LOGGER.info('Nuke {0}.'.format(datapath))
    return backupfile, datapath


def fix_srm_in_kef(startfilepath, fixedfilepath, datapath):
    """
    Correct sample rate multiplier (srm) from kef file startfilepath and
    save into fixedfilepath as following:
        + replace srm=0 with srm=1
        + add srm=1 for each data row if there is no srm
    :param startfilepath: name of kef file for das table (str)
    :param fixedfilepath: name of kef file in which srms are fixed (str)
    :param datapath: path to the table in ph5 structure
    """
    startfile = open(startfilepath, 'r')
    fixedfile = open(fixedfilepath, 'w')
    content = startfile.read()
    # occurrences of sample_rate_multiplier_i
    srm_occ = [i for i in range(len(content))
               if content.startswith('sample_rate_multiplier_i=0', i)]

    if 'sample_rate_multiplier_i' in content:
        # there are sample_rate_multiplier_i(s) in kef file,
        # => replace value 0 with value 1
        content = content.replace('sample_rate_multiplier_i=0',
                                  'sample_rate_multiplier_i=1')
        logmsg = ('Convert {0} sample_rate_multiplier_i=0 to 1 in {1} and '
                  'save in {2}.').format(len(srm_occ),
                                         startfilepath,
                                         fixedfilepath)
    else:
        content = content.replace(datapath,
                                  datapath + '\n\tsample_rate_multiplier_i=1')
        logmsg = ('Add sample_rate_multiplier_i=1 to {0} and '
                  'save in {1}.').format(startfilepath,
                                         fixedfilepath)

    fixedfile.write(content)
    startfile.close()
    fixedfile.close()
    LOGGER.info(logmsg)


def add_fixed_table(ex, ph5, path, fixedfilepath):
    """
    Add fixed kef file to ex of which the table has been removed.
    The fixed kef file will be deleted after added to ex.
    :param ex: experiment where the das table has been deleted (experiment)
    :param ph5: name of ph5 file (str)
    :param path: path to ph5 file (str)
    :param fixedfilepath: name of the fixed kef file to be added
        to the experiment (str)
    """
    K2T.LOGGER = LOGGER
    K2T.EX = ex
    K2T.KEFFILE = fixedfilepath
    K2T.TRACE = False
    K2T.PH5 = ph5
    K2T.PATH = path
    K2T.populateTables()
    os.unlink(fixedfilepath)


def process(ph5object, ph5, path, das_name=None, array_name=None):
    """
    Correct srm in a das identified by das_sn or
     in an array identify by array_id.
    :param ph5object: ph5object where the das table's srm need to be corrected
    :param ph5: name of ph5 file (str)
    :param path: path to ph5 file (str)
    :param das_name: name of das table of which srm need to be corrected (str)
    :param array_name: name of array table of which srm need
        to be corrected (str)
    """
    fixedfilepath = 'fixed.kef'

    if das_name is not None:
        LOGGER.info('>>> Processing Das: %s' % das_name)
        backupfile, datapath, ph5object = delete_das(
            ph5object, das_name, ph5, path)
    else:
        LOGGER.info('>>> Processing Array: %s' % array_name)
        backupfile, datapath = delete_array(ph5object, array_name)
    fix_srm_in_kef(backupfile, fixedfilepath, datapath)
    add_fixed_table(ph5object, ph5, path, fixedfilepath)
    return ph5object


def main():
    ph5, path = get_args()
    set_logger()
    ph5object = ph5api.PH5(path=path, nickname=ph5, editmode=True)
    LOGGER.info("fix_srm {0}".format(PROG_VERSION))
    LOGGER.info("{0}".format(sys.argv))
    init_T2K(ph5object)
    try:
        # fix all das tables
        ph5object.read_das_g_names()
        for das_g_name in ph5object.Das_g_names.keys():
            das_t_name = das_g_name.replace('Das_g_', 'Das_t_')
            ph5object = process(ph5object, ph5, path, das_name=das_t_name)
        # fix all array tables
        ph5object.ph5_g_sorts.read_sorts()
        for array_name in ph5object.ph5_g_sorts.names():
            process(ph5object, ph5, path, array_name=array_name)
    except Exception as e:
        LOGGER.error(e.message)

    ph5object.close()


if __name__ == '__main__':
    main()
