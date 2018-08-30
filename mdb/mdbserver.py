import http.server
import socketserver
import sqlite3
import random
import json
import sched
import time
import threading
import math
import operator

import mdb.dtutil
import mdb.seed
import mdb.util
import mdb.songgraph

sdb = sqlite3.connect("data/music.sqlite3")
times_dict = mdb.dtutil.times_dict(sdb)
weather_db = sqlite3.connect("data/weather.sqlite3")
graph = mdb.songgraph.make_play_graph(sdb)
pdens = mdb.seed.play_times_density(times_dict)
wdens = mdb.seed.get_weather_dens(weather_db, sdb)
rateadj = mdb.seed.rating_adjustment(sdb, weight=0.8)
playadj = mdb.seed.num_plays_adjustment(times_dict, weight=0.6)
combo_dens = {}


def update_pdens(schedu, sdb_tl, wdb_tl):
    global wdens
    global pdens
    global combo_dens
    print("updating")
    if sdb_tl is None or wdb_tl is None:
        sdb_tl = sqlite3.connect("data/music.sqlite3")
        wdb_tl = sqlite3.connect("data/weather.sqlite3")
    st = time.time()
    pdens = mdb.seed.play_times_density(times_dict)
    wdens = mdb.seed.get_weather_dens(wdb_tl, sdb_tl)
    combo_dens_sc = mdb.seed.keywise_mult(wdens, pdens)
    combo_dens_sc = mdb.seed.keywise_mult(combo_dens_sc, rateadj)
    combo_dens_sc = mdb.seed.keywise_mult(combo_dens_sc, playadj)
    for key in pdens:
        if key not in combo_dens_sc:
            combo_dens_sc[key] = pdens[key] * 0.02
    # Don't want to modify global in place
    combo_dens = combo_dens_sc
    print("done", time.time()-st)
    schedu.enter(60, 0, update_pdens, (schedu, sdb_tl, wdb_tl))

def update_pdens_thread():
    schedu = sched.scheduler(time.time, time.sleep)
    schedu.enter(2, 0, update_pdens, (schedu, None, None))
    schedu.run()


class MDBRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,x,y,z):
        super().__init__(x,y,z)

    def _encode_song_list(self, songkeys):
        songs = [[mdb.util.get_key_sname(key, sdb), mdb.util.get_key_artist(key, sdb), key] for key in songkeys]
        return json.dumps(songs).encode("utf-8")

    def do_GET(self):
        if self.path=="/simpleseed":
            songkeys = mdb.seed.get_start_points(sdb)[:20]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self._encode_song_list(songkeys))
        elif self.path=="/weatherseed":
            seed = sorted([(key, combo_dens[key]) for key in combo_dens], key=operator.itemgetter(1), reverse=True)
            songkeys = [x[0] for x in seed[:20]]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self._encode_song_list(songkeys))
        elif self.path.startswith("/graphcrawl"):
            sel_song = int(self.path.split("?")[1])
            lst = mdb.songgraph.graph_walk(sel_song, graph, combo_dens)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self._encode_song_list(lst))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write("not found\n".encode("utf-8"))

def mdbserv():
    Handler = MDBRequestHandler
    thr = threading.Thread(target=update_pdens_thread)
    thr.start()
    httpd = socketserver.TCPServer(("", 8000), Handler)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()

if __name__=="__main__":
    mdbserv()
