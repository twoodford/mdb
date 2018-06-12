# songgraph.py (mdb.songgraph)
# Copyright (C) 2014-2017 Timothy Woodford.  All rights reserved.
# Create song-related graph structures
from datetime import timedelta
import random
import networkx as nx

def make_play_graph(sdb, grtype=nx.MultiDiGraph):
    """ Read the play times from sdb and return a NetworkX graph structure with nodes representing songs and 
        edges representing sequential plays.
    """
    gr = grtype()
    cur = sdb.cursor()
    # We don't need timezone awareness here - songs that were played close together
    cur.execute("SELECT song, unixtime FROM plays")
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
    
# TODO this is inherently sub-optimal - need a better way to do find a route
def possible_routes(start_key, graph, maxdepth, _visited=None):
    """ Function to find all possible routes that we could take along the given graph, 
        starting at the song given by start_key, up to a certain maximum number of songs 
        in list.  Note: The _visited parameter is for internal use only.  This is a 
        recursive method, which places an upper limit on maxdepth.
    """
    if _visited is None:
        _visited = list()
    if maxdepth == 1:
        ret = [[song] for song in graph.successors(start_key) if not song in _visited]
    else:
        _visited.append(start_key)
        ret = list()
        for song in graph.successors(start_key):
            if not song in _visited:
                ret.extend([[start_key] + route for route in possible_routes(song, graph, maxdepth - 1, _visited)])
    return ret

class _emptydict(object):
    def __getitem__(self, index):
        return 1

def graph_walk(start_key, graph, song_weight=_emptydict(), max_depth=15, iter_depth=3, mean_selection_index=5):
    sequence = [start_key]
    last = start_key
    lmbda=1/mean_selection_index
    while len(sequence) < max_depth:
        options = possible_routes(last, graph, iter_depth, _visited=list(sequence))
        def _lstdens(lst):
            return sum([song_weight[key] for key in lst])
        options.sort(key=_lstdens, reverse=True)
        if len(options)==0:
            break
        # Bias selection towards things that are earlier in list
        choice = options[min(round(random.expovariate(lmbda)), len(options)-1)]
        if len(choice)==0:
            break
        sequence.append(choice[1])
        last = sequence[-1]
    return sequence
