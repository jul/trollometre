
rrdcreate activitef.rrd --step 300 --start now-100d \
DS:posts:GAUGE:5m:0:24000 \
DS:spam:GAUGE:5m:0:24000 \
DS:block:GAUGE:5m:0:24000 \
DS:repost:GAUGE:5m:0:24000 \
DS:like:GAUGE:5m:0:24000 \
RRA:AVERAGE:0.5:5m:10d RRA:AVERAGE:0.5:50m:100d RRA:AVERAGE:0.5:500m:1000d
#rrdcreate activite.rrd --step 600 --start now-1d DS:posts:GAUGE:10m:0:24000 RRA:AVERAGE:0.5:10m:10d RRA:AVERAGE:0.5:100m:100d RRA:AVERAGE:0.5:1000m:1000d
