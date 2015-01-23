# circstats.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
#
# Collect statistics about when a certain song tends to be played
from __future__ import print_function
from __future__ import division
from datetime import datetime, time, date, timedelta
from math import sqrt, sin, cos, atan2, pi, log
import sqlite3

def statfunc(sfunc):
    """Decorator for statistics functions - makes the initial function call
       output a function suitable for use in stat_to_dict, that will convert
       inputs into numbers, then back again after the statistic is calculated.
    """
    def retfunc(prefunc, postfunc):
        return lambda x: postfunc(sfunc([prefunc(num) for num in x]))
    return retfunc

TIMEOFDAY_CONVERSION = 86400/2/pi

def preproc_timeofday(dtm):
    """Changes a time object into a number representing the number of seconds
       elapsed at the given time of day, mapped onto a location in radians on a circle"""
    return (((dtm.hour*60)+dtm.minute)*60+dtm.second)/TIMEOFDAY_CONVERSION

def postproc_timeofday(num):
    """Changes the radians representation of time of day back into a time object.
    """
    num = int(num*TIMEOFDAY_CONVERSION)
    return time(num//3600, (num//60)%60, num%60%60)

def postproc_timedelta(num):
    num = int(num*TIMEOFDAY_CONVERSION)
    return timedelta(seconds=num)

DAYOFYEAR_CONVERSION = 365/2/pi

def preproc_dayofyear(dtm):
    """Takes a date object and outputs a measurement in radians representing the 
    day of the year"""
    return (dtm.timetuple().tm_yday)/DAYOFYEAR_CONVERSION

def postproc_dayofyear(num):
    """Takes a radian day of year and converts it to the equivalent day in the 
    year 1 (what else was I supposed to do?)"""
    return date.fromordinal(int(num*DAYOFYEAR_CONVERSION)+1)

def proc_null(x):
    """Utility function to do nothing instead of pre-/post-processing"""
    return x

#### Begin core stats stuff ####

def _avg_pos(dat):
    n = len(dat)
    return (sum(map(sin, dat))/n, sum(map(cos, dat))/n)

@statfunc
def stat_avg(dat):
    x,y = _avg_pos(dat)
    num = atan2(x, y)
    if num<0:
        num += 2*pi
    return num

@statfunc
def stat_stddev(dat):
    x, y = _avg_pos(dat)
    radius = sqrt(x**2 + y**2)
    return sqrt(-2*log(radius))

#### End core stats stuff ####

def stat_to_dict(sdict, avg_method):
    return {key: avg_method(sdict[key]) for key in sdict}

