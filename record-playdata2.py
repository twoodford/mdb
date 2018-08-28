#!/opt/local/bin/python3.6
# import-playdata.py
# Copyright (C) 2014-2018 Timothy Woodford.  All rights reserved.
#
# Move play data to sqlite3 database

import calendar
import plistlib
import os
import os.path
import sqlite3
import time

from mdb import util

ITL_PATH = os.path.expanduser("~/Music/iTunes/iTunes Music Library.xml")

# The following note applies to much of the code below:
# Shamelessly copied from itunes-record.py in the hope that the old ways may eventually disappear
# Please ignore the occasional snark in the comments.

def db_init(db):
    cur = db.cursor()
    cur.execute("CREATE TABLE songs (key integer primary key, sid blob, name string, artist string, genre string, rating integer)")
    cur.execute("""CREATE TABLE plays (
                        pkey integer primary key,
                        song integer,
                        unixlocaltime integer,
                        utcoffs integer,
                        FOREIGN KEY(song) REFERENCES songs(key)
                )""")
    db.commit()


def db_convert(ndb):
    odb = sqlite3.connect("data/music.sqlite3")
    ocur = odb.cursor()
    ncur = ndb.cursor()
    ocur.execute("SELECT plays.pkey, plays.datetime, songs.sid FROM plays INNER JOIN songs ON plays.song = songs.key")
    plays = ocur.fetchall()
    for play in plays:
        (pkey, datime, sid) = play
        ncur.execute("SELECT songs.key FROM songs WHERE songs.sid=?", (sid,))
        try:
            song_key = ncur.fetchall()[0][0]
            ncur.execute("INSERT INTO plays(pkey, song, unixtime, utcoffs) VALUES (?, ?,?,?)", (pkey, song_key, datime-18000, -18000))
        except IndexError: pass # Song gone bye-bye
    ndb.commit()


def _record_song_info(song, cur):
    try:
        sid = int(song["Persistent ID"], 16)
        nm = song["Name"]
        art = song["Artist"]
        cur.execute("SELECT name, artist, genre, rating FROM songs WHERE sid=?", (str(sid),))
        # str() is used above to avoid automatic conversion to an sqlite integer.  sids are blobs due to size.
        existing = cur.fetchall()
        if len(existing)>0:
            if str(existing[0][0]) != nm:
                print("Name update", nm, existing[0][0], art)
                cur.execute("UPDATE songs SET name=? WHERE sid=?", (nm, str(sid)))
            if str(existing[0][1]) != art:
                print("Artist update", nm, existing[0][1], art)
                cur.execute("UPDATE songs SET artist=? WHERE sid=?", (art, str(sid)))
            try:
                genre = song["Genre"]
                if existing[0][2] != genre:
                    print("Genre update", nm, existing[0][1], art)
                    cur.execute("UPDATE songs SET genre=? WHERE sid=?", (genre, str(sid)))
            except KeyError: pass
            try:
                genre = song["Rating"]
                if existing[0][3] != genre:
                    cur.execute("UPDATE songs SET rating=? WHERE sid=?", (genre, str(sid)))
            except KeyError: pass
        else:
            cur.execute("INSERT INTO songs(sid, name, artist) VALUES (?,?,?)", (str(sid), nm, art))
        db.commit()
    except KeyError:
        pass

def play_recorder(db, min_time):
    "Only considers play times after min_time"
    cur = db.cursor()
    def _record(song):
        _record_song_info(song, cur)
        try:
            # Play Date defined with regards to HFS epoch shifted to local timezone
            tmn = int(song["Play Date"]) - 2082844800
            if tmn < min_time:
                return
            sid = int(song["Persistent ID"], 16)
            nm = song["Name"]
            artist = song["Artist"]
            # Get song key
            try:
                key = util.sname_artist_to_key(nm, artist, db)
            except TypeError:
                # Didn't find anything!
                print("Error: couldn't find song "+nm+" by "+artist)
                return

            #DBG
            #cur.execute("SELECT * FROM plays WHERE song=?", (key,))
            #for x in cur.fetchall():
            #    print(x)
            # Check if this play has already been recorded
            cur.execute("SELECT * FROM plays WHERE song=? AND unixlocaltime=?", (key, tmn))
            if len(cur.fetchall()) == 0:
                print(str(song["Name"].encode(), 'ascii', 'ignore')+" got played at "+time.asctime(time.gmtime(tmn)))
                # Record play data
                cur.execute("INSERT INTO plays(song, unixlocaltime, utcoffs) VALUES (?, ?, ?)", (key, tmn, time.localtime().tm_gmtoff))
        except KeyError:
            pass
    return _record

def import_songdata(db):
    _record = songdat_recorder(db)
    proclib(ITL_PATH, (_record,))

def collect_playdata(db):
    mtime = os.stat("data/music.sqlite3").st_mtime
    mtime -= 2*24*60*60
    _record = play_recorder(db, mtime)
    proclib(ITL_PATH, (_record,))
    db.commit()

def proclib(fname, callbacks):
    with open(fname, "rb") as libf:
        lib = plistlib.readPlist(libf)
    for songid in lib["Tracks"]:
        song = lib["Tracks"][songid]
        try:
            if song["Podcast"]:
                try:
                    if song["Location"].count("Podcast") > 0: continue
                    if song["Track Type"] != "File": continue
                except KeyError: continue
        except KeyError: pass
        try:
            if song["TV Show"]: continue
        except KeyError: pass
        try:
            if song["iTunesU"]: continue
        except KeyError: pass
        for callback in callbacks:
            callback(song)

if __name__=="__main__":
    import sys
    cmd = sys.argv[1]
    db = sqlite3.connect("data/music.sqlite3")
    if cmd=="initdb":
        db_init(db)
    elif cmd=="songs":
        import_songdata(db)
    elif cmd=="plays":
        collect_playdata(db)
    elif cmd=="convert":
        db_convert(db)
    else:
        print("Usage: record-playdata.py [command]")
        print("Commands:")
        print(" * initdb")
        print(" * songs")
        print(" * plays")
    db.close()

