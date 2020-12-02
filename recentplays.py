#!/opt/local/bin/python3.8

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

def collect_artists(songids, mdbdb):
    cur = mdbdb.cursor()
    plays = {}
    for songid in songids:
        cur.execute("SELECT artist FROM songs WHERE key=?", (songid[0],))
        (artist,)=cur.fetchone()
        try:
            plays[artist] += songid[1]
        except KeyError:
            plays[artist] = songid[1]
    cur.close()
    return sorted(plays.items(), key=operator.itemgetter(1), reverse=True)

if __name__=="__main__":
    mdbdb = sqlite3.connect("data/music-v3.sqlite3")
    print("most recent")
    mcur = mdbdb.cursor()
    cur_time = round(time.clock_gettime(time.CLOCK_REALTIME))
    mcur.execute("SELECT * FROM plays WHERE unixtime > ? AND unixtime < ?", (cur_time - 60*60*24*31*12, (cur_time + 0)))
    #mcur.execute("SELECT * FROM plays WHERE unixtime > ? AND unixtime < ?", (cur_time - 60*60*24*365*2, cur_time - 60*60*24*365))
    #mcur.execute("SELECT * FROM plays WHERE datetime > ? AND datetime < ?", (cur_time - 60*60*24*30*5,cur_time - 60*60*24*30*3))
    rlist = mcur.fetchall()
    recent = collect_songs(rlist, mdbdb)
    print("Top Songs:")
    [print(" ", mdb.util.key_to_string(song[0], mdbdb), song[1]) for song in recent[:15]]
    print("Top Artists:")
    artists = collect_artists(recent, mdbdb)
    [print(" ", artist[0], artist[1]) for artist in artists[:10]]
