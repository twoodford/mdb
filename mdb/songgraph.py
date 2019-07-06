# songgraph.py (mdb.songgraph)
# Copyright (C) 2014-2017 Timothy Woodford.  All rights reserved.
# Create song-related graph structures
from datetime import timedelta
import random
import networkx as nx

def make_play_graph(sdb, grtype=nx.DiGraph):
    """ Read the play times from sdb and return a NetworkX graph structure with nodes representing songs and 
        edges representing sequential plays.
    """
    gr = grtype()
    cur = sdb.cursor()
    # We don't need timezone awareness here - songs that were played close together
    cur.execute("SELECT song, unixlocaltime FROM plays ORDER BY unixlocaltime ASC")
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
    def __init__(self, default_value=1):
        self.val = default_value

    def __getitem__(self, index):
        return self.val

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


def graph_walk_dual(start_key, graph, song_weight=_emptydict(0.05), max_len=30):
    """Like graph_walk_maxocc, but tries to go in reverse as well as forward along the graph.
    Except if song_weight is set, in which case weights are adjusted by the song weights."""
    if start_key not in graph: return [start_key]
    seq = [start_key]
    while len(seq) < max_len:
        end = seq[-1]
        start = seq[0]
        sweigh = lambda x: song_weight[x] if song_weight[x] > 0 else 0.000000001
        cand_end = [x for x in graph.successors(end) if x not in seq]
        end_possible = [(x, graph[end][x]["weight"]/sweigh(x)) for x in cand_end]
        end_possible.sort(key=lambda x: x[1], reverse=False)
        cand_begin = [x for x in graph.predecessors(start) if x not in seq]
        begin_possible = [(x, graph[x][start]["weight"]/sweigh(x)) for x in cand_begin]
        begin_possible.sort(key=lambda x: x[1], reverse=False)
        if len(end_possible) > 0:
            if len(begin_possible) > 0:
                # Both have at least 1 item
                if end_possible[0][1] > begin_possible[0][1]:
                    # Append to end - end is better
                    seq.append(end_possible[0][0])
                else:
                    # Insert at beginning - beginning is better
                    seq.insert(0, begin_possible[0][0])
            else:
                # Have end possibility, but no beginning possibility
                seq.append(end_possible[0][0])
        elif len(begin_possible) > 0:
            # Have beginning possibility, but no end
            seq.insert(0, begin_possible[0][0])
        else:
            # No possibilities at all :(
            break
    return seq

def graph_walk_maxocc(start_key, graph, song_weight=_emptydict(), max_depth=15):
    "Walk the graph by always taking the song that has most frequently been played after the current song"
    sequence = [start_key]
    last = start_key
    while len(sequence) < max_depth:
        current = sequence[-1]
        next_ = None
        for succ in graph.successors(current):
            print(succ, graph[current][succ]["weight"])
            if next_ is None or graph[current][next_]["weight"] > graph[current][succ]["weight"]:
                next_ = succ
        sequence.append(next_)
        break
    return sequence
