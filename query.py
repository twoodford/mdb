#!/usr/bin/env python3.8
# query.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
# Command line query tool for the music database.
from __future__ import print_function
from datetime import datetime, timedelta,timezone
import operator
import sqlite3

import mdb.circstats
import mdb.dtutil
import mdb.seed
import mdb.util

def dbg_list_times(sname, key, sdb, weathdb):
    #print("Plays of "+sname)
    cur = sdb.cursor()
    wcur = weathdb.cursor()
    cur.execute("SELECT unixlocaltime, utcoffs, pkey FROM plays WHERE song=?", (key,))
    for tm in cur.fetchall():
        pkey = tm[2]
        timez = timezone(timedelta(seconds=tm[1]))
        #print(str(datetime.fromtimestamp(tm[0]-tm[1], tz=timez)))
        wcur = weathdb.cursor()
        wcur.execute("SELECT bw.temp_c, nws.skycondition, nws.cloudcover FROM play_weather_match AS pwm JOIN nws_weather AS nws ON pwm.nws_time=nws.time LEFT OUTER JOIN basic_weather AS bw ON pwm.basic_time=bw.time WHERE pwm.pkey=?", (pkey,))
        weath_matches = wcur.fetchall()
        if len(weath_matches) > 0:
            weath_str = f"{weath_matches[0][0]}˚C {weath_matches[0][2]}% clouds {weath_matches[0][1]}"
        else: weath_str = ""
        try:
            #print("{:<45}{:<20}".format(play[0], str(tm)))
            print(f"{datetime.fromtimestamp(tm[0]-tm[1], tz=timez)} {weath_str}")
        except UnicodeEncodeError:
            print("warn: UnicodeEncodeError")

def dbg_list_all_plays_w_weather(sdb, weathdb):
    cur = sdb.cursor()
    cur.execute("SELECT name, plays.unixlocaltime, plays.utcoffs, pkey FROM plays JOIN songs ON plays.song=songs.key ORDER BY plays.unixlocaltime ASC")
    for play in cur.fetchall():
        pkey = play[3]
        timez = timezone(timedelta(seconds=play[2]))
        tm = datetime.fromtimestamp(play[1]-play[2], tz=timez)
        wcur = weathdb.cursor()
        wcur.execute("SELECT bw.temp_c, nws.skycondition, nws.cloudcover FROM play_weather_match AS pwm JOIN nws_weather AS nws ON pwm.nws_time=nws.time LEFT OUTER JOIN basic_weather AS bw ON pwm.basic_time=bw.time WHERE pwm.pkey=?", (pkey,))
        weath_matches = wcur.fetchall()
        if len(weath_matches) > 0:
            weath_str = f"{weath_matches[0][0]}˚C {weath_matches[0][2]}% clouds {weath_matches[0][1]}"
        else: weath_str = ""
        try:
            #print("{:<45}{:<20}".format(play[0], str(tm)))
            print(f"{play[0]:<45}{tm:<20} {weath_str}")
        except UnicodeEncodeError:
            print("warn: UnicodeEncodeError")

def dbg_list_all_plays(sdb, weathdb):
    cur = sdb.cursor()
    cur.execute("SELECT name, plays.unixlocaltime, plays.utcoffs, pkey FROM plays JOIN songs ON plays.song=songs.key ORDER BY plays.unixlocaltime ASC")
    for play in cur.fetchall():
        pkey = play[3]
        timez = timezone(timedelta(seconds=play[2]))
        tm = datetime.fromtimestamp(play[1]-play[2], tz=timez)
        try:
            print(f"{play[0]:<45}{tm}")
        except UnicodeEncodeError:
            print("warn: UnicodeEncodeError")




def dbg_get_timedens(sdb):
    times_dict = mdb.dtutil.times_dict(sdb)
    pdens = mdb.seed.play_times_density(times_dict)
    sorted_pdens = sorted(pdens.items(), key=operator.itemgetter(1), reverse=True)
    for pv in sorted_pdens:
        print(mdb.util.key_to_string(pv[0], sdb), ": ", pv[1])

def run(argv):
    sdb = sqlite3.connect("data/music.sqlite3")
    weathdb = sqlite3.connect("data/weather.sqlite3")
    cur = sdb.cursor()
    if len(argv) > 2:
        sname = argv[2]
    else:
        sname = "Strong"
    cur.execute("SELECT key FROM songs WHERE name=?", (sname,))
    key = cur.fetchone()[0]
    if len(argv) > 1:
        if argv[1] == "listplays":
            dbg_list_times(sname, key, sdb, weathdb)
        elif argv[1]=="listallplays":
            dbg_list_all_plays(sdb, weathdb)
        elif argv[1]=="pdens":
            dbg_get_timedens(sdb)
        else:
            if argv[1] == "avgtime":
                pre = mdb.circstats.preproc_timeofday
                post = mdb.circstats.postproc_timeofday
            elif argv[1]=="avgday":
                pre = mdb.circstats.preproc_dayofyear
                post = mdb.circstats.postproc_dayofyear
            cur.execute("SELECT unixlocaltime, utcoffs FROM plays WHERE song=?", (key,))
            recs = cur.fetchall()
            plays = [datetime.fromtimestamp(tm[0]-tm[1], tz=timezone(timedelta(seconds=tm[1]))) for tm in recs]
            avg = mdb.circstats.stat_avg(pre, post)(plays)
            sdev = mdb.circstats.stat_stddev(pre, post)(plays)
            print("Average time played: " + str(avg))
            print("Standard Deviation: " + str(sdev))
    else:
        print("Usage: query.py (avgtime|avgday|listplays|listallplays) [Song name]")

if __name__ == "__main__":
    import sys
    run(sys.argv)

