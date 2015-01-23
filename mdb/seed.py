# seed.py (mdb.seed)
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
# Interpret past play data to determine which song to start with
from __future__ import division
from datetime import datetime

import mdb.circstats
import mdb.dtutil
import mdb.util

def play_density(sdb):
    """ Returns a dictionary with song keys as keys and the values as a representation of how frequently 
        a song has been played at this particular time and day of week.
    """
    # Ideally, we should shift all song play data to local time.  Until that happens, we need to compensate for the 
    # fact that everything's in UTC
    now = datetime.utcnow().time()
    current_dow = datetime.now().weekday()
    # Prepare the stats
    tdict = mdb.dtutil.times_dict(sdb)
    pre = mdb.circstats.preproc_timeofday
    post = mdb.circstats.postproc_timeofday
    avgs = mdb.circstats.stat_to_dict(tdict, mdb.circstats.stat_avg(pre, post))
    sdevs = mdb.circstats.stat_to_dict(tdict, mdb.circstats.stat_stddev(pre, mdb.circstats.postproc_timedelta))
    return {key: mdb.dtutil.day_of_week_density(tdict[key])[current_dow] * mdb.dtutil.time_local_density(now, tdict[key])
            for key in tdict.keys()}

def get_start_points(sdb):
    "Get possible start points, ordered by how good of an idea they are"
    dens = play_density(sdb)
    # Sort by proximity to current day of week and time
    start_point = list(dens.keys()) # Could try to narrow some stuff down here
    start_point.sort(key=lambda x: dens[x], reverse=True)
    for point in start_point[:10]:
        print(mdb.util.key_to_string(point, sdb)+": "+str(dens[point]))
    return start_point
