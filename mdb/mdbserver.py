import http.server
import http.client
import socketserver
import sqlite3
import random
import json
import sched
import time
import threading
import math
import operator
import urllib.parse

import mdb.seed
import mdb.util
import mdb.songgraph

sdb = sqlite3.connect("data/music-v3.sqlite3")
weather_db = sqlite3.connect("data/weather.sqlite3")
graph = mdb.songgraph.make_play_graph(sdb)
times_dict = mdb.dtutil.times_dict(sdb)
pdens = mdb.seed.play_times_density(times_dict)
wdens = mdb.seed.get_weather_dens(weather_db, sdb)
combo_dens = {}

def update_pdens(schedu, sdb_tl, wdb_tl):
    global wdens
    global pdens
    global combo_dens
    print("updating")
    # Need new connection for running this in a different thread
    if sdb_tl is None or wdb_tl is None:
        sdb_tl = sqlite3.connect("data/music-v3.sqlite3")
        wdb_tl = sqlite3.connect("data/weather.sqlite3")
    pdens = mdb.seed.play_times_density(times_dict)
    wdens = mdb.seed.get_weather_dens(wdb_tl, sdb_tl)
    combo_dens = {sid: (weather_dens * math.sqrt(pdens[sid])) for (sid, weather_dens) in wdens.items()}
    combo_dens = mdb.seed.keywise_mult(wdens, pdens)
    for key in pdens:
        if key not in combo_dens:
            combo_dens[key] = pdens[key] * 0.04
    # Mix it up...
    # Plays adjuster
    plays_adj = mdb.seed.num_plays_adjustment(times_dict, weight=0.01)
    combo_dens = mdb.seed.keywise_mult(combo_dens, plays_adj)
    # Rating adjuster
    rating_adj = mdb.seed.rating_adjustment(sdb_tl, weight=0.8)
    combo_dens = mdb.seed.keywise_mult(combo_dens, rating_adj)
    # Recentness - has to go last for now 'cause it's funky
    lplay_dist = mdb.seed.last_play_distance(times_dict)
    combo_dens = mdb.seed.play_dens_adjust_lastplay(combo_dens, lplay_dist, sdb_tl, 28/365)
    # Add a tad bit of randomness
    mdb.seed.randomise_seeds(combo_dens, sigma=0.04)
    
    print("done")
    schedu.enter(60, 0, update_pdens, (schedu, sdb_tl, wdb_tl))

def update_pdens_thread():
    schedu = sched.scheduler(time.time, time.sleep)
    schedu.enter(1, 0, update_pdens, (schedu, None, None))
    schedu.run()


class MDBRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,x,y,z):
        super().__init__(x,y,z)

    def _encode_song_list(self, songkeys):
        songs = [[mdb.util.get_key_sname(key, sdb), mdb.util.get_key_artist(key, sdb), key] for key in songkeys]
        return json.dumps(songs).encode("utf-8")

    def _do_ok(self):
        self.send_response(200)
        # Allow Ajax requests from locally-run servers, but nowhere else
        if urllib.parse.urlparse(str(self.headers["Origin"])).netloc.split(":")[0] == "localhost":
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
        self.send_header('Content-Type', 'application/json')

    def do_GET(self):
        if self.path=="/simpleseed":
            songkeys = mdb.seed.get_start_points(sdb)[:20]
            self._do_ok()
            self.end_headers()
            self.wfile.write(self._encode_song_list(songkeys))
        elif self.path=="/weatherseed":
            print(self.headers)
            #seed = sorted([(sid, weather_dens * math.sqrt(pdens[sid])) for (sid, weather_dens) in wdens.items()], key=operator.itemgetter(1), reverse=True)
            # Randomise each time we run this to give a slightly different result
            mdb.seed.randomise_seeds(combo_dens, sigma=0.02)
            seed = sorted([(key, combo_dens[key]) for key in combo_dens], key=operator.itemgetter(1), reverse=True)
            songkeys = [x[0] for x in seed[:20]]
            self._do_ok()
            self.end_headers()
            self.wfile.write(self._encode_song_list(songkeys))
        elif self.path.startswith("/graphcrawl"):
            sel_song = int(self.path.split("?")[1])
            lst = mdb.songgraph.graph_walk(sel_song, graph, combo_dens)
            self._do_ok()
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
