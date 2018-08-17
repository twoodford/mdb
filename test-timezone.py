import sqlite3

import mdb.dtutil
import mdb.util

sdb = sqlite3.connect("data/music.sqlite3")

fun = mdb.dtutil.times_dict(sdb)

index = mdb.util.sname_artist_to_key("Breathe", "U2", sdb)

print(index)

print(fun[index][-1])
