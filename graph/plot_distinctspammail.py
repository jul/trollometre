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
        date as  (select * from generate_series(NOW()-interval '25d', NOW() , interval '1d') as d)
select date.d::date, count(distinct(post::json#>'{author,handle}')::text) 
from posts, date 
where created_at > NOW() - interval '25d' and created_at < date.d + interval '1d' and maybe_spam is true group by date.d;


""")

data = pd.DataFrame(cur.fetchall())
data.columns = [ "date", "spamers" ]
#delta = (-data["timestamp"].shift(1)+data["timestamp"])
ax.plot(data.date, data["spamers"], label="spammers")
#ax.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
fig.autofmt_xdate()
ax.legend(loc='upper left')
plt.title("Évolution du nombre de spammeurs avec le temps")
plt.show()
