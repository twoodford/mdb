#!/opt/local/bin/python3.6
# db-converter.py
# Copyright (C) 2018 Timothy Woodford.  All rights reserved.
# 
# Convert to new database format

import sqlite3

# EST
utcoffs = -5*60*60 # seconds

def do_migration(db):
    cur = db.cursor()
    cur.execute("ALTER TABLE plays RENAME TO old_plays")
    cur.execute("""CREATE TABLE plays (
                        pkey integer primary key,
                        song integer,
                        unixlocaltime integer,
                        utcoffs integer,
                        FOREIGN KEY(song) REFERENCES songs(key)
                )""")
    cur.execute("SELECT pkey, song, datetime FROM old_plays")
    for row in cur.fetchall():
        (pkey, song, timeval) = row
        # timevalue EST -> UTC
        #timeval += utcoffs
        # Note on how time works with iTunes: the unix epoch is offset for your timezone
        # This is how iTunes stores times across its databases, so I'm not going to mess with this
        cur.execute("INSERT INTO plays VALUES (?,?,?,?)", (pkey, song, timeval, utcoffs))
    db.commit()

if __name__=="__main__":
    db = sqlite3.connect("data/music.sqlite3")
    do_migration(db)
    db.close()
