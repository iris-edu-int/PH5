#!/usr/bin/env pnpython3
#
# Update a ph5 file from a kef file
#
# Steve Azevedo, January 2007
#

import argparse
import logging
import os
import os.path
import time
from ph5.core import experiment, kefx, columns

PROG_VERSION = '2018.268'
LOGGER = logging.getLogger(__name__)

# Force time zone to UTC
os.environ['TZ'] = 'UTC'
time.tzset()


def get_args():
    global KEFFILE, PH5, PATH, TRACE

    parser = argparse.ArgumentParser(
                                formatter_class=argparse.RawTextHelpFormatter)

    parser.usage = ("kef2ph5 --kef kef_file --nickname ph5_file_prefix "
                    "[--path path]")

    parser.description = ("Update a ph5 file from a kef file.\n\nVersion: {0}"
                          .format(PROG_VERSION))

    parser.add_argument("-n", "--nickname", dest="outfile",
                        help="The ph5 file prefix (experiment nickname).",
                        required=True)
    parser.add_argument("-k", "--kef", dest="keffile",
                        help="Kitchen Exchange Format file.", required=True)
    parser.add_argument("-p", "--path", dest="path",
                        help="Path to directory where ph5 files are stored.",
                        default=".")
    parser.add_argument("-c", "--check", action="store_true", default=False,
                        dest="check",
                        help="Show what will be done but don't do it!")

    args = parser.parse_args()

    KEFFILE = args.keffile
    PH5 = args.outfile
    PATH = args.path
    TRACE = args.check


def initializeExperiment():
    global EX, PH5, PATH

    EX = experiment.ExperimentGroup(nickname=PH5, currentpath=PATH)
    EDIT = True
    EX.ph5open(EDIT)
    EX.initgroup()


def add_references(rs):
    '''   Add a reference for each Das_t so we can look it up later   '''
    import string
    global EX

    for r in rs:
        flds = string.split(r, '/')
        das = string.split(flds[3], '_')[2]
        g = EX.ph5_g_receivers.getdas_g(das)
        EX.ph5_g_receivers.setcurrent(g)
        # Set reference
        columns.add_reference(r, EX.ph5_g_receivers.current_t_das)


def populateTables():
    global EX, KEFFILE, TRACE
    LOGGER.info("Loading {0} into {1}.".format(KEFFILE, PH5))
    k = kefx.Kef(KEFFILE)
    k.open()

    while True:
        n = k.read(1000000)
        if n == 0:
            err = "Empty kef file."
            break

        # Get Das_g references
        ret = k.strip_receiver_g()

        if ret:
            add_references(ret)

        # Make sure Array_t_xxx, Event_t_xxx, and Offset_t_aaa_sss exist
        arrays, events, offsets = k.strip_a_e_o()
        if arrays:
            for a in arrays:
                a = a.split(':')[0]
                EX.ph5_g_sorts.newArraySort(a)

        if events:
            for e in events:
                e = e.split(':')[0]
                EX.ph5_g_sorts.newEventSort(e)

        if offsets:
            for o in offsets:
                o = o.split(':')[0]
                EX.ph5_g_sorts.newOffsetSort(o)

        if TRACE is True:
            err = k.batch_update(trace=True)
        else:
            err = k.batch_update()

    k.close()
    if err is True:
        LOGGER.error("There were errors! See output.")


def closePH5():
    global EX
    EX.ph5close()


def update_log():
    '''   Write a log of kef2ph5 activities.   '''
    global PH5, KEFFILE, PATH, TRACE
    # Don't log when run with the -c option
    if TRACE is True:
        return

    keffile = KEFFILE
    ph5file = os.path.join(PATH, PH5)
    klog = os.path.join(PATH, "kef2ph5.log")

    kef_mtime = time.ctime(os.stat(keffile).st_mtime)
    now = time.ctime(time.time())

    line = "%s*:*%s*:*%s*:*%s\n" % (now, ph5file, keffile, kef_mtime)
    if not os.path.exists(klog):
        line = "modification_time*:*experiment_nickname*:*\
        kef_filename*:*kef_file_mod_time\n" + \
               "-------------------------------------------------------------\
               -------------\n" + line

    try:
        LOGGER.info("Updated kef2ph5.log file.")
        fh = open(klog, 'a+')
        fh.write(line)
        fh.close()
    except BaseException:
        LOGGER.warning("Failed to write kef2ph5.log file.")


def main():
    get_args()
    initializeExperiment()
    populateTables()
    closePH5()
    update_log()


if __name__ == '__main__':
    main()
