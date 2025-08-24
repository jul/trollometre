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

input_file = os.path.expanduser("~/trollometre.csv")
#input_file = "this"

data = pd.read_csv(input_file,names=['timestamp', 'posts', 'todel', 'spam', 'block', 'repost'], header=None)
#data = pd.read_csv(input_file,names=['timestamp', 'posts'])
data = data[data.timestamp > int(time()) - 4 * 24 * 3600  ]

time = data["timestamp"].apply(dt.datetime.fromtimestamp)
#from pdb import set_trace; set_trace()
delta = (-data["timestamp"].shift(1)+data["timestamp"])
delta[delta<300] = 300
print(delta.min())
#ax.plot(time[1:], data["posts"][1:]/delta[1:]) 

ax.stackplot(time[1:], (data["spam"]/delta)[1:], (data["block"]/delta)[1:], (data["posts"]/delta)[1:], labels=['spams', 'block', 'posts'])
ax.plot(time[1:], (data["repost"]/delta)[1:],label=['repost',], linewidth=.75 , )
#ax.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
fig.autofmt_xdate()
ax.legend(loc='upper left')
plt.title("Posts légitimes, Spams, Blocage de posts et Reposts par seconde en français")
plt.show()
