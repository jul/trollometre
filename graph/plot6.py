import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import csv
import datetime as dt
from time import time
import os
import psycopg2 as sq
from sys import argv

what = argv[1]
what2 = argv[2]

con = sq.connect(dbname="trollo", user="jul")
cur = con.cursor()
plt.style.use('tableau-colorblind10')
fig = plt.figure()
ax = fig.add_subplot(111)
nbday=250

res = cur.execute(f"""
    with 
        date as  (select * from generate_series(NOW()-interval '{nbday}d', NOW() , interval '20m') as d)
    select
        date.d as timestamp,
        percentile_cont(0.33) WITHIN GROUP ( order by score) as tier,
        percentile_cont(0.5) WITHIN GROUP ( order by score) as med,
        percentile_cont(0.66)  WITHIN GROUP ( order by score) as up_tier,
        sum(score)/count(*) as average,
        count(*) from posts, date
    where is_spam is not true and maybe_spam is false and post::text ILIKE '%{what}%' and
    created_at BETWEEN  date.d::timestamp - interval '1d' and date.d
    group by date.d order by date.d asc;

""")

data = pd.DataFrame(cur.fetchall())
data.columns = [ "timestamp", "tier", "median", "up_tier", "average", "count" ]
time = data["timestamp"]
#delta = (-data["timestamp"].shift(1)+data["timestamp"])
#ax.plot(time, data["tier"], label="33%ile")
#ax.plot(time, data["up_tier"], label="66%ile")
#ax.plot(time, data["median"], label="median")

ax.plot(time, data["average"], label=f"score moyen des posts «{what}»")
res = cur.execute(f"""
    with 
        date as  (select * from generate_series(NOW()-interval '{nbday}d', NOW() , interval '20m') as d)
    select
        date.d as timestamp,
        percentile_cont(0.33) WITHIN GROUP ( order by score) as tier,
        percentile_cont(0.5) WITHIN GROUP ( order by score) as med,
        percentile_cont(0.66)  WITHIN GROUP ( order by score) as up_tier,
        sum(score)/count(*) as average,
        count(*) from posts, date
    where is_spam is not true and maybe_spam is false and post::text ILIKE '%{what2}%' and
    created_at BETWEEN  date.d::timestamp - interval '1d' and date.d
    group by date.d order by date.d asc;

""")

data = pd.DataFrame(cur.fetchall())
data.columns = [ "timestamp", "tier", "median", "up_tier", "average", "count" ]
time = data["timestamp"]
#ax.plot(time, data["count"], label="count")
#ax.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
ax.plot(time, data["average"], label=f"score moyen des posts «{what2}»")
fig.autofmt_xdate()
ax.legend(loc='upper left')
plt.title(f"Évolution des scores pour les mots «{what}» et «{what2}» sur les {nbday} derniers jours")
plt.show()
