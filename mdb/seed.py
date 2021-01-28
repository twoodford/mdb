# seed.py (mdb.seed)
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
# Interpret past play data to determine which song to start with
from __future__ import division
from datetime import datetime, timezone, timedelta
import time
from math import log
import operator
import random
import warnings

import mdb.circstats
import mdb.dtutil
import mdb.util

#######################
# Play time densities #
#######################

def play_density(sdb):
    """ Returns a dictionary with song keys as keys and the values as a 
        representation of how frequently a song has been played at this 
        particular time and day of week.
    """
    warnings.warn("Call to deprecated function")
    # Ideally, we should shift all song play data to local time.  Until
    # that happens, we need to compensate for the fact that everything's in UTC
    now = datetime.utcnow().time()
    current_dow = datetime.now().weekday()
    # Prepare the stats
    tdict = mdb.dtutil.times_dict(sdb)
    return {key: mdb.dtutil.day_of_week_density(tdict[key])[current_dow] * \
            mdb.dtutil.time_local_density_smoothed(now, tdict[key])
            for key in tdict.keys()}

def play_times_density(times_dict):
    """ Returns a dictionary with song keys as keys and the values as a 
        representation of how frequently a song has been played at this 
        particular time and day of week.
        times_dict comes from mdb.dtutil.times_dict()
    """
    # Ideally, we should shift all song play data to local time.  Until
    # that happens, we need to compensate for the fact that everything's in UTC
    now = datetime.utcnow().time()
    now = datetime.now().time()
    current_dow = datetime.now().weekday()
    print(now)
    return {key: mdb.dtutil.day_of_week_density(times_dict[key])[current_dow] * \
            mdb.dtutil.time_local_density_smoothed(now, times_dict[key])
            for key in times_dict}

def last_play_distance(times_dict):
    """ Find the latest play time for each song. Returns dictionary of 
        song ID as key and latest play time as value. """
    tdict = times_dict
    now = mdb.dtutil.now()
    return {sid: now - max(tdict[sid]) for sid in tdict}

def play_dens_adjust_lastplay(playdens, lastplay, sdb, limit=1/12, weight=0.005):
    """ Adjust play density to favor songs that haven't been played 
        recently.  The adjustment reaches its maximum at 1 month 
        since last play, which should help avoid excessively boosting 
        songs I don't like much anymore.  Adjust this limit using the limit 
        parameter (unit: years)"""
    year_seconds = 60 * 60 * 24
    return {sid: playdens[sid] + \
            weight * max(log(min(lastplay[sid].total_seconds() / year_seconds, limit)*10000), 0)
            for sid in playdens.keys()}

#################################
#       Weather-related         #
#################################

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
    return songs
    #return sorted(songs.items(), key=operator.itemgetter(1), reverse=True)

def get_weather_dens(weather_db, sdb, weathertype=None, temp=None):
    cur = weather_db.cursor()

    # Get current conditions
    mintime = (datetime.now() - timedelta(days=4)).timestamp()
    print(mintime)
    cur.execute("SELECT * FROM basic_weather WHERE time > ? ORDER BY time DESC", (mintime,))
    (temp,pressure,precip) = cur.fetchone()[1:]
    print(temp,pressure,precip)
    if weathertype is None:
        cur.execute("SELECT * FROM nws_weather WHERE time > ? ORDER BY time DESC", (mintime,))
        (sky,cloudcover,weathertype) = cur.fetchone()[1:4]
        print(sky,cloudcover,weathertype)

    #weathertype="rain"
    
    # Stage 1: Matching plays for ballpark temperature, I think.  I'm having trouble understanding my own SQL.
    cur.execute("SELECT pkey FROM play_weather_match AS pwm JOIN nws_weather AS nws ON pwm.nws_time=nws.time LEFT OUTER JOIN basic_weather AS bw ON pwm.basic_time=bw.time WHERE temp_c > ? AND temp_c < ?", (temp-15, temp+15))
    temp_match = cur.fetchall()
    cur.execute("SELECT pkey FROM play_weather_match WHERE nws_time IS NOT NULL");
    temp_all = cur.fetchall()

    # Stage 2: Look for plays that occurred during similar weather
    if weathertype != "?":
        cur.execute("SELECT pkey FROM play_weather_match AS pwm JOIN nws_weather AS nws ON pwm.nws_time=nws.time LEFT OUTER JOIN basic_weather AS bw ON pwm.basic_time=bw.time WHERE nws.weathertype=?", (weathertype,))
        conditions_match = cur.fetchall()
        cur.execute("SELECT pkey FROM play_weather_match WHERE basic_time IS NOT NULL");
        conditions_all = cur.fetchall()
    else:
        conditions_match = []
        conditions_all = []

    cur.close()
    # Combine them
    match_count = _collect_songs(temp_match+conditions_match, sdb)
    all_count = _collect_songs(temp_all, sdb)
    # I was doing this instead in the script.  May call for more investigation.
    #seed = collect_songs(morefun, mdbdb) 

    #return _keywise_divide(match_count, all_count)
    return match_count

###########################################
#  Song quality estimation                #
###########################################

def num_plays_adjustment(times_dict, weight=0.7):
    return {key: len(times_dict[key])**weight for key in times_dict}

def rating_adjustment(sdb, weight=1):
    """Song weight adjustment based on manual rating.  Songs with 2.5 stars will 
    remain the same (returns 1).  Other songs will be adjusted at (stars-2.5)*weight"""
    cur = sdb.cursor()
    cur.execute("SELECT key, rating FROM songs")
    dat = cur.fetchall()
    cur.close()
    return {row[0]: (row[1]-50)/20*weight if row[1] is not None else 1 for row in dat}


###########################################
# Misc utility functions                  #
###########################################

def keywise_mult(dict_a, dict_b):
    """Multiple two dictionaries together.  Assumes dict_b has all of the keys that 
    dict_a has.  Any additional keys in dict_b will be dropped"""
    return {key: dict_a[key]*dict_b[key] for key in dict_a}

def _keywise_divide(a, b):
    return {key: (1+a[key])/(1+b[key]) for key in a}

def get_start_points(sdb):
    "Get possible start points, ordered based on time-appropriateness"
    dens = play_density(sdb)
    tdict = mdb.dtutil.times_dict(sdb)
    pdistance = last_play_distance(tdict)
    dens = play_dens_adjust_lastplay(dens, pdistance, sdb)
    # Sort by proximity to current day of week and time
    start_point = list(dens.keys()) # Could try to narrow some stuff down here
    start_point.sort(key=lambda x: dens[x], reverse=True)
    for point in start_point[:10]:
        print(mdb.util.key_to_string(point, sdb)+": "+str(dens[point]))
    return start_point

def randomise_seeds(sdict, sigma=0.1):
    rnd = random.Random()
    for key in sdict:
        sdict[key] *= rnd.normalvariate(1, sigma)
