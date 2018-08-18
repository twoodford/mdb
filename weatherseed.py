#!/opt/local/bin/python3.6
# Experiment in finding weather matches
# NOTE EXPERIMENT should be made into something nicer sometime
import datetime
import math
import operator
import sqlite3
import time

import mdb.seed
import mdb.util

def collect_songs(playids, mdbdb):
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

if __name__=="__main__":
    # Note: requires recent weather in weather.sqlite
    wdb = sqlite3.connect("data/weather.sqlite3")
    cur = wdb.cursor()
    mintime = (datetime.datetime.now() - datetime.timedelta(days=2)).timestamp()
    cur.execute("SELECT * FROM basic_weather WHERE time > ? ORDER BY time DESC", (mintime,))
    (temp,pressure,precip) = cur.fetchone()[1:]
    cur.execute("SELECT * FROM nws_weather WHERE time > ? ORDER BY time DESC", (mintime,))
    (sky,cloudcover,weathertype) = cur.fetchone()[1:4]

    mdbdb = sqlite3.connect("data/music.sqlite3")
    cur.execute("SELECT pkey FROM play_weather_match AS pwm JOIN nws_weather AS nws ON pwm.nws_time=nws.time LEFT OUTER JOIN basic_weather AS bw ON pwm.basic_time=bw.time WHERE temp_c > ? AND temp_c < ?", (temp-5, temp+5))
    fun = cur.fetchall()
    print(len(fun))
    print(weathertype)
    if weathertype != "?":
        cur.execute("SELECT pkey FROM play_weather_match AS pwm JOIN nws_weather AS nws ON pwm.nws_time=nws.time LEFT OUTER JOIN basic_weather AS bw ON pwm.basic_time=bw.time WHERE nws.weathertype=?", (weathertype,))
        morefun = cur.fetchall()
    else:
        morefun = []
    print(len(morefun))
    #seed = collect_songs(morefun+fun, mdbdb)
    seed = collect_songs(morefun, mdbdb)
    # Revise with time-based play densities
    pdens = mdb.seed.play_density(mdbdb)
    revised = sorted([(sid, weather_dens * math.sqrt(pdens[sid])) for (sid, weather_dens) in seed[:100]], key=operator.itemgetter(1), reverse=True)
    [print(mdb.util.key_to_string(song[0], mdbdb), song[1]) for song in seed[:15]]
    print("alternate")
    [print(mdb.util.key_to_string(song[0], mdbdb), song[1]) for song in revised[:15]]

