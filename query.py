#!/usr/bin/env python3.6
# query.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
# Command line query tool for the music database.
from __future__ import print_function
from datetime import datetime, timedelta,timezone
import sqlite3

import mdb.circstats
import mdb.util

def dbg_list_times(sname, key, sdb):
    #print("Plays of "+sname)
    cur = sdb.cursor()
    cur.execute("SELECT unixlocaltime, utcoffs FROM plays WHERE song=?", (key,))
    for tm in cur.fetchall():
        timez = timezone(timedelta(seconds=tm[1]))
        print(str(datetime.fromtimestamp(tm[0]-tm[1], tz=timez)))

def dbg_list_all_plays(sdb):
    cur = sdb.cursor()
    cur.execute("SELECT name, plays.unixlocaltime, plays.utcoffs FROM plays JOIN songs ON plays.song=songs.key ORDER BY plays.unixlocaltime ASC")
    for play in cur.fetchall():
        timez = timezone(timedelta(seconds=play[2]))
        tm = datetime.fromtimestamp(play[1]-play[2], tz=timez)
        try:
            print("{:<45}{:<20}".format(play[0], str(tm)))
        except UnicodeEncodeError:
            print("warn: UnicodeEncodeError")

def run(argv):
    sdb = sqlite3.connect("data/music.sqlite3")
    cur = sdb.cursor()
    if len(argv) > 2:
        sname = argv[2]
    else:
        sname = "Strong"
    cur.execute("SELECT key FROM songs WHERE name=?", (sname,))
    key = cur.fetchone()[0]
    if len(argv) > 1:
        if argv[1] == "listplays":
            dbg_list_times(sname, key, sdb)
        elif argv[1]=="listallplays":
            dbg_list_all_plays(sdb)
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

