#!/usr/bin/env bash
perl -ane "/(\d+),(\d+),[^,]+,(\d+),(\d+)/ and \$1 > $(rrdinfo activite.rrd | perl -ane '/last_update = (\d+)/ and print $1' || echo 0 ) and print \"rrdtool update activite.rrd \$1:\$2:\$3:\$4\n\"" ~/trollometre.csv | bash  && \
rrdtool graph -w 500 -h 400  activite.png \
    -t "activité bluesky francophone en évènements posts par seconde" \
    --start now-1d --end now -l 0   \
    COMMENT:"          " COMMENT:"current " COMMENT:"average " COMMENT:"maximum " COMMENT:"minimum\l" \
    DEF:spamsa=activite.rrd:spam:AVERAGE CDEF:spam=spamsa,300,/ \
    AREA:spam#00FF00:"spams/s":STACK \
    VDEF:spamcur=spam,LAST GPRINT:spamcur:'%6.2lf %S' \
    VDEF:spamavg=spam,AVERAGE GPRINT:spamavg:'%6.2lf %S' \
    VDEF:spammax=spam,MAXIMUM GPRINT:spammax:'%6.2lf %S' \
    VDEF:spammin=spam,MINIMUM GPRINT:spammin:'%6.2lf %S\l' \
    DEF:blocka=activite.rrd:block:AVERAGE CDEF:block=blocka,300,/ \
    AREA:block#0000FF:"block/s":STACK \
    VDEF:blockcur=block,LAST GPRINT:blockcur:'%6.2lf %S' \
    VDEF:blockavg=block,AVERAGE GPRINT:blockavg:'%6.2lf %S' \
    VDEF:blockmax=spam,MAXIMUM GPRINT:blockmax:'%6.2lf %S' \
    VDEF:blockmin=block,MINIMUM GPRINT:blockmin:'%6.2lf %S\l' \
    DEF:postsa=activite.rrd:posts:AVERAGE CDEF:posts=postsa,300,/ \
    AREA:posts#FF0000:"posts/s":STACK \
    VDEF:postcur=posts,LAST GPRINT:postcur:'%6.2lf %S' \
    VDEF:postavg=posts,AVERAGE GPRINT:postavg:'%6.2lf %S' \
    VDEF:postmax=posts,MAXIMUM GPRINT:postmax:'%6.2lf %S' \
    VDEF:postmin=posts,MINIMUM GPRINT:postmin:'%6.2lf %S\l' \
    && qiv activite.png 

