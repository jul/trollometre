import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import psycopg2 as sq
import csv
import datetime as dt
from time import time
import os
plt.style.use('tableau-colorblind10')
fig = plt.figure()
ax = fig.add_subplot(111)

nb_day = 40
con = sq.connect(dbname="trollo", user="jul")
cur = con.cursor()
res = cur.execute(f"""
    with 
        date as  (select * from generate_series(NOW()-interval '{nb_day}d', NOW() , interval '20m') as d)
    select
        date.d as timestamp,
        percentile_cont(0.) WITHIN GROUP ( order by score) as min,
        percentile_cont(0.5) WITHIN GROUP ( order by score) as med,
        percentile_cont(0.66)  WITHIN GROUP ( order by score) as up_tier,
        sum(score)/count(*) as average,
        count(*) from posts, date
    where maybe_spam is false and is_spam is not true and
    created_at BETWEEN  date.d::timestamp - interval '24h' and date.d
    group by date.d order by date.d asc;

""")

data2 = pd.DataFrame(cur.fetchall())
data2.columns = [ "timestamp", "min", "median", "up_tier", "average", "count" ]
input_file = os.path.expanduser("~/trolloscore.csv")
#input_file = "this"
data = pd.read_csv(input_file,names=['timestamp', 'score', 'cumul'], header=None)
#data = pd.read_csv(input_file,names=['timestamp', 'posts'])

data = data[data.timestamp > int(time()) - nb_day * 24 * 3600  ]
time2 = data2.timestamp.apply(lambda e : e.timestamp() )
data2 = data2[time2 > int(time()) - nb_day * 24 * 3600  ]

time = data["timestamp"].apply(dt.datetime.fromtimestamp)
#from pdb import set_trace; set_trace()
ax.plot(time, data["score"], label = ["score passe haut"])
ax.plot(time, data["cumul"], label = ["repost des 24 dernières heures"]) 
ax.plot(data2.timestamp, data2["median"], label = [ "score median observé sur 24h "])
ax.plot(data2.timestamp, data2["average"], label = [ "score moyen observé sur 24h"])
from time import time
plt.axhline( 105, color= "green")
plt.axhline( 115, color= "green")
#plt.axline([time2[0], 115], [time2[2], 115])
#ax.plot(time[1:], (data["repost"]/delta)[1:],label=['repost',], linewidth=.75 , )
#ax.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
fig.autofmt_xdate()
ax.legend(loc='upper left')
plt.title("Score du trollomètre en fonction du temps")
plt.show()
