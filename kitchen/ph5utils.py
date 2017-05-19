'''
A collection of common methods for ph5tomsAPI.py, ph5tostationxml.py and
ph5toexml.py.
'''


import fnmatch
from datetime import datetime
from obspy.geodetics import locations2degrees
from TimeDOY import epoch2passcal
from TimeDOY import passcal2epoch
import time


def does_pattern_exists(patterns_list, value):
    """
    Checks a list of patterns against a value. 
    :param: patterns_list : A list of regular glob expression strings
    :type: str
    :returns: Returns True if any of the patterns match the value, False otherwise.
    :type: boolean
    """
    for pattern in patterns_list:
        if fnmatch.fnmatch(str(value), str(pattern)):
            return True
    return False


def is_radial_intersection(point_lat, point_lon, 
                           minradius, maxradius, 
                           latitude, longitude):
    """
    Checks if there is a radial intersection between a point radius boundary
    and a latitude/longitude point.
    :param: point_lat : the latitude of the point radius boundary :type: float
    :param: point_lon : the longitude of the point radius boundary :type: float
    :param: minradius : the minimum radius boundary :type: float
    :param: maxradius : the maximum radius boundary :type: float
    :param: latitude : the latitude of the point to check :type: float
    :param: longitude : the longitude of the point to check :type: float
    """
    if minradius or maxradius or point_lat or point_lon:
        # min radius default to 0.0
        if not minradius:
            minradius = 0.0
        # make max radius default to min radius when not defined
        if not maxradius:
            maxradius = minradius
        # latitude and longitude default to 0.0 when not defined
        if not point_lat:
            point_lat = 0.0
        if not point_lon:
            point_lon = 0.0
        dist = locations2degrees(latitude, longitude, point_lat, point_lon)
        if dist < minradius:
            return False
        elif dist > maxradius:
            return False
        else:
            return True
    else:
        return True


def is_rect_intersection(minlat, maxlat, minlon, maxlon, latitude, longitude):
    """
    Checks if there is a radial intersection between a point radius boundary
    and a latitude/longitude point.
    :param: minlat : the minimum rectangular latitude :type: float
    :param: maxlat : the maximum rectangular latitude :type: float
    :param: minlon : the minimum rectangular longitude :type: float
    :param: maxlon : the maximum rectangular longitude :type: float
    :param: latitude : the latitude of the point to check :type: float
    :param: longitude : the longitude of the point to check :type: float
    """
    if minlat and float(
            minlat) > float(latitude):
        return False
    elif minlon and float(
            minlon) > float(longitude):
        return False
    elif maxlat and float(
            maxlat) < float(latitude):
        return False
    elif maxlon and float(
            maxlon) < float(longitude):
        return False
    else:
        return True


def datestring_to_datetime(date_str):
    """
    Converts a FDSN or PASSCAL date string to a datetime.datetime object
    :param: date_str
    :type: str
    :returns: datetime equivalent to string
    :type: datetime
    """
    if isinstance(date_str, (str, unicode)):
        fmts = ("%Y:%j:%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")
        for fmt in fmts:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.year < 1900:
                    err_msg = 'Date %s is out of range. Year must be year >= 1900.' % date_str
                    raise ValueError(err_msg)
                return dt
            except ValueError:
                pass
        err_msg = 'Unsupported date format. %s' % date_str
        raise ValueError(err_msg)
    elif isinstance(date_str, datetime):
        return date_str # already a date
    else:
        raise ValueError("Got {0} expected str or unicode.".format(type(date_str)))


def fdsntime_to_epoch(fdsn_time):
    """
    Converts a FDSN date string to epoch seconds
    :param: fdsn_time
    :type: str
    :returns: epoch seconds
    :type: float
    """
    pattern = "%Y-%m-%dT%H:%M:%S.%f"
    epoch = float(time.mktime(time.strptime(fdsn_time, pattern)))
    return epoch


def doy_breakup(start_fepoch):
    """
    Given a start time epoch returns a next days equivalent epoch time and the
    difference in seconds between the start and stop epoch times.
    :param: start_fepoch
    :type: float
    :returns: stop_fepoch : next days stop epoch :type: float
              seconds: difference in seconds between the start and end epoch times :type: float
    """
    passcal_start = epoch2passcal(start_fepoch)
    start_passcal_list = passcal_start.split(":")
    start_doy = start_passcal_list[1]
    year = start_passcal_list[0]
    next_doy = int(start_doy) + 1
    if next_doy > 365:
        next_doy = 1
        year = int(year) + 1

    next_passcal_date = str(year) + ":" + str(next_doy) + ":00:00:00.000"
    stop_fepoch = passcal2epoch(next_passcal_date)

    seconds = stop_fepoch - start_fepoch
    return stop_fepoch, seconds