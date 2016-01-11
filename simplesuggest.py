#!/opt/local/bin/python3.5
# simplesuggest.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
from __future__ import print_function
from datetime import datetime, time
import random
import sys
import sqlite3

import mdb.seed
import mdb.util
import mdb.songgraph

def proc_adjacent_graph(sel_sid, graph, sdb):
    possible = mdb.songgraph.possible_routes(sel_sid, graph, 10)
    dens = mdb.seed.play_density(sdb)
    def _lstdens(lst):
        return sum([dens[key] for key in lst])
    possible.sort(key=_lstdens, reverse=True)
    # Randomly choose a sequence, with a bias towards stuff at the beginning
    rngmod = len(possible)//2 + 1
    for lst in possible:
        if random.randrange(rngmod) == 0:
            return lst

if __name__=="__main__":
    sdb = sqlite3.connect("data/music.sqlite3")
    graph = mdb.songgraph.make_play_graph(sdb)
    if len(sys.argv)<=1:
        for key in mdb.seed.get_start_points(sdb):
            sel_song = key
            if sel_song in graph:
                break
    else:
        sel_song = mdb.util.sname_to_key(sys.argv[1], sdb)
    slist = proc_adjacent_graph(sel_song, graph, sdb)
    [print(mdb.util.key_to_string(key, sdb)) for key in slist]
