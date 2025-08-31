import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import csv
import datetime as dt
from time import time
import os
plt.style.use('tableau-colorblind10')
fig = plt.figure()
ax = fig.add_subplot(111)

#input_file = os.path.expanduser("~/trolloscore.csv")
input_file = "this"

#data = pd.read_csv(input_file,names=['timestamp', 'todel', 'total'], header=None)
data = pd.read_csv(input_file,names=['timestamp', 'total', ], header=None)

#data = data[data.timestamp > int(time()) - 4 * 24 * 3600  ]


time = data["timestamp"].apply(dt.datetime.fromtimestamp)
delta = (-data["timestamp"].shift(1)+data["timestamp"])
print(data)
ax.plot(time[1:], (data["total"]/delta)[1:],label=['total',], linewidth=.75 , )
#ax.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
fig.autofmt_xdate()
ax.legend(loc='upper left')
plt.title("Nombre d'évènements posts par seconde sur bluesky")
plt.show()
