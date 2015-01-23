# songgraph.py (mdb.songgraph)
# Copyright (C) 2014 Timothy Woodford.  All rights reserved.
# Create song-related graph structures
from datetime import timedelta
import networkx as nx

def make_play_graph(sdb, grtype=nx.MultiDiGraph):
    gr = grtype()
    cur = sdb.cursor()
    cur.execute("SELECT song, datetime FROM plays")
    prev = None
    for row in cur.fetchall():
        if prev:
            if (row[1] - prev[1]) < 12*60: # Find difference in timestamps
                nd1 = int(prev[0])
                nd2 = int(row[0])
                try:
                    gr[nd1][nd2]["weight"] /= 2
                except KeyError:
                    gr.add_edge(nd1, nd2, weight=16)
        prev = row
    return gr
    
def possible_routes(start_key, graph, maxdepth, _visited=None):
    """ Function to find all possible routes that we could take along the given graph, 
        starting at the song given by start_key, up to a certain maximum number of songs 
        in list.  Note: The _visited parameter is for internal use only.  This is a 
        recursive method, which places an upper limit on maxdepth.
    """
    if _visited is None:
        _visited = list()
    if maxdepth == 1:
        ret = [[song] for song in graph.successors(start_key)]
    else:
        _visited.append(start_key)
        ret = list()
        for song in graph.successors(start_key):
            if not song in _visited:
                ret.extend([[start_key] + route for route in possible_routes(song, graph, maxdepth - 1, _visited)])
    if len(ret) == 0:
        ret.append([start_key])
    return ret
