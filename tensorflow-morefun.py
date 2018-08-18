import datetime
from math import cos, sin
import operator
import pickle
import sqlite3
import time

import tensorflow as tf
import numpy as np
from tensorflow import keras

import mdb.circstats

# Architecture sketch: pluggable modules that do play key -> list or int
# Add in a labeller that maps play key -> song
class MDBTemperatureSource(object):
    output_dim = 1
    _last_temp = 0
    def __init__(self, weather_db):
        self._wdb = weather_db
        cur = weather_db.cursor()
        cur.execute("SELECT pkey, temp_c FROM basic_weather AS bw JOIN play_weather_match AS pwm ON pwm.basic_time=bw.time")
        self._mappings = {}
        for (pkey, temp_c) in cur.fetchall():
            self._mappings[pkey] = temp_c

    def train_data(self, pkey):
        try:
            self._last_temp = self._mappings[pkey]
            return self._mappings[pkey]
        except:
            return self._last_temp # ??????

class MDBDayTimeSource(object):
    output_dim = 2
    def __init__(self, mdb):
        cur = mdb.cursor()
        cur.execute("SELECT pkey, unixlocaltime FROM plays")
        self._mappings = {}
        for row in cur:
            self._mappings[row[0]] = row[1]

    def train_data(self, pkey):
        tm = datetime.datetime.fromtimestamp(self._mappings[pkey])
        angle = mdb.circstats.preproc_timeofday(tm)
        return [cos(angle), sin(angle)]

class MDBDataBuilder(object):
    data_sources = []

    def __init__(self, songs_db):
        self._sdb = songs_db

    def build_data(self, time_lim):
        cur = self._sdb.cursor()
        cur.execute("SELECT pkey FROM plays WHERE unixlocaltime > ?", (time_lim,))
        pkeys = [row[0] for row in cur]
        data = np.zeros((len(pkeys), sum([src.output_dim for src in self.data_sources])))
        pindex = 0
        for pkey in pkeys:
            pdat = []
            for src in self.data_sources:
                dat = src.train_data(pkey)
                try: pdat += dat
                except TypeError: pdat.append(dat)
            data[pindex,:] = pdat
            pindex += 1
        return data

    def build_labels(self, time_lim):
        cur = self._sdb.cursor()
        cur.execute("SELECT sid FROM songs")
        num_songs = len(cur.fetchall())
        cur.execute("SELECT song FROM plays WHERE unixlocaltime > ?", (time_lim,))
        sids = [row[0] for row in cur]
        data = np.zeros((len(sids), num_songs))
        for (pindex, sid) in enumerate(sids):
            data[pindex, sid] = 1
        return data
    
    def num_outputs(self, time_lim):
        cur = self._sdb.cursor()
        cur.execute("SELECT sid FROM songs")
        num_songs = len(cur.fetchall())
        return num_songs

sdb = sqlite3.connect("data/music.sqlite3")
weather = sqlite3.connect("data/weather.sqlite3")

time_lim = round(time.clock_gettime(time.CLOCK_REALTIME)) - 60*60*24*30*10
builder = MDBDataBuilder(sdb)
if True:
    s = time.time()
    labels = builder.build_labels(time_lim)
    print("label time", time.time()-s)
    s = time.time()
    builder.data_sources.append(MDBTemperatureSource(weather))
    builder.data_sources.append(MDBDayTimeSource(sdb))
    data = builder.build_data(time_lim)
    print("data time", time.time()-s)
    with open("labels.pk", "wb") as f:
        pickle.dump(labels, f)
    with open("data.pk", "wb") as f:
        pickle.dump(data, f)
else:
    with open("labels.pk", "rb") as f:
        labels = pickle.load(f)
    with open("data.pk", "rb") as f:
        data = pickle.load(f)

model = keras.Sequential()
model.add(keras.layers.Dense(4))
#model.add(tf.keras.layers.Dropout(0.2))
model.add(keras.layers.Dense(builder.num_outputs(time_lim)))

model.compile(optimizer=tf.train.AdamOptimizer(0.001),
              loss='mse',
              metrics=['accuracy'])

#data = np.concatenate((np.ones((5,1)), np.zeros((6,1))), 0)
#labels = np.concatenate((np.zeros((5,1)), np.ones((6,1))), 0)
#print(data)

model.fit(data, labels, epochs=4, batch_size=4)

print(model.predict(np.array([[24, 1, 0], [24, -1, 0]]), steps=5)[1,:])

def do_predict(temp):
    prediction = model.predict(np.array([temp]), steps=5)[1,:]

    max_index, max_value = max(enumerate(prediction), key=operator.itemgetter(1))

    print(max_index, max_value)
    cur = sdb.cursor()
    cur.execute("SELECT * FROM songs WHERE key=?", (max_index,))
    print(cur.fetchall())

x=[]
for i in range(-4,30):
    prediction = model.predict(np.array([[i, 0, 0], [0, 0, 0]]), steps=5)[1,:]
    max_index, max_value = max(enumerate(prediction), key=operator.itemgetter(1))
    x.append(max_index)

print(x)


x=[]
for i in range(-4,30):
    prediction = model.predict(np.array([[i, 0, 1], [0, 0, 0]]), steps=5)[1,:]
    max_index, max_value = max(enumerate(prediction), key=operator.itemgetter(1))
    x.append(max_index)

print(x)
