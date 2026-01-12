import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import csv
import datetime as dt
from time import time
import os
import psycopg2 as sq
con = sq.connect(dbname="trollo", user="jul")
cur = con.cursor()
plt.style.use('tableau-colorblind10')
fig = plt.figure()
ax = fig.add_subplot(111)

res = cur.execute("""
    with 
        date as  (select * from generate_series(NOW()-interval '15d', NOW() , interval '20m') as d)
    select
        date.d as timestamp,
        percentile_cont(0.33) WITHIN GROUP ( order by score) as tier,
        percentile_cont(0.5) WITHIN GROUP ( order by score) as med,
        percentile_cont(0.66)  WITHIN GROUP ( order by score) as up_tier,
        sum(score)/count(*) as average,
        count(*) from posts, date
    where maybe_spam is false and is_spam is not true and
    created_at BETWEEN  date.d::timestamp - interval '1d' and date.d
    group by date.d order by date.d asc;

""")

data = pd.DataFrame(cur.fetchall())
data.columns = [ "timestamp", "tier", "median", "up_tier", "average", "count" ]
time = data["timestamp"]
#delta = (-data["timestamp"].shift(1)+data["timestamp"])
ax.plot(time, data["tier"], label="33%ile")
ax.plot(time, data["up_tier"], label="66%ile")
ax.plot(time, data["median"], label="median")
ax.plot(time, data["average"], label="average")
ax.plot(time, data["count"], label="count")
#ax.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
fig.autofmt_xdate()
ax.legend(loc='upper left')
plt.title("Évolution du score sur une fenêtre mouvante de 24h sur ces 15 derniers jours")
plt.show()
