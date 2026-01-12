#!/usr/bin/env bash
SINCE=${1:-1d}

perl -ane "/(\d+),(\d+),[^,]+,(\d+),(\d+),(\d+),(\d+)/ and \$1 > $(rrdinfo activitef.rrd | perl -ane '/last_update = (\d+)/ and print $1' || echo 0 ) and print \"rrdtool update activitef.rrd \$1:\$2:\$3:\$4:\$5:\$6\n\"" ~/trollometre.csv | bash  && \
rrdtool graph -w 700 -h 400  activite.png \
    -t "activité bluesky francophone en évènements posts par seconde" \
    --start now-$SINCE --end now -l 0 -u 1.2 -r   \
    COMMENT:"          " COMMENT:" current " COMMENT:"average " COMMENT:"maximum " COMMENT:"minimum\l" \
    DEF:spamsa=activitef.rrd:spam:AVERAGE CDEF:spam=spamsa,300,/ \
    AREA:spam#00FF00:"spams/s ":STACK \
    VDEF:spamcur=spam,LAST GPRINT:spamcur:'%6.2lf %s' \
    VDEF:spamavg=spam,AVERAGE GPRINT:spamavg:'%6.2lf %s' \
    VDEF:spammax=spam,MAXIMUM GPRINT:spammax:'%6.2lf %s' \
    VDEF:spammin=spam,MINIMUM GPRINT:spammin:'%6.2lf %s\l' \
    DEF:blocka=activitef.rrd:block:AVERAGE CDEF:block=blocka,300,/ \
    AREA:block#0000FF:"block/s ":STACK \
    VDEF:blockcur=block,LAST GPRINT:blockcur:'%6.2lf %s' \
    VDEF:blockavg=block,AVERAGE GPRINT:blockavg:'%6.2lf %s' \
    VDEF:blockmax=spam,MAXIMUM GPRINT:blockmax:'%6.2lf %s' \
    VDEF:blockmin=block,MINIMUM GPRINT:blockmin:'%6.2lf %s\l' \
    DEF:postsa=activitef.rrd:posts:AVERAGE CDEF:posts=postsa,300,/ \
    AREA:posts#FF0000:"posts/s ":STACK \
    VDEF:postcur=posts,LAST GPRINT:postcur:'%6.2lf %s' \
    VDEF:postavg=posts,AVERAGE GPRINT:postavg:'%6.2lf %s' \
    VDEF:postmax=posts,MAXIMUM GPRINT:postmax:'%6.2lf %s' \
    VDEF:postmin=posts,MINIMUM GPRINT:postmin:'%6.2lf %s\l' \
    DEF:reposta=activitef.rrd:repost:AVERAGE CDEF:repost=reposta,300,/ \
    LINE2:repost#000000:"repost/s" \
    VDEF:repostcur=repost,LAST GPRINT:repostcur:'%6.2lf %s' \
    VDEF:repostavg=repost,AVERAGE GPRINT:repostavg:'%6.2lf %s' \
    VDEF:repostmax=repost,MAXIMUM GPRINT:repostmax:'%6.2lf %s' \
    VDEF:repostmin=repost,MINIMUM GPRINT:repostmin:'%6.2lf %s\l' \
    DEF:likea=activitef.rrd:like:AVERAGE CDEF:like=likea,300,/ \
    LINE2:like#606060:"like/s  " \
    VDEF:likecur=like,LAST GPRINT:likecur:'%6.2lf %s' \
    VDEF:likeavg=like,AVERAGE GPRINT:likeavg:'%6.2lf %s' \
    VDEF:likemax=like,MAXIMUM GPRINT:likemax:'%6.2lf %s' \
    VDEF:likemin=like,MINIMUM GPRINT:likemin:'%6.2lf %s\l' \
    && qiv activite.png 

