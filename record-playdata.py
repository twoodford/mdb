#!/usr/bin/which python3.4
# import-playdata.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
#
# Move play data to sqlite3 database

import plistlib
import sqlite3

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

def import_songdata(db):
    _record = songdat_recorder(db)
    proclib("/Users/timothy/Music/iTunes/iTunes Library.xml", (_record,))

# Shamelessly copied from itunes-record.py in the hope that the old ways may eventually disappear
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
    else:
        print("Usage: record-playdata.py [command]")
        print("Commands:")
        print(" * initdb")
        print(" * songs")
    db.close()

