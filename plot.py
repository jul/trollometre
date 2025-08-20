import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import csv
import datetime as dt
from time import time
import os

fig = plt.figure()
ax = fig.add_subplot(111)

input_file = os.path.expanduser("~/trollometre.csv")
#input_file = "this"

data = pd.read_csv(input_file,names=['timestamp', 'posts', 'todel', 'spam', 'block'], header=None)
#data = pd.read_csv(input_file,names=['timestamp', 'posts'])
data = data[data.timestamp > int(time()) - 7 *  24 * 3600  ]

time = data["timestamp"].apply(dt.datetime.fromtimestamp)
#ax.stackplot(time, data["posts"], labels=[ 'posts'])
#ax.stackplot(time, data["block"], labels=[ 'block'])
ax.stackplot(time, data["spam"], data["block"], data["posts"], labels=['spams', 'block', 'posts'])
#ax.xaxis.set_major_formatter(mdates.DateFormatter('%H-%M-%S'))
fig.autofmt_xdate()
ax.legend(loc='upper left')
#msft.plot(0, [ 1, 3, 4])
plt.show()
