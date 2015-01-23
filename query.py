#!/usr/bin/which python3.4
# query.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
# Command line query tool for the music database.
from __future__ import print_function
from datetime import datetime, timedelta
import sqlite3

import mdb.circstats
import mdb.util

def dbg_list_times(sname, key, sdb):
    print("Plays of "+sname)
    cur = sdb.cursor()
    cur.execute("SELECT datetime FROM plays WHERE song=?", (key,))
    for tm in cur.fetchall():
        print(str(datetime.utcfromtimestamp(tm[0])))

def dbg_list_all_plays(sdb):
    cur = sdb.cursor()
    cur.execute("SELECT name, datetime FROM plays JOIN songs ON plays.song=songs.key")
    for play in cur.fetchall():
        try:
            print(str(play[0])+": "+str(play[1]))
        except UnicodeEncodeError:
            pass

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
            cur.execute("SELECT datetime FROM plays WHERE song=?", (key,))
            recs = cur.fetchall()
            plays = [datetime.utcfromtimestamp(tm[0]) for tm in recs]
            avg = mdb.circstats.stat_avg(pre, post)(plays)
            sdev = mdb.circstats.stat_stddev(pre, post)(plays)
            print("Average time played: " + str(avg))
            print("Standard Deviation: " + str(sdev))
    else:
        print("Usage: query.py (avgtime|avgday|listplays) [Song name]")

if __name__ == "__main__":
    import sys
    run(sys.argv)

