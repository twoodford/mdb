# seed.py (mdb.seed)
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
# Interpret past play data to determine which song to start with
from __future__ import division
from datetime import datetime, timedelta
from math import log
import operator

import mdb.circstats
import mdb.dtutil
import mdb.util

def play_density(sdb):
    """ Returns a dictionary with song keys as keys and the values as a 
        representation of how frequently a song has been played at this 
        particular time and day of week.
    """
    # Ideally, we should shift all song play data to local time.  Until
    # that happens, we need to compensate for the fact that everything's in UTC
    now = datetime.utcnow().time()
    current_dow = datetime.now().weekday()
    # Prepare the stats
    tdict = mdb.dtutil.times_dict(sdb)
    pre = mdb.circstats.preproc_timeofday
    post = mdb.circstats.postproc_timeofday
    avgs = mdb.circstats.stat_to_dict(tdict, mdb.circstats.stat_avg(pre, post))
    sdevs = mdb.circstats.stat_to_dict(tdict, \
            mdb.circstats.stat_stddev(pre, mdb.circstats.postproc_timedelta))
    return {key: mdb.dtutil.day_of_week_density(tdict[key])[current_dow] * \
            mdb.dtutil.time_local_density(now, tdict[key])
            for key in tdict.keys()}

def last_play_distance(sdb):
    """ Find the latest play time for each song. Returns dictionary of 
        song ID as key and latest play time as value. """
    tdict = mdb.dtutil.times_dict(sdb)
    now = datetime.utcnow()
    return {sid: now - max(tdict[sid]) for sid in tdict.keys()}

def play_dens_adjust_lastplay(playdens, lastplay, sdb, weight=0.005):
    """ Adjust play density to favor songs that haven't been played 
        recently.  The adjustment reaches its maximum at 10 months 
        since last play, which should help avoid excessively boosting 
        songs I don't like much anymore."""
    year_seconds = 60 * 60 * 24 * 30
    return {sid: playdens[sid] + \
            weight * log(max(min(lastplay[sid].total_seconds() / year_seconds, 5), 0.00001))
            for sid in playdens.keys()}

def get_start_points(sdb):
    "Get possible start points, ordered by how good of an idea they are"
    dens = play_density(sdb)
    pdistance = last_play_distance(sdb)
    dens = play_dens_adjust_lastplay(dens, pdistance, sdb)
    # Sort by proximity to current day of week and time
    start_point = list(dens.keys()) # Could try to narrow some stuff down here
    start_point.sort(key=lambda x: dens[x], reverse=True)
    #for point in start_point[:10]:
    #    print(mdb.util.key_to_string(point, sdb)+": "+str(dens[point]))
    return start_point


def _collect_songs(playids, mdbdb):
    cur = mdbdb.cursor()
    songs = {}
    for playid in playids:
        cur.execute("SELECT song FROM plays WHERE pkey=?", (playid[0],))
        try:
            (songid,) = cur.fetchone()
        except TypeError: # Nothing here
            #print("Warn: could not find play")
            continue
        try:
            songs[songid] += 1
        except KeyError:
            songs[songid] = 1
    cur.close()
    return sorted(songs.items(), key=operator.itemgetter(1), reverse=True)

def get_weather_dens(weather_db, sdb):
    cur = weather_db.cursor()

    # Get current conditions
    mintime = (datetime.now() - timedelta(days=2)).timestamp()
    cur.execute("SELECT * FROM basic_weather WHERE time > ? ORDER BY time DESC", (mintime,))
    (temp,pressure,precip) = cur.fetchone()[1:]
    cur.execute("SELECT * FROM nws_weather WHERE time > ? ORDER BY time DESC", (mintime,))
    (sky,cloudcover,weathertype) = cur.fetchone()[1:4]
    
    # Stage 1: Matching plays for ballpark temperature, I think.  I'm having trouble understanding my own SQL.
    cur.execute("SELECT pkey FROM play_weather_match AS pwm JOIN nws_weather AS nws ON pwm.nws_time=nws.time LEFT OUTER JOIN basic_weather AS bw ON pwm.basic_time=bw.time WHERE temp_c > ? AND temp_c < ?", (temp-5, temp+5))
    fun = cur.fetchall()

    # Stage 2: Look for plays that occurred during similar weather
    if weathertype != "?":
        cur.execute("SELECT pkey FROM play_weather_match AS pwm JOIN nws_weather AS nws ON pwm.nws_time=nws.time LEFT OUTER JOIN basic_weather AS bw ON pwm.basic_time=bw.time WHERE nws.weathertype=?", (weathertype,))
        morefun = cur.fetchall()
    else:
        morefun = []

    # Combine them
    seed = _collect_songs(morefun+fun, sdb)
    # I was doing this instead in the script.  May call for more investigation.
    #seed = collect_songs(morefun, mdbdb) 

    return seed
