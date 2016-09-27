#!/usr/bin/env pnpython3
#
#   Create Receiver order gathers from a ph5 file.
#   Steve Azevedo, Jan 2011
# 
#

import sys, os, os.path, time, copy, logging, traceback
#   Get our environment so we can find our libraries
sys.path.append (os.path.join (os.environ['K3'], "apps", "pn3"))
#   This provides the base functionality
import Experiment, SEGYFactory, decimate #, TimeDOY
#   The wiggles are stored as numpy arrays
import numpy

#   Make sure we are all on the same time zone ;^)
os.environ['TZ'] = 'UTC'
time.tzset ()

PROG_VERSION = '2016.217 Developmental'

#   Maximum samples in standard SEG-Y trace (2 ^ 15 - 1)
MAX_16 = 32767
#   Maximum samples for PASSCAL SEGY trace (2 ^ 31 - 1)
MAX_32 = 2147483647
#   Default Maximum samples
MAXSAMPLES = MAX_16

CHAN_MAP = { 1:'Z', 2:'N', 3:'E', 4:'Z', 5:'N', 6:'E' }
#
#   These are to hold different parts of the meta-data
#
#   /Experiment_g/Experiment_t
EXPERIMENT_T = None
#   /Experiment_g/Sorts_g/Event_t
EVENT_T = {}
#   /Experiment_g/Sorts_g/Offset_t, keyed by station then shot id
OFFSET_T = {}
#   /Experiment_g/Sorts_g/Sort_t
SORT_T = None
#   /Experiment_g/Responses_g/Response_t
RESPONSE_T = None
#   /Experiment_g/Sorts_g/Array_t_[nnn]
ARRAY_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/Das_t (keyed on DAS)
DAS_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/Receiver_t (keyed on DAS)
RECEIVER_T = {}
#   /Experiment_g/Receivers_g/Das_g_[sn]/SOH_a_[n] (keyed on DAS then by SOH_a_[n] name) 
SOH_A = {}
#   A list of das_groups that refers to Das_g_[sn]'s
DASS = []
DASSN = []
#   offset_t = KEYED_SHOT[shot][station]
KEYED_SHOT = None
#
TIME_T = None
#   Comma separated list of stations
STATIONS = None
#   Output path
OUTPATH = '.'
#   Length of trace in seconds
LENGTH = None
#   Offset in seconds
OFFSET = 0
#   Range of shots
a = (2**31) - 1
b = -a - 1
SHOTRANGE = [ b, a ]
#   Reduction velocity
RED_VEL = None
#   Sort shots by offset
SORT_OFFSETS = False
#
UTM = False
#
EXT = 'S'
#
DEPLOY_PICKUP = False
#
BREAK_STANDARD = False
###   ZZZ   ###
EVT_LIST = None

DECIMATION_FACTORS = { '2': '2', '4': '4', '5': '5', '8': '4,2', '10': '5,2', '20': '5,4' } 

#
#   To hold table rows and keys
#
class rows_keys (object) :
    __slots__ = ('rows', 'keys')
    def __init__ (self, rows = None, keys = None) :
        self.rows = rows
        self.keys = keys
        
    def set (self, rows = None, keys = None) :
        if rows != None : self.rows = rows
        if keys != None : self.keys = keys

#
#   To hold DAS sn and references to Das_g_[sn]
#
class das_groups (object) :
    __slots__ = ('das', 'node')
    def __init__ (self, das = None, node = None) :
        self.das = das
        self.node = node

#
#   Read Command line arguments
#
def get_args () :
    global PH5, PATH, DEBUG, STATIONS, CHANNEL, LENGTH, OFFSET, FORMAT, SHOT_RANGE, OUTPATH, SHOTRANGE, RED_VEL, UTM
    global DECIMATION, SORT_OFFSETS, EXT, DEPLOY_PICKUP, BREAK_STANDARD, IGNORE_CHANNEL, EVT_LIST, ARRAY_NAME, SHOT_LINE_NAME
    
    from optparse import OptionParser
    
    oparser = OptionParser ()
    
    oparser.usage = "Version: {0}: recvorder --nickname ph5-file-prefix [--path path-to-ph5-files]".format (PROG_VERSION)
    
    oparser.description = "Generate gathers in receiver order..."
    
    oparser.add_option ("-n", "--nickname", dest = "ph5_file_prefix",
                        help = "The ph5 file prefix (experiment nickname).",
                        metavar = "ph5_file_prefix")
    
    oparser.add_option ("-p", "--path", dest = "ph5_path",
                        help = "Path to ph5 files. Defaults to current directory.",
                        metavar = "ph5_path")
    
    oparser.add_option ("-c", "--channel", action="store",
                        type="int", dest="channel", metavar="channel")
    
    oparser.add_option ("-S", "--stations", dest="stations_to_gather",
                        help = "Comma separated list of stations to receiver gather.",
                        metavar = "stations_to_gather")
    ###   ZZZ   ###
    oparser.add_option ("--event_list", dest="evt_list",
                        help = "Comma separated list of event id's to gather from defined or selected events.",
                        metavar="evt_list")
    
    oparser.add_option ("-l", "--length", action="store",
                        type="int", dest="length", metavar="length")
    
    oparser.add_option ("-A", "--station_array", dest="station_array", action="store",
                        help = "The array number that holds the station(s).",
                        type="int", metavar="station_array")
    
    oparser.add_option ("-E", "--shot_line", dest="shot_line", action="store",
                        help = "The shot line number that holds the shots.",
                        type="int", metavar="shot_line")
    
    #oparser.add_option ("-O", "--offset", action="store", default=0.0,
                        #type="float", dest="offset", metavar="offset")
    
    oparser.add_option ("-o", "--out_dir", action="store", dest="out_dir", 
                        metavar="out_dir", type="string", default=".")
    
    oparser.add_option ("-f", "--format", action="store", choices=["SEGY", "PSGY"],
                        dest="format", metavar="format")
    
    oparser.add_option ("-r", "--shot_range", action="store", dest="shot_range",
                        help="example: --shot_range=1001-1100",
                        metavar="shot_range")
    
    oparser.add_option ("-V", "--reduction_velocity", action="store", dest="red_vel",
                        metavar="red_vel", type="float", default="-1.")
    
    oparser.add_option ("-d", "--decimation", action="store",
                        choices=["2", "4", "5", "8", "10", "20"], dest="decimation",
                        metavar="decimation")
    
    oparser.add_option ("--sort_by_offset", action="store_true", dest="sort_by_offset",
                        default=False, metavar="sort_by_offset")
    
    oparser.add_option ("--use_deploy_pickup", action="store_true", default=False,
                        help="Use deploy and pickup times to determine if data exists for a station.",
                        dest="deploy_pickup", metavar="deploy_pickup")
    
    oparser.add_option ("-U", "--UTM", action="store_true", dest="use_utm",
                        help="Fill SEG-Y headers with UTM instead of lat/lon.",
                        default=False, metavar="use_utm")
    
    oparser.add_option ("-x", "--extended_header", action="store", dest="ext_header",
                        help="Extended trace header style: \
                        'P' -> PASSCAL, \
                        'S' -> SEG, \
                        'U' -> Menlo USGS",
                        choices=["P", "S", "U"], default="S", metavar="extended_header_style") 
    
    oparser.add_option ("--ic", action="store_true", dest="ignore_channel", default=False)
    
    oparser.add_option ("--break_standard", action = "store_true", dest = "break_standard",
                        default = False, metavar = "break_standard")
    
    oparser.add_option ("--debug", dest = "debug", action = "store_true", default = False)
    
    options, args = oparser.parse_args ()
    
    if options.ph5_file_prefix != None :
        PH5 = options.ph5_file_prefix
    else :
        PH5 = None
        
    if options.ph5_path != None :
        PATH = options.ph5_path
    else :
        PATH = "."
        
    PH5 = os.path.join (PATH, PH5)
    
    if options.debug != None :
        DEBUG = options.debug
    
    if options.station_array == None :
        sys.stderr.write ("Error: Array number via the -A option is required.")
        sys.exit ()
    else :
        ARRAY_NAME = "Array_t_{0:03d}".format (options.station_array)
        
    if options.shot_line == None :
        sys.stderr.write ("Error: Shot line number is required via the -E option. Set to 0 for Event_t.")
        sys.exit ()
    else :
        SHOT_LINE_NAME = "Event_t_{0:03d}".format (options.shot_line)
        if SHOT_LINE_NAME == "Event_t_000" : SHOT_LINE_NAME = "Event_t"  
        
    IGNORE_CHANNEL = options.ignore_channel        
    BREAK_STANDARD = options.break_standard
    UTM = options.use_utm
    LENGTH = options.length
    #OFFSET = options.offset
    OUTPATH = options.out_dir
    RED_VEL = options.red_vel
    DECIMATION = options.decimation
    SORT_OFFSETS = options.sort_by_offset
    EXT = options.ext_header
    DEPLOY_PICKUP = options.deploy_pickup
    FORMAT = options.format
    if FORMAT == 'PSGY' or BREAK_STANDARD :
        MAXSAMPLES = MAX_32
        
    if options.stations_to_gather != None :
        STATIONS = options.stations_to_gather.split (',')
    else :
        STATIONS = None
    ###   ZZZ   ###    
    try :
        if options.evt_list :
            tmp = options.evt_list.split (",")
            EVT_LIST = [int (a.strip ()) for a in tmp]
    except :
        EVT_LIST = None
        sys.stderr.write ("Warning: Could not interpret event_list: {0}".format (options.evt_list))
    
    if options.channel : 
        CHANNEL = options.channel
    else : CHANNEL = None
    
    if options.shot_range != None :
        try :
            SHOTRANGE = options.shot_range.split ('-')
            SHOTRANGE = map (lambda a : int (a), SHOTRANGE)
        except Exception, e:
            sys.stderr.write ("Can't read shot range {0:s}".format (e))
            sys.exit ()
        
    #if PH5 == None or LENGTH == None or not STATIONS :
        #sys.stderr.write ("Error: Missing required option. Try --help\n")
        #sys.exit (-1)
        
    if not os.path.exists (PH5) and not os.path.exists (PH5 + '.ph5') :
        sys.stderr.write ("Error: %s does not exist!\n" % PH5)
        sys.exit ()

    #   Set up logging
    if not os.path.exists (OUTPATH) :
        os.mkdir (OUTPATH)
        os.chmod(OUTPATH, 0777)

    logging.basicConfig (
        filename = os.path.join (OUTPATH, "recvorder.log"),
        format = "%(asctime)s %(message)s",
        level = logging.INFO
    )
    if LENGTH == None or PH5 == None or not STATIONS :
        logging.error ("Error: Length of trace in seconds or list of stations or path to PH5 master file missing.")
        logging.error ("See: -n, -p, -S, or -l options.")
        sys.exit (-1)
        
    if options.shot_range != None :
        try :
            SHOTRANGE = options.shot_range.split ('-')
            SHOTRANGE = map (lambda a : int (a), SHOTRANGE)
        except Exception, e:
            logging.error ("Error: Can't read shot range {0:s}".format (e))
            sys.exit (-2)
        
#   Convert from polar to rectangular coordinates
def rect(r, w, deg=0): 
    # radian if deg=0; degree if deg=1 
    from math import cos, sin, pi 
    if deg: 
        w = pi * w / 180.0 
    #   return x, y
    return r * cos(w), r * sin(w) 

#   Linear regression, return coefficients a and b (a/b and c)
""" Returns coefficients to the regression line "y=ax+b" from x[] and y[]. 
    Basically, it solves 
        Sxx a + Sx b = Sxy 
        Sx a + N b = Sy 
    where Sxy = \sum_i x_i y_i, Sx = \sum_i x_i, and Sy = \sum_i y_i. 
    The solution is 
        a = (Sxy N - Sy Sx)/det 
        b = (Sxx Sy - Sx Sxy)/det 
    where det = Sxx N - Sx^2. In addition, 
    Var|a| = s^2 |Sxx Sx|^-1 = s^2 | N -Sx| / det 
       |b|       |Sx N |           |-Sx Sxx| 
    s^2 = {\sum_i (y_i - \hat{y_i})^2 \over N-2} 
        = {\sum_i (y_i - ax_i - b)^2 \over N-2} 
        = residual / (N-2) 
    R^2 = 1 - {\sum_i (y_i - \hat{y_i})^2 \over \sum_i (y_i - \mean{y})^2} 
        = 1 - residual/meanerror 
        
    It also prints to <stdout> few other data, N, a, b, R^2, s^2, 
    which are useful in assessing the confidence of estimation. 
""" 
def linreg(X, Y): 
    from math import sqrt 
    if len(X) != len(Y): 
        raise ValueError, 'Unequal length, X and Y. Can\'t do linear regression.' 
    
    N = len(X) 
    Sx = Sy = Sxx = Syy = Sxy = 0.0 
    for x, y in map(None, X, Y): 
        Sx = Sx + x 
        Sy = Sy + y 
        Sxx = Sxx + x*x 
        Syy = Syy + y*y 
        Sxy = Sxy + x*y 
        
    det = Sxx * N - Sx * Sx
    if det == 0 :
        return 0.0, 0.0
    
    a, b = (Sxy * N - Sy * Sx)/det, (Sxx * Sy - Sx * Sxy)/det 
    
    meanerror = residual = 0.0 
    for x, y in map(None, X, Y): 
        meanerror = meanerror + (y - Sy/N)**2 
        residual = residual + (y - a * x - b)**2 
        
    RR = 1 - residual/meanerror
    if N > 2 :
        ss = residual / (N-2)
    else :
        ss = 1.
        
    Var_a, Var_b = ss * N / det, ss * Sxx / det 
    
    #print "y=ax+b" 
    #print "N= %d" % N 
    #print "a= %g \\pm t_{%d;\\alpha/2} %g" % (a, N-2, sqrt(Var_a)) 
    #print "b= %g \\pm t_{%d;\\alpha/2} %g" % (b, N-2, sqrt(Var_b)) 
    #print "R^2= %g" % RR 
    #print "s^2= %g" % ss 
    
    return a, b, (RR, ss)

def calc_offset_sign (offsets) :
    '''   offsets is a list of offset_t   '''
    from math import atan, degrees
    X = []; Y = []; O = []
    for offset_t in offsets :
        try :
            w = offset_t['azimuth/value_f']
            r = offset_t['offset/value_d']
            x, y = rect (r, w, deg=True)
            X.append (x); Y.append (y)
        except Exception, e :
            sys.stderr.write ("%s\n" % e)
            
    #   The seismic line is abx + c (ab => w)   
    ab, c, err = linreg (X, Y)
    
    logging.info ("Linear regression: {0}x + {1}, R^2 = {2}, s^2 = {3}".format (ab, c, err[0], err[1]))
    
    if abs (ab) > 1 :
        regangle = degrees (atan (1./ab))
    else :
        regangle = degrees (atan (ab))
        
    #print "RR: {2} Rise / Run {1} Regression angle: {0}".format (regangle, ab, err[0])
    #if regangle < 0 :
        #regangle += 180.
    #else :
        #regangle = 90. - regangle
        
    #print " Corrected: {0}".format (regangle)
    
    for offset_t in offsets :
        try :
            #   Rotate line to have zero slope
            a = offset_t['azimuth/value_f']
                
            w = a - regangle
            #if offset_t['receiver_id_s'][0] == '3' :
                #print "Receiver: {2} Azimuth: {0} Corrected azimuth: {1}".format (a, w, offset_t['receiver_id_s'])
            #   Use azimuth to determine sign of offset
            if w < 0 :
                '''   esquerdo   '''
                offset_t['offset/value_d'] = -1.0 * float (offset_t['offset/value_d'])
            else :
                '''   direita   '''
                offset_t['offset/value_d'] = float (offset_t['offset/value_d'])
            
            #print "w: ", w, "regangle: ", regangle, "offset: ", offset_t['offset/value_d']
            O.append (offset_t)
        except Exception, e :
            sys.stderr.write ("%s\n" % e)
            
    #   XXX        
    sys.stdout.flush ()
    #   Returning Oh not zero
    return O

#
#   Initialize ph5 file
#
def initialize_ph5 (editmode = False) :
    '''   Initialize the ph5 file   '''
    global EX, PATH, PH5
    
    EX = Experiment.ExperimentGroup (PATH, PH5)
    EX.ph5open (editmode)
    EX.initgroup ()

#
#   Print rows_keys
#
def debug_print (a) :
    i = 1
    #   Loop through table rows
    for r in a.rows :
        #   Print line number
        print "%d) " % i,
        i += 1
        #   Loop through each row column and print
        for k in a.keys :
            print k, "=>", r[k], ",",
        print
        
def read_experiment_table () :
    '''   Read /Experiment_g/Experiment_t   '''
    global EX, EXPERIMENT_T
    
    exp, exp_keys = EX.read_experiment ()
    
    rowskeys = rows_keys (exp, exp_keys)
    
    return rowskeys
    
def read_event_table () :
    '''   Read /Experiment_g/Sorts_g/Event_t   '''
    global EX, EVENT_T, EVENT_LINES, SHOT_LINE_NAME
    
    names = EX.ph5_g_sorts.namesEvent_t ()
    if SHOT_LINE_NAME == "Event_t_000" : SHOT_LINE_NAME = "Event_t"
    for name in names : 
        if name != SHOT_LINE_NAME : continue
        events, event_keys = EX.ph5_g_sorts.read_events (name)
        rowskeys = rows_keys (events, event_keys)
        EVENT_T[name] = rowskeys
    
def read_offset_table () :
    '''   Read /Experinent_t/Sorts_g/Offset_t   '''
    global EX, OFFSET_T, SHOTRANGE, STATIONS
    import ph5API
    
    p = ph5API.ph5 (path=PATH, nickname=PH5)
    
    OFFSET_T = {}
    for station_id in STATIONS :
        OFFSET_T[station_id] = p.read_offsets_receiver_order (ARRAY_NAME, 
                                                              station_id, 
                                                              shot_line=SHOT_LINE_NAME)
    ##   Have we changed SHOTRANGE
    #if SHOTRANGE[1] != (2**31) - 1 :
        #SR = SHOTRANGE
    #else :
        #SR = None
        
    #offsets, offset_keys = EX.ph5_g_sorts.read_offsets (shotrange=SR, stations=STATIONS)
    
    #rowskeys = rows_keys (offsets, offset_keys)
    
    #OFFSET_T = rowskeys
    
def read_sort_table () :
    '''   Read /Experiment_t/Sorts_g/Sort_g   '''
    global EX, SORT_T
    
    sorts, sorts_keys = EX.ph5_g_sorts.read_sorts ()
    
    rowskeys = rows_keys (sorts, sorts_keys)
    
    SORT_T = rowskeys
    
def read_sort_arrays () :
    '''   Read /Experiment_t/Sorts_g/Array_t_[n]   '''
    global EX, ARRAY_T, STATION_LINES
    
    #   We get a list of Array_t_[n] names here...
    #   (these are also in Sort_t)
    names = EX.ph5_g_sorts.names ()
    for name in names :
        arrays, array_keys = EX.ph5_g_sorts.read_arrays (name)
        
        rowskeys = rows_keys (arrays, array_keys)
        #   We key this on the name since there can be multiple arrays
        ARRAY_T[name] = rowskeys
    
def read_response_table () :
    '''   Read /Experiment_g/Respones_g/Response_t   '''
    global EX, RESPONSE_T
    
    response, response_keys = EX.ph5_g_responses.read_responses ()
    
    rowskeys = rows_keys (response, response_keys)
    
    RESPONSE_T = rowskeys
    
def read_receivers () :
    '''   Read tables and arrays (except wiggles) in Das_g_[sn]   '''
    global EX, DAS_T, RECEIVER_T, DASS, SOH_A
    
    #   Get references for all das groups keyed on das
    dasGroups = EX.ph5_g_receivers.alldas_g ()
    dass = dasGroups.keys ()
    #   Sort by das sn
    dass.sort ()
    for d in dass :
        #   Get node reference
        g = dasGroups[d]
        dg = das_groups (d, g)
        #   Save a master list for later
        DASS.append (dg)
        
        #   Set the current das group
        EX.ph5_g_receivers.setcurrent (g)
        
        #   Read /Experiment_g/Receivers_g/Das_g_[sn]/Das_t
        das, das_keys = EX.ph5_g_receivers.read_das ()
        rowskeys = rows_keys (das, das_keys)
        DAS_T[d] = rowskeys
        
        #   Read /Experiment_g/Receivers_g/Receiver_t
        receiver, receiver_keys = EX.ph5_g_receivers.read_receiver ()
        rowskeys = rows_keys (receiver, receiver_keys)
        RECEIVER_T[d] = rowskeys
        
        #   Read SOH file(s) for this dasread_experiment_table
        SOH_A[d] = EX.ph5_g_receivers.read_soh ()
        #   Get all of the SOH_a_[n] names
        #soh_names = SOH_A[d].keys ()
        
        #LOG_A[d] = EX.ph5_g_receivers.read_log ()
        
        #EVENT_T[d] = EX.ph5_g_receivers.read_event ()
                
def read_data () :
    '''   Read all of the wiggles and calculate standard deviation of trace data   '''
    global EX, DAS_T, DASS
    
    import numpy.fft
    #   We use this to build up a list of trace standard deviations keyed by epoch ;^)
    tmp = {}
    #   How many points do we read?
    pts = 0
    #   Loop through each Das_g_[sn]
    for dg in DASS :
        das = dg.das
        node = dg.node
        
        #   Set current das
        EX.ph5_g_receivers.setcurrent (node)
        
        rowskeys = DAS_T[das]
        #   Loop through each line in Das_t
        for r in rowskeys.rows :
            #   Get data array name for this trace
            data_array_name = r['array_name_data_a']
            #   Ascii start time
            start = r['time/ascii_s']
            #   Epoch start time
            epoch = r['time/epoch_l']
            #   Make sure it points to a list
            if not tmp.has_key (epoch) :
                tmp[epoch] = []
            
            #   Get node reference to trace array
            trace_ref = EX.ph5_g_receivers.find_trace_ref (data_array_name)
            #   Read the trace
            data = EX.ph5_g_receivers.read_trace (trace_ref)
            #   Update total points
            pts += len (data)
            #   Get spectra
            #spec = numpy.fft.rfft (data, axis = -1)
            #for i in spec :                
                #print i
            #sys.exit ()
            #print spec
            #   Get standard deviation for this data trace spectra and save it in tmp
            std = data.std ()
            tmp[epoch].append (std)
            
    return tmp, pts

#
#
#
def read_time_table () :
    global EX
    
    times, time_keys = EX.ph5_g_receivers.read_time ()
    
    return rows_keys (times, time_keys)

def get_time (Time_t, das, start) :
    
    for r in Time_t.rows :
        if r['das/serial_number_s'].strip () != das :
            continue
        
        if das == 11986 :
            pass
        
        time_start = SEGYFactory.fepoch (r['start_time/epoch_l'], r['start_time/micro_seconds_i'])
        time_stop = SEGYFactory.fepoch (r['end_time/epoch_l'], r['end_time/micro_seconds_i'])
        if start >= time_start and start <= time_stop :
            return r
        
    return None

#
#
#
def read_receiver_table () :
    '''   Read receiver table   '''
    global EX
    
    receiver, receiver_keys = EX.ph5_g_receivers.read_receiver ()
    rowskeys = rows_keys (receiver, receiver_keys)
    
    return rowskeys

#
#   recvorder
#
def cut (start, stop, Das_t, time_t, Response_t, Receiver_t, sf) :
    '''   Cut trace data from the ph5 file   '''
    global EX, CURRENT_TRACE_BYTEORDER, CURRENT_TRACE_TYPE
    
    data = []
    samples_read = 0
    
    #   Loop through each das table line for this das
    for d in Das_t :
        #   Start time and stop time of recording window
        window_start_epoch = SEGYFactory.fepoch (d['time/epoch_l'], d['time/micro_seconds_i'])
        window_sample_rate = d['sample_rate_i'] / float (d['sample_rate_multiplier_i'])
        window_samples = d['sample_count_i']
        window_stop_epoch = window_start_epoch + (window_samples / window_sample_rate)
        
        #   Number of samples left to cut
        cut_samples = int (((stop - start) * window_sample_rate) - samples_read)
        #
        if samples_read == 0 and not DECIMATION :
            sf.set_length_points (cut_samples)
            
        #   How many samples into window to start cut
        cut_start_sample = int ((start - window_start_epoch) * window_sample_rate)
        #   If this is negative we must be at the start of the next recording window
        if cut_start_sample < 0 : cut_start_sample = 0
        #   Last sample in this recording window that we need to cut
        cut_stop_sample = cut_start_sample + cut_samples
        
        #   Read the data trace from this window
        trace_reference = EX.ph5_g_receivers.find_trace_ref (d['array_name_data_a'].strip ())
        data_tmp = EX.ph5_g_receivers.read_trace (trace_reference, 
                                                  start = cut_start_sample,
                                                  stop = cut_stop_sample)
        
        CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER = EX.ph5_g_receivers.trace_info (trace_reference)
        
        #   First das table line
        if data == [] :
            #data.extend (data_tmp)
            #samples_read = len (data)
            #new_window_start_epoch = window_stop_epoch + (1. / window_sample_rate)
            needed_samples = cut_samples
            #   Set das table in SEGYFactory.Ssegy
            sf.set_das_t (d)
            #   Get response table line
            if Response_t :
                try :
                    response_t = Response_t.rows[d['response_table_n_i']]
                except Exception as e :
                    sys.stderr.write ("Response_t error: {0}\n".format (e))
                    response_t = None
            else :
                response_t = None
                
            #   Get receiver table line 
            if Receiver_t :
                try :
                    receiver_t = Receiver_t.rows[d['receiver_table_n_i']]
                except Exception as e :
                    sys.stderr.write ("Receiver_t error: {0}\n".format (e))
                    sys.stderr.write ("Is Receiver_t empty?\n")
                    receiver_t = None
            else :
                receiver_t = None
            
            #   Log information about recorder and sensor
            if response_t :
                sf.set_response_t (response_t)
                logging.info ("Gain: %d %s Bitweight: %g %s" % (response_t['gain/value_i'],
                                                                response_t['gain/units_s'],
                                                                response_t['bit_weight/value_d'],
                                                                response_t['bit_weight/units_s'].strip ()))
            if receiver_t :
                sf.set_receiver_t (receiver_t)
                logging.info ("Component: %s Azimuth: %5.1f %s Dip: %5.1f %s" % (receiver_t['orientation/description_s'].strip (),
                                                                                 receiver_t['orientation/azimuth/value_f'],
                                                                                 receiver_t['orientation/azimuth/units_s'].strip (),
                                                                                 receiver_t['orientation/dip/value_f'],
                                                                                 receiver_t['orientation/dip/units_s'].strip ()))
            #   Log time correction information
            if time_t :
                sf.set_time_t (time_t)
                logging.info ("Clock: Start Epoch: %015.3f End Epoch: %015.3f" % (SEGYFactory.fepoch (time_t['start_time/epoch_l'], time_t['start_time/micro_seconds_i']),
                                                                                  SEGYFactory.fepoch (time_t['end_time/epoch_l'], time_t['end_time/micro_seconds_i'])))
                
                logging.info ("Clock: Offset: %g seconds Slope: %g" % (time_t['offset_d'],
                                                                       time_t['slope_d']))
            else :
                #   Do not apply time correction
                sf.set_time_t (None)
                
        #   We are at the start of the next recording window
        else :
            #   Time difference between the end of last window and the start of this one
            time_diff = abs (new_window_start_epoch - window_start_epoch)
            if time_diff > (1. / window_sample_rate) :
                logging.error ("Error: Attempted to cut past end of recording window and data is not continuous!")
                #return []
                
        if len (data_tmp) > 0 :
            data.extend (data_tmp)
            samples_read = len (data)
            
        new_window_start_epoch = window_stop_epoch + (1. / window_sample_rate)
        
    #   Attempt to cut past end of recording window
    if samples_read < needed_samples :
        logging.error ("Error: Attempted to cut past end of recording window!")
        #return []
                    
    #   Do we need to decimate this trace?
    if DECIMATION :
        shift, data = decimate.decimate (DECIMATION_FACTORS[DECIMATION], data)
        window_sample_rate = int (window_sample_rate / int (DECIMATION))
        sf.set_sample_rate (window_sample_rate)
        samples_read = len (data)
        shift_seconds = float (shift) / window_sample_rate
        if shift_seconds > (1./window_sample_rate) :
            logging.warn ("Warning: Time shift from decimation %06.4f" % shift_seconds)
            pass

    sf.set_length_points (int ((stop - start) * window_sample_rate))
    
    logging.info ("Sample rate: %d Number of samples: %d" % (window_sample_rate, samples_read))
    
    return data


##
##
##
#def cut (start, stop, Das_t, time_t, Response_t, Receiver_t, sf) :
    #'''   Cut trace data from the ph5 file   '''
    #global EX, CURRENT_TRACE_BYTEORDER, CURRENT_TRACE_TYPE
    
    #data = []
    #samples_read = 0
    
    ##   Loop through each das table line for this das
    #for d in Das_t.rows :
        ##   Start time and stop time of recording window
        #window_start_epoch = SEGYFactory.fepoch (d['time/epoch_l'], d['time/micro_seconds_i'])
        #window_sample_rate = d['sample_rate_i'] / float (d['sample_rate_multiplier_i'])
        #window_samples = d['sample_count_i']
        #window_stop_epoch = window_start_epoch + (window_samples / window_sample_rate)
        
        ##   Number of samples left to cut
        #cut_samples = int (((stop - start) * window_sample_rate) - samples_read)
        ##   How many samples into window to start cut
        #cut_start_sample = int ((start - window_start_epoch) * window_sample_rate)
        ##   If this is negative we must be at the start of the next recording window
        #if cut_start_sample < 0 : cut_start_sample = 0
        ##   Last sample in this recording window that we need to cut
        #cut_stop_sample = cut_start_sample + cut_samples
        
        ##   Read the data trace from this window
        #trace_reference = EX.ph5_g_receivers.find_trace_ref (d['array_name_data_a'].strip ())
        #data_tmp = EX.ph5_g_receivers.read_trace (trace_reference, 
                                                  #start = cut_start_sample,
                                                  #stop = cut_stop_sample)
        
        #CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER = EX.ph5_g_receivers.trace_info (trace_reference)
        
        ##   First das table line
        #if data == [] :
            ##data.extend (data_tmp)
            ##samples_read = len (data)
            ##new_window_start_epoch = window_stop_epoch + (1. / window_sample_rate)
            #needed_samples = cut_samples
            ##   Set das table in SEGYFactory.Ssegy
            #sf.set_das_t (d)
            ##   Get response table line
            #if Response_t :
                #response_t = Response_t.rows[d['response_table_n_i']]
            #else :
                #response_t = None
                
            ##   Get receiver table line 
            #if Receiver_t :
                #receiver_t = Receiver_t.rows[d['receiver_table_n_i']]
            #else :
                #receiver_t = None
            
            ##   Log information about recorder and sensor
            #if response_t :
                #sf.set_response_t (response_t)
                #logging.info ("Gain: %d Bitweight: %g %s" % (response_t['gain/value_i'],
                                                             #response_t['bit_weight/value_d'],
                                                             #response_t['bit_weight/units_s'].strip ()))
            #if receiver_t :
                #sf.set_receiver_t (receiver_t)
                #comp = d['channel_number_i']
                #logging.info ("Component: %s Azimuth: %5.1f %s Dip: %5.1f %s" % (CHAN_MAP[comp],
                                                                                 #receiver_t['orientation/azimuth/value_f'],
                                                                                 #receiver_t['orientation/azimuth/units_s'].strip (),
                                                                                 #receiver_t['orientation/dip/value_f'],
                                                                                 #receiver_t['orientation/dip/units_s'].strip ()))
            ##   Log time correction information
            #if time_t :
                #sf.set_time_t (time_t)
                #logging.info ("Clock: Start Epoch: %015.3f End Epoch: %015.3f" % (SEGYFactory.fepoch (time_t['start_time/epoch_l'], time_t['start_time/micro_seconds_i']),
                                                                                  #SEGYFactory.fepoch (time_t['end_time/epoch_l'], time_t['end_time/micro_seconds_i'])))
                
                #logging.info ("Clock: Offset: %g seconds Slope: %g" % (time_t['offset_d'],
                                                                       #time_t['slope_d']))
            #else :
                ##   Do not apply time correction
                #sf.set_time_t (None)
                
        ##   We are at the start of the next recording window
        #else :
            ##   Time difference between the end of last window and the start of this one
            #time_diff = abs (new_window_start_epoch - window_stop_epoch)
            #if time_diff > (1. / window_sample_rate) :
                #logging.error ("Error: Attempted to cut past end of recording window and data is not continuous!")
                #return []
                
        #data.extend (data_tmp)
        #samples_read = len (data)
        #new_window_start_epoch = window_stop_epoch + (1. / window_sample_rate)
        
    ##   Attempt to cut past end of recording window
    #if samples_read < needed_samples :
        #logging.error ("Error: Attempted to cut past end of recording window!")
        #return []
                    
    ##   Do we need to decimate this trace?
    #if DECIMATION :
        #shift, data = decimate.decimate (DECIMATION_FACTORS[DECIMATION], data)
        #window_sample_rate = int (window_sample_rate / int (DECIMATION))
        #sf.set_sample_rate (window_sample_rate)
        #samples_read = len (data)
        #shift_seconds = float (shift) / window_sample_rate
        #if shift_seconds > (1./window_sample_rate) :
            #logging.warn ("Warning: Time shift from decimation %06.4f" % shift_seconds)
            #pass

    #sf.set_length_points (samples_read)
    
    #logging.info ("Sample rate: %d Number of samples: %d" % (window_sample_rate, samples_read))
    
    #return data

#
#   Write standard SEG-Y reel header
#
def write_segy_hdr (data, fd, sf, num_traces) :
    if len (data) > MAX_16 and BREAK_STANDARD == False :
        logging.warn ("Warning: Data trace too long, %d samples, truncating to %d" % (len (data), MAX_16))
        sf.set_length_points (MAX_16)
    else :
        sf.set_length_points (sf.length_points_all)
        
    logging.info ("New " * 10)
    logging.info ("Opening: %s" % fd.name)
    sf.set_data (data[:MAXSAMPLES])
    sf.set_trace_type (CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER)
    try :
        sf.set_text_header () 
        sf.set_reel_header (num_traces) 
        sf.set_trace_header ()
    except SEGYFactory.SEGYError as e :
        logging.error (e.message)
        sys.stderr.write ("{0}\n".format (e.message))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        

        
    try :
        n, nparray = sf.set_data_array ()
    except Exception as e :
        logging.error (e.message)
        sys.stderr.write ("{0}\n".format (e.message))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        
     
    
    try :
        sf.write_text_header (fd)
        sf.write_reel_header (fd)
        sf.write_trace_header (fd)
        sf.write_data_array (fd, nparray)
    except SEGYFactory.SEGYError as e :
        logging.error (e.message)
        sys.stderr.write ("{0}\n".format (e.message))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        

        
    L = len (data)
    p = sf.length_points_all - L
    logging.info ("Wrote: {0:d} samples with {1:d} sample padding.".format (L, p))
    if n != sf.length_points_all :
            logging.warn ("Only wrote {0} samples.".format (n))   
            
#
#   Write SEG-Y trace
#
def write_segy (data, fd, sf) :
    if len (data) > MAX_16 and BREAK_STANDARD == False :
        logging.warn ("Warning: Data trace too long, %d samples, truncating to %d" % (len (data), MAX_16))
        sf.set_length_points (MAX_16)
        sf.set_data (data[:MAXSAMPLES])
    else :
        sf.set_data (data)
    
    try :
        sf.set_trace_type (CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER)
        sf.set_trace_header ()
    except SEGYFactory.SEGYError as e :
        logging.error (e.message)
        sys.stderr.write ("{0}\n".format (e.message))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        

        
    try :
        n, nparray = sf.set_data_array ()
    except Exception as e :
        logging.error (e)
        sys.stderr.write ("{0}\n".format (e))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        
       
    
    try :
        sf.write_trace_header (fd) 
        sf.write_data_array (fd, nparray)
    except SEGYFactory.SEGYError as e :
        logging.error (e.message)
        sys.stderr.write ("{0}\n".format (e.message))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        

        
    L = len (data)
    p = sf.length_points_all - L
    logging.info ("Wrote: {0:d} samples with {1:d} sample padding.".format (L, p))
    if n != sf.length_points_all :
            logging.warn ("Only wrote {0} samples.".format (n))    
#
#   Write a PASSCAL SEGY file
#
def write_psgy (data, fd, sf) :
    if len (data) > MAX_32 :
        logging.warn ("Warning: Data trace too long, %d samples, truncating to %d" % (len (data), MAX_32))
        sf.set_length_points (MAX_32)
    else :
        sf.set_length_points (sf.length_points_all)
        
    logging.info ("New " * 10)
    logging.info ("Opening: %s" % fd.name)
    
    sf.set_data (data[:MAXSAMPLES])
    sf.set_trace_type (CURRENT_TRACE_TYPE, CURRENT_TRACE_BYTEORDER)
    sf.set_pas ()
    try :
        sf.set_trace_header ();
    except SEGYFactory.SEGYError as e :
        logging.error (e.message)
        sys.stderr.write ("{0}\n".format (e.message))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        

        
    try :
        n, nparray = sf.set_data_array ()
    except Exception as e :
        logging.error (e.message)
        sys.stderr.write ("{0}\n".format (e.message))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        
      
    
    try :
        sf.write_trace_header (fd); 
        sf.write_data_array (fd, nparray)
    except SEGYFactory.SEGYError as e :
        logging.error (e.message)
        sys.stderr.write ("{0}\n".format (e.message))
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stderr)        

        
    L = len (data)
    p = sf.length_points_all - L
    logging.info ("Wrote: {0:d} samples with {1:d} sample padding.".format (L, p))
    if n != sf.length_points_all :
            logging.warn ("Only wrote {0} samples.".format (n))    
###
###
###

def get_das_lines (das, Das_t, start, stop, chan, sr_array) :
    '''   Get lines from a das (rows/keys) table that cover start stop times and channel   '''
    def last_das_start (tmp_row) :
        return SEGYFactory.fepoch (tmp_row['time/epoch_l'], tmp_row['time/micro_seconds_i'])
    
    def last_das_chan (tmp_row) :
        return tmp_row['channel_number_i']
        
    rows = {}
    used_sr = None
    for r in Das_t.rows :
        das_start = SEGYFactory.fepoch (r['time/epoch_l'], r['time/micro_seconds_i'])
        das_stop = das_start + (r['sample_count_i'] / (float (r['sample_rate_i']) / r['sample_rate_multiplier_i']))
        das_chan = r['channel_number_i']
        sample_rate = r['sample_rate_i'] / r['sample_rate_multiplier_i']
        #   Filter on sample rate
        if sr_array == None :
            sr_array = sample_rate
        else :
            if sr_array != sample_rate :
                continue
        #   Filter on channel
        if chan != None :
            if chan != das_chan : continue
            
        #   Check for duplicate data entered in ph5 file
        #   XXX   Should log duplicate data   XXX
        if start >= das_start and start <= das_stop :
            if not rows.has_key (das_chan) :
                rows[das_chan] = []
            try :
                if len (rows[das_chan]) == 0 :
                    rows[das_chan].append (r)
                    used_sr = sample_rate
                elif (last_das_start (rows[das_chan][-1]) != das_start) or (last_das_chan(rows[das_chan][-1]) != das_chan) :
                    rows[das_chan].append (r)
                    used_sr = sample_rate
                else :
                    logging.warn ("Warning: Ignoring extra data trace in PH5 file, DAS: {0}.".format (das))
            except :
                pass
                
            continue
        
        if stop <= das_stop and stop >= das_start :
            if not rows.has_key (das_chan) :
                rows[das_chan] = []
            try :
                if len (rows) == 0 :
                    rows[das_chan].append (r)
                    used_sr = sample_rate
                elif last_das_start (rows[das_chan][-1]) != das_start :
                    rows[das_chan].append (r)
                    used_sr = sample_rate
            except :
                pass
                        
    return rows_keys (rows, Das_t.keys), used_sr

def read_das_groups () :
    '''   Get das groups   '''
    global EX, DASSN
    
    #   Get references for all das groups keyed on das
    dass = EX.ph5_g_receivers.alldas_g ()
    DASSN = [d[6:] for d in dass.keys ()]
    
    return dass

def get_offset_distance_for_shots (Offset_t, Shot_t, stations) :
    #
    keyed_station = {}
    keyed_event = {}
    ks = {}  
    i = 0
    stations = map (int, stations); stations = map (str, stations)
    for o in Offset_t.rows :
        sta = str (int (o['receiver_id_s']))
        #print sta, stations
        if sta not in stations :
            #print "continuing..."
            continue
        
        shot = str (int (o['event_id_s']))
        #
        #i += 1; print i, sta
        keyed_station[sta] = o
        ks[shot] = copy.deepcopy (keyed_station)  
        
    for event_t in Shot_t.rows :
        shot = str (int (event_t['id_s']))
        if ks.has_key (shot) :
            keyed_event[shot] = copy.deepcopy (ks[shot])
            
    del ks
    
    return keyed_event

def get_array_t (Array_t, station) :
    for array_t in Array_t.rows :
        if station == array_t['id_s'] :
            return array_t
        
    return None

def sort_by_offset (kbs) :
    shot_offset = {}
    shots = kbs.keys ()
    for s in shots :
        o = kbs[s][3]
        shot_offset[o['offset/value_d']] = s
        
    offsets = shot_offset.keys ()
    offsets.sort ()
    
    ret = []
    for o in offsets :
        ret.append (shot_offset[o])
        
    return ret

#
#
#
def calc_red_vel_secs (offset_t) :
    global RED_VEL
    
    if RED_VEL <= 0 :
        return 0.
    
    if offset_t == None :
        logging.warn ("Warning: No geometry for station. Reduction velocity not applied.")
        return 0.
     
    if offset_t['offset/units_s'] != 'm' :
        logging.warn ("Warning: Units for offset not in meters! No reduction velocity applied.")
        return 0.
    
    #   m / m/s = seconds
    try :
        secs = abs (offset_t['offset/value_d']) / (RED_VEL * 1000.)
        logging.info ("Applying a reduction velocity of {0:5.3f} seconds (Shot: {1}, Receiver: {2})".format (secs, offset_t['event_id_s'], offset_t['receiver_id_s']))
        #print secs
        return secs
    except Exception, e :
        logging.warn ("{0:s}\n".format (e))
        return 0.
    
def get_chans_in_array (Array_t) :
    akey = {}
    ret = ''
    for r in Array_t.rows :
        if r['channel_number_i'] :
            akey[r['channel_number_i']] = True
        if r.has_key ('seed_orientation_code_s') and not akey.has_key (r['channel_number_i']) :
            ret = ret + r['seed_orientation_code_s']
        
    if ret != '' : return ret    
    ckeys = akey.keys (); ckeys.sort ()
    for c in ckeys :
        ret = ret + CHAN_MAP[c]
        
    return ret

def process_station (station, array=None, sr_array=None) :
    global OUTPATH, SHOTRANGE, PH5
    ###
    #length = 240.
    #chan = 1
    #n = 0
    #m = 0
    ###
    experiment_t = EXPERIMENT_T.rows[0]
    try :
        nickname = experiment_t['nickname_s']
    except :
        if PH5[-3:] == 'ph5' :
            nickname = PH5[:-4]
        else :
            nickname = PH5
        
    station = str (int (station))
    #base = "{0}_{1}".format (nickname, station)
    arrays = ARRAY_T.keys ()
    #   Das_t and other stuff keyed on shot ID
    keyed_by_shot = {}
    #   Order of shots
    shot_order = []
    if array :
        Array_t = ARRAY_T[array]
        array_t = get_array_t (Array_t, station)
    else :
        for array in arrays :
            #   Find which array this station is in
            Array_t = ARRAY_T[array]
            array_t = get_array_t (Array_t, station)
            if array_t != None : break
        
    if array_t == None :
        logging.error ("Error: No data for station {0:s}.\n".format (station))
        return
    else :
        logging.info ("Extracting receiver at station {0:s}.".format (station))
        logging.info ("DAS: {0}".format (array_t['das/serial_number_s']))
        logging.info ("Lat: {0} Lon: {1} Elev: {2}".format (array_t['location/Y/value_d'],
                                                            array_t['location/X/value_d'],
                                                            array_t['location/Z/value_d']))
    

    #
    #   XXX   We need to move these to the channels that are in the PH5 file   XXX
    #
    if CHANNEL :
        chan_name = CHAN_MAP[CHANNEL]
    else :
        chan_name = get_chans_in_array (Array_t)
        
    base = "{0}_{1}_{2}_{3}".format (nickname, array[-3:], station, chan_name)
            
    das = array_t['das/serial_number_s']
    das = "Das_g_{0}".format (das)
    deploy = array_t['deploy_time/epoch_l']
    pickup = array_t['pickup_time/epoch_l']
    
    
    if not DASS.has_key (das) :
        logging.error ("Error: No data for station {0:s}, das {1}.\n".format (station, das))
        return
    
    EX.ph5_g_receivers.setcurrent (DASS[das])
    das_r, das_keys = EX.ph5_g_receivers.read_das ()
    Das_t = rows_keys (das_r, das_keys)
    
    event_table_names = EVENT_T.keys ()
    for event_table_name in event_table_names :
        for event_t in EVENT_T[event_table_name].rows :
            ###   ZZZ   ###
            if EVT_LIST != None and not int (event_t['id_s']) in EVT_LIST :
                continue
            #   Each event has start time to cut
            shot = str (int (event_t['id_s']))
            
            if int (shot) >= SHOTRANGE[0] and int (shot) <= SHOTRANGE[1] :
                #print shot, SHOTRANGE
                #   Find offset from this station to shot
                try :
                    #print KEYED_SHOT[shot][station]
                    #offset_t = KEYED_SHOT[shot][station]
                    #offset_t = EX.ph5_g_sorts.read_offset_fast (shot, station)
                    offset_t = OFFSET_T[station][shot]
                except :
                    #print shot, station
                    offset_t = None
                    continue
                
                ###   Need to add in any offset time here!
                start_time = SEGYFactory.fepoch (event_t['time/epoch_l'], event_t['time/micro_seconds_i'])
                #print "Extracting data for shot {0} at station {1}".format (shot, station)
                if DEPLOY_PICKUP == True and not ((start_time >= deploy and start_time <= pickup)) :
                    #print '***'
                    logging.info ("DAS {0} not deployed at station {1} on {2}.".format (das, array_t['id_s'], time.ctime (start_time)))
                    logging.info ("Deployed: {0} Picked up: {1}.".format (time.ctime (deploy), time.ctime (pickup)))
                    continue
                
                #start_time += offset_time
                stop_time = start_time + LENGTH
                if IGNORE_CHANNEL :
                    das_t, tmp_sr = get_das_lines (das, Das_t, start_time, stop_time, None, sr_array)
                else :
                    das_t, tmp_sr = get_das_lines (das, Das_t, start_time, stop_time, CHANNEL, sr_array)
                 
                if sr_array == None : sr_array = tmp_sr  
                if not das_t.rows : continue
                rvs = calc_red_vel_secs (offset_t)
                time_t = get_time (TIME_T, das, start_time + rvs)
                shot_order.append (shot)
                keyed_by_shot[shot] = [ das_t, start_time + rvs, stop_time + rvs, offset_t, time_t, array_t, event_t ]
    
    ntraces = len (shot_order) * len (chan_name)
    if SORT_OFFSETS == True :
        shot_order = sort_by_offset (keyed_by_shot)
        
    logging.info ("Found data for {0:d} traces.\n".format (ntraces))
    sf = SEGYFactory.Ssegy (None, None, utm = UTM)
    sf.set_ext_header_type (EXT)
    sf.set_break_standard (BREAK_STANDARD)
    i = 0
    fh = None
    for s in shot_order :
        das_t, start_time, stop_time, offset_t, time_t, array_t, event_t = keyed_by_shot[s]
        #print das_t.rows
        chans = das_t.rows.keys ()
        chans.sort ()
        for n in chans :
            i += 1
            r = das_t.rows[n]
            if not r : continue
            #print r
            logging.info ("{0}".format (i))
            logging.info ("Extracting: Event ID %s" % event_t['id_s'])
            logging.info ("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
            logging.info ("Shot: {0:s}".format (s))
            logging.info ("Chan: {2} Start: {0:s}, Stop: {1:s}.".format (time.ctime (start_time), 
                                                                         time.ctime (stop_time), 
                                                                         r[0]['channel_number_i']))
            
            logging.info ("Lat: %f Lon: %f Elev: %f %s" % (event_t['location/Y/value_d'],
                                                           event_t['location/X/value_d'],
                                                           event_t['location/Z/value_d'],
                                                           event_t['location/Z/units_s'].strip ()))
                                                            
            sf.set_cut_start_epoch (start_time)
            sf.set_array_t (array_t)
            sf.set_offset_t (offset_t)
            sf.set_event_t (event_t)
            sf.set_das_t (r[0])
            sf.set_line_sequence (i)
            
            data = cut (start_time, stop_time , r, time_t, RESPONSE_T, RECEIVER_T, sf)
            if not data :
                logging.warn ("Warning: No data found for shot {0:s}.\n".format (s))
            
            if FORMAT == 'PSGY' :
                outfilename = "{1:s}/{0:s}.0001.psgy".format (base, OUTPATH)
                #outfilename = os.path.join (OUTPATH, outfilename)
                j = 1
                while os.path.exists (outfilename) :
                    j += 1
                    tmp = outfilename[:-9]
                    outfilename = "%s%04d.psgy" % (tmp, j) 
                    
                logging.info ("Opening: {0:s}\n".format (outfilename))
                fh = open (outfilename, "w+")
                write_psgy (data, fh, sf)
                fh.close ()
            elif not fh :
                outfilename = "{1:s}/{0:s}_0001.SGY".format (base, OUTPATH)
                #outfilename = os.path.join (OUTPATH, outfilename)
                j = 1
                while os.path.exists (outfilename) :
                    j += 1
                    tmp = outfilename[:-8]
                    outfilename = "%s%04d.SGY" % (tmp, j) 
                    
                logging.info ("Opening: {0:s}\n".format (outfilename))
                fh = open (outfilename, 'w+')
                write_segy_hdr (data, fh, sf, ntraces)
            else :
                write_segy (data, fh, sf)
                os.chmod(outfilename, 0777)
    if fh : fh.close ()

       
        
if __name__ == "__main__" :
    #   Get program arguments
    get_args ()
    logging.info ("%s: %s" % (PROG_VERSION, sys.argv))
    #   Initialize ph5 file
    initialize_ph5 ()
    EXPERIMENT_T = read_experiment_table ()
    
    try :
        experiment_t = EXPERIMENT_T.rows[0]
        logging.info ("Experiment: %s" % experiment_t['longname_s'].strip ())
        logging.info ("Summary: %s" % experiment_t['summary_paragraph_s'].strip ())
    except :
        logging.error ("Error: Critical information missing from /Experiment_g/Experiment_t. Exiting.")
        sys.exit (-1)
    #   Read event table (shots)process_event
    #print "Read event table...",; sys.stdout.flush ()
    read_event_table ()
    #print "Done"
    
    #   Read offsets
    #print "Read offset table...",; sys.stdout.flush ()
    ###   Done in kernel space   ###
    read_offset_table ()
    #print "Done"
    
    #   Read sort table (Start time, Stop time, and Array)
    #print "Read sort table...",; sys.stdout.flush ()
    read_sort_table ()
    #print "Done"
        
    #   Read sort arrays
    read_sort_arrays ()
    read_response_table ()
    RECEIVER_T = read_receiver_table ()     
    TIME_T = read_time_table ()
    
    #print "Read DAS groups...",; sys.stdout.flush ()
    DASS = read_das_groups ()
    #print "Done"
    
    #print "Get offset distances for shots...",; sys.stdout.flush ()
    #KEYED_SHOT = get_offset_distance_for_shots (OFFSET_T, EVENT_T, STATIONS)
    #print "Done\nProcessing...",
    for station in STATIONS :
        #print "Processing station {0}".format (station)
        process_station (station)
        #break
        
    #print "Done"
    #   Close ph5 file
    EX.ph5close ()
    logging.info ("Done.\n")
    logging.shutdown ()
    sys.stderr.write ("Done\n")
