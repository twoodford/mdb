import tensorflow as tf
import numpy as np
from tensorflow import keras

model = keras.Sequential()
model.add(keras.layers.Dense(2))
model.add(keras.layers.Dense(1))

model.compile(optimizer=tf.train.AdamOptimizer(0.001),
              loss='mse',
              metrics=['accuracy'])

data = np.concatenate((np.ones((5,1)), np.zeros((6,1))), 0)
labels = np.concatenate((np.zeros((5,1)), np.ones((6,1))), 0)
print(data)

model.fit(data, labels, epochs=10, batch_size=4)

print(model.predict(np.array([1]), steps=4))
