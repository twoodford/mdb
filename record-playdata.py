#!/opt/local/bin/python3.5
# import-playdata.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
#
# Move play data to sqlite3 database

import calendar
import plistlib
import sqlite3
import time

from mdb import util

# The following note applies to much of the code below:
# Shamelessly copied from itunes-record.py in the hope that the old ways may eventually disappear
# Please ignore the occasional snark in the comments.

def db_init(db):
    cur = db.cursor()
    cur.execute("CREATE TABLE songs (key integer primary key, sid blob, name string, artist string, genre string)")
    cur.execute("""CREATE TABLE plays (
                        pkey integer primary key,
                        song integer,
                        datetime integer,
                        FOREIGN KEY(song) REFERENCES songs(key)
                )""")
    db.commit()

def songdat_recorder(db):
    cur = db.cursor()
    def _record(song):
        try:
            sid = int(song["Persistent ID"], 16)
            nm = song["Name"]
            art = song["Artist"]
            cur.execute("SELECT * FROM songs WHERE sid=?", (str(sid),))
            # str() is used above to avoid automatic conversion to an sqlite integer.  sids are blobs due to size.
            if len(cur.fetchall())>0:
                return # TODO check if we need to do updates
            cur.execute("INSERT INTO songs(sid, name, artist) VALUES (?,?,?)", (str(sid), nm, art))
            # See if we can add the genre, too
            genre = song["Genre"]
            cur.execute("UPDATE songs SET genre=? WHERE sid=?", (genre, str(sid)))
            db.commit()
        except KeyError:
            pass
    return _record

def play_recorder(db):
    cur = db.cursor()
    def _record(song):
        try:
            # Unfortunately, "Play Date UTC" doesn't seem to actually mean the UTC part
            # This is actually "UTC-but-it-changes-with-daylight-savings-time"
            # Yeah.
            # UTC.
            # Right.
            tmn = calendar.timegm(song["Play Date UTC"].utctimetuple())
            if time.localtime().tm_isdst:
                tmn += 60*60 # So dumb, Apple
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
            # Check if this play has already been recorded
            cur.execute("SELECT * FROM plays WHERE song=? AND datetime=?", (key, tmn))
            if len(cur.fetchall()) == 0:
                print(song["Name"]+" got played at "+str(song["Play Date UTC"]))
                # Record play data
                cur.execute("INSERT INTO plays(song, datetime) VALUES (?, ?)", (key, tmn))
        except KeyError:
            pass
    return _record

def import_songdata(db):
    _record = songdat_recorder(db)
    proclib("/Users/tim/Music/iTunes/iTunes Music Library.xml", (_record,))

def collect_playdata(db):
    _record = play_recorder(db)
    proclib("/Users/tim/Music/iTunes/iTunes Music Library.xml", (_record,))
    db.commit()

def proclib(fname, callbacks):
    with open(fname, "rb") as libf:
        lib = plistlib.readPlist(libf)
    for songid in lib["Tracks"]:
        song = lib["Tracks"][songid]
        try:
            if song["Podcast"]: continue
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
    else:
        print("Usage: record-playdata.py [command]")
        print("Commands:")
        print(" * initdb")
        print(" * songs")
        print(" * plays")
    db.close()

