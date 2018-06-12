# util.py (mdb.util)
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
# Various useful utilities for managing the music database

def key_to_string(key, sdb):
    cur = sdb.cursor()
    cur.execute("SELECT name, artist FROM songs WHERE key=?", (key,))
    result = cur.fetchone()
    return str(result[1])+" - "+str(result[0])

def key_to_sid(key, sdb):
    cur = sdb.cursor()
    cur.execute("SELECT sid FROM songs WHERE key=?", (key,))
    return long(cur.fetchone()[0])

def sname_to_key(sname, sdb):
    cur = sdb.cursor()
    cur.execute("SELECT key FROM songs WHERE name=?", (sname,))
    return cur.fetchone()[0]

def sname_artist_to_key(sname, artist, sdb):
    cur = sdb.cursor()
    cur.execute("SELECT key FROM songs WHERE name=? AND artist=?", (sname, artist))
    return cur.fetchone()[0]

def get_key_artist(key, sdb):
    cur = sdb.cursor()
    cur.execute("SELECT artist FROM songs WHERE key=?", (key,))
    return cur.fetchone()[0]

def get_key_sname(key, sdb):
    cur = sdb.cursor()
    cur.execute("SELECT name FROM songs WHERE key=?", (key,))
    return cur.fetchone()[0]
