# dtutil.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
from __future__ import print_function
import datetime
import math
import sys

def time_to_seconds(tm):
    return ((tm.hour*60)+tm.minute)*60+tm.second

def time_difference(tm1, tm2):
    tm1s = time_to_seconds(tm1)
    tm2s = time_to_seconds(tm2)
    diff1 = abs(tm1s-tm2s)
    if tm1s < tm2s:
        tm1s += 24*60*60
    else:
        tm2s += 24*60*60
    diff2 = abs(tm1s - tm2s)
    diff = min((diff1, diff2))
    return datetime.timedelta(seconds=diff)

def time_local_density(tmc, other_tm):
    if len(other_tm) == 0:
        return 0
    else:
        def _td(otm):
            td = time_difference(tmc, otm).total_seconds()
            if td != 0:
                return 1/td
            else:
                return sys.maxsize
        return sum([_td(otm) for otm in other_tm])/(len(other_tm))**0.8

def day_of_week_density(tlist):
    dow = [x.weekday() for x in tlist]
    ret = [0, 0, 0, 0, 0, 0, 0]
    for i in range(0, len(ret)):
        ret[i] = 0.01
    for item in dow:
        ret[item] += 1
    return [x/len(dow) for x in ret]

def times_dict(sdb):
    """Creates a dictionary with keys being the SID of a song, and values being
       datetime objects representing play records."""
    cur = sdb.cursor()
    cur.execute("SELECT song, datetime FROM plays")
    ret = {}
    for play in cur.fetchall(): 
        if not play[0] in ret: ret[play[0]] = []
        ret[play[0]].append(datetime.datetime.utcfromtimestamp(play[1]))
    return ret

def _test():
    print(time_difference(datetime.time(hour=2), datetime.time(hour=3)))
    print(time_difference(datetime.time(hour=23), datetime.time(hour=3)))

if __name__=="__main__": _test()
