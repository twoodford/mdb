#!/opt/local/bin/python3.6
# Experiment in finding weather matches
# NOTE EXPERIMENT should be made into something nicer sometime
import datetime
import math
import operator
import sqlite3
import time

import mdb.dtutil
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
    mdbdb = sqlite3.connect("data/music.sqlite3")
    times_dict = mdb.dtutil.times_dict(mdbdb)
    wdens = mdb.seed.get_weather_dens(wdb, mdbdb)
    #wdens = collect_songs(morefun, mdbdb)
    # Revise with time-based play densities
    pdens = mdb.seed.play_times_density(times_dict)
    combo_dens = mdb.seed.keywise_mult(wdens, pdens)
    for key in pdens:
        if key not in combo_dens:
            combo_dens[key] = pdens[key] * 0.05
    # Mix it up...
    # Plays adjuster
    plays_adj = mdb.seed.num_plays_adjustment(times_dict, weight=0.4)
    combo_dens = mdb.seed.keywise_mult(combo_dens, plays_adj)
    # Rating adjuster
    rating_adj = mdb.seed.rating_adjustment(mdbdb, weight=0.8)
    combo_dens = mdb.seed.keywise_mult(combo_dens, rating_adj)
    # Recentness - has to go last for now 'cause it's funky
    lplay_dist = mdb.seed.last_play_distance(times_dict)
    #combo_dens = mdb.seed.play_dens_adjust_lastplay(combo_dens, lplay_dist, mdbdb, 28/365)
    revised = sorted([(key, combo_dens[key]) for key in combo_dens], key=operator.itemgetter(1), reverse=True)
    #[print(mdb.util.key_to_string(song[0], mdbdb), song[1]) for song in wdens[:15]]
    print("alternate")
    [print(mdb.util.key_to_string(song[0], mdbdb), song[1]) for song in revised[:15]]

