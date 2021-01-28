#!/opt/local/bin/python3.8
# simplesuggest.py
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
from __future__ import print_function
import sys
import sqlite3

import mdb.seed
import mdb.util
import mdb.songgraph

if __name__=="__main__":
    sdb = sqlite3.connect("data/music.sqlite3")
    graph = mdb.songgraph.make_play_graph(sdb)
    dens = mdb.seed.play_density(sdb)
    if len(sys.argv)<=1:
        for key in mdb.seed.get_start_points(sdb):
            sel_song = key
            if sel_song in graph:
                break
    else:
        sel_song = mdb.util.sname_to_key(sys.argv[1], sdb)
        print(sel_song)
    slist = mdb.songgraph.graph_walk_maxocc(sel_song, graph, dens)
    slist = mdb.songgraph.graph_walk_dual(sel_song, graph, max_len=10)
    [print(mdb.util.key_to_string(key, sdb)) for key in slist]
