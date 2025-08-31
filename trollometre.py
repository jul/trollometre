#!/usr/bin/env python
# licence WTFPL 2.0 fait ce que tu veux avec sauf dire que tu l'as fait @jul 2025
# https://github.com/MarshalX/atproto/blob/main/examples/firehose/process_commits.py
from filelock import FileLock
import os
import sys
import psycopg2 as sq
from atproto_client.models import get_or_create
import signal
import requests

from atproto_firehose import FirehoseSubscribeReposClient
from atproto import models
from archery import mdict, vdict
from time import time, sleep
import re
from json import load, dumps, loads, dump
# import trio as asyncio
#import asyncio
from websockets.asyncio.server import serve
from multiprocessing import Process, Queue
import multiprocessing
q= Queue()

lock_config = FileLock("config_trollo.txt")
lock_out = FileLock("config_stdout.txt")
lock_vect = FileLock("config_vect.txt")


cfg = load(open(os.path.expanduser("~/.bluesky.json")))
handle = cfg["handle"]
password= cfg["password"]
def dbg(msg):
    sys.stdout.write(str(msg));sys.stdout.flush()




import spacy
from langdetect import detect
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
stemmer = SnowballStemmer(language='french')

stop_words = set(stopwords.words('french')) | {',', ':', '#', '-', '\n', '\n\n', '.', '!', '(', ')',  }


path_to_config= os.path.expanduser("~/.trollometre.vect.json")

settings = load(open(path_to_config))
training_set = vdict(settings["ham_spam"])
blacklist = set(settings["blacklist"])
score = multiprocessing.Value('i',settings.get("score",125))

def is_a_spam(post, blacklist):
    vtext = parse(post, blacklist)
    if "SPAM" in vtext or not vtext:
        dbg("SPAM in vtext?")
        dbg("SPAM" in vtext)
        return True
    dbg(f"""c1 : {vtext.dot(training_set["spam"])}""")
    dbg(f"""c2 {vtext.dot(training_set["ham"])}""")
    return vtext.dot(training_set["spam"]) > vtext.dot(training_set["ham"])


def save_settings(blacklist=blacklist):
    with open(path_to_config, 'w') as f:
        dbg("saving..")
        dump(dict(ham_spam = training_set,blacklist=list(blacklist), score=score.value), f)

def update_black_list(local_blacklist):
    with lock_vect:
        dbg("updateing bl")
        settings = load(open(path_to_config))
        training_set = vdict(settings["ham_spam"])
        dbg(f"lb{len(local_blacklist)}")
        blacklist = set(settings["blacklist"]) | local_blacklist
        dbg(f"lb{len(blacklist)}")
        save_settings(blacklist)
        return blacklist
def update_score():
    with lock_vect:
        settings = load(open(path_to_config))
        settings["score"] = score.value
        with open(path_to_config, 'w') as f:
            dbg("saving..")
            dump(settings, f)


def parse(post, blacklist):
    text = post["record"]["text"]
    #from pdb import set_trace; set_trace()
    if post["labels"]:
        for i in post["labels"]:
            if i["val"] == "porn":
                dbg(f"lb{len(blacklist)}")
                blacklist |= {post["author"]["handle"], }
                dbg(f"lb{len(blacklist)}")

                dbg("UPBL")
                dbg(f"adding { post["author"]["handle"]}")
                blacklist = update_black_list(blacklist)

                dbg("is porn")
                return vdict(SPAM=1)
    if post["embed"]:
        if "images" in post["embed"]:
            for i in post["embed"]["images"]:
                if not i["alt"]:
                    text += " NO_ALT"
                text += " " + i["alt"]
        if "external" in post["embed"]:
            text += " " + post["embed"]["external"]["title"]
            text += " " + post["embed"]["external"]["description"]



    res = vdict()
    try:
        if not post:
            dbg("not post")
            return vdict(SPAM=1)
        if not detect(text) in {  "fr", "ca" }:
            dbg("dtec" + detect(text))
            return vdict()
    except Exception as e:
        dbg(e)
        return res

    if text:
        res = sum(map(fcounter,map(return_stem, return_token_sent(text))), vdict())
        dbg(res)
        if len(res) < 10:
            dbg("too short")
            return vdict(SPAM = 1)
    for w in text.split():
        if w.startswith("#") or w.startswith("@"):
            res+=vdict({w:1 })
            if w.lower() in { "#nfsw",  "#vendrediseins", "#jeudipussy", "@ma-queue.com" , "@mon-cul.com", '#respectauxcréateurs' } or 'cum' in w.lower() or "orgasm" in w.lower() or "porn" in w.lower() or "coquin" in w.lower() or "salop" in w.lower() or "adult" in w.lower() or w.lower() in blacklist:
                res+=vdict(SPAM=1)


    for c in text:
        if is_emoji(c):
            res+=vdict({c:1 })
    return res



nlp = spacy.load("fr_core_news_sm")
def fcounter(list_of_words):
    res = vdict({})
    for i in list_of_words:
        res += vdict({ i : 1 })
    return res

def return_token_sent(sentence):
    # Tokeniser la phrase
    doc = nlp(sentence)
    # Retourner le texte de chaque phrase
    return [X.text for X in doc.sents]

def return_stem(sentence):
    doc = nlp(sentence)
    return [stemmer.stem(X.text) for X in doc if X.text not in stop_words]

from emoji import is_emoji



counter = mdict()
scorer_fr = mdict()
scorer = mdict()
seen = set()
at=dict()
nb_fr=0
nb_spam=0
j=0




def repost_root_refs(bsc,parent_uri: str) :
    _,_,did,collection, rkey = parent_uri.split("/")
    pds_url = "https://bsky.social"
    resp = requests.get(
        pds_url + "/xrpc/com.atproto.repo.getRecord",
        params=dict(
            repo = did,
            collection = collection,
            rkey = rkey,
       )
    )
    resp.raise_for_status()
    parent = resp.json()
    root = parent
    bsc.repost(root["uri"], root["cid"])

def get_root_refs(bsc, parent_uri: str, text : str) :
    _,_,did,collection, rkey = parent_uri.split("/")
    pds_url = "https://bsky.social"
    resp = requests.get(
        pds_url + "/xrpc/com.atproto.repo.getRecord",
        params=dict(
            repo = did,
            collection = collection,
            rkey = rkey,
       )
    )
    resp.raise_for_status()
    parent = resp.json()
    root = parent

    return {
          "$type": "app.bsky.feed.post",
          "text": text,
          "createdAt": bsc.get_current_time_iso(),
          "embed": {
          "$type": "app.bsky.embed.record",
          "record": {
            "uri": root["uri"],
            "cid": root["cid"],
            }
          }
        }




def send_post(bsc, payload):
    pds_url = "https://bsky.social"
    resp = requests.post(
        pds_url + "/xrpc/com.atproto.repo.createRecord",
        headers=bsc._get_access_auth_headers(),
        json=dict(
            repo=bsc.me.did,
            collection = "app.bsky.feed.post",
            record = payload )
    )
    resp.raise_for_status()

def get_firehose_params(cursor_value: multiprocessing.Value) -> models.ComAtprotoSyncSubscribeRepos.Params:
    return models.ComAtprotoSyncSubscribeRepos.Params(cursor=cursor_value.value)

# all of this undocumented horseshit is based on cargo-culting the bollocks out of
# https://github.com/MarshalX/atproto/blob/main/examples/firehose/sub_repos.py
# and
# https://github.com/MarshalX/bluesky-feed-generator/blob/main/server/data_stream.py
class SpamError(Exception):
    pass
nb_not_fr=0
nb_block = 0
nb_repost_fr=0
last= dict()
from atproto import CAR, models, Client, client_utils, AtUri

bsc = Client()
bsc.login(handle, password)


def worker_main(message_queue, mesure_queue, cursor,score):
    global bsc



    last_step=time() - (id(multiprocessing.current_process().name) %120) + 60
    dbg(f'time={last_step}/')
    from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message

    dbg("stated")
    # SCORE
    con = sq.connect(dbname="trollo", user="jul")
    cur = con.cursor()
    evicted = set()
    cur.execute("select uri from posts")
    for l in cur.fetchall():
        evicted |= set(l)


    path_to_config= os.path.expanduser("~/.trollometre.vect.json")

    settings = load(open(path_to_config))
    training_set = vdict(settings["ham_spam"])
    blacklist = set(settings["blacklist"])
    while message := message_queue.get():
        commit = parse_subscribe_repos_message(message)
        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            continue

        if commit.seq % 20 == 0:
            cursor.value = commit.seq

        if not commit.blocks:
            continue
        commit = parse_subscribe_repos_message(message)
        mesure = mdict()
        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            debug("wtf")
            return
        car = CAR.from_bytes(commit.blocks)

        for op in commit.ops:
            if op.action in ["create"] and op.cid:
                raw = car.blocks.get(op.cid)
                cooked = get_or_create(raw, strict=False)
                root_uri = AtUri.from_str(f'at://{commit.repo}/{op.path}')

#
                if cooked and cooked.py_type in { "app.bsky.feed.repost","app.bsky.feed.like" }:
                    try:
                        uri = raw["subject"]["uri"]
                        if uri in scorer_fr:
                            scorer_fr[uri] += 1
                            dbg("r" if cooked.py_type in { "app.bsky.feed.repost" } else "l")
                            mesure+=mdict({ "repost" if cooked.py_type in { "app.bsky.feed.repost" } else "like" : 1 })

                    except KeyError:
                        dbg(raw)
                        pass
                    except SpamError:
                        dbg('%')
                        mesure+=mdict(repost=1)

                    except Exception as e:
                        dbg(e)

                if cooked and cooked.py_type in { "app.bsky.feed.post" }:
                    if "langs" in raw and not set(raw["langs"]) & {'fr',}:
                        mesure+=mdict(nb_not_fr=1)
                        continue

                    toprint=""
                    try:
                        uri = raw["reply"]["root"]["uri"]
                        toprint = raw
                        if root_uri != uri:
                            toprint = raw = bsc.get_posts([uri])

                        post = raw = raw.posts[0]
                        if "market" in raw["author"]["handle"] or "yuno-wov" in raw["author"]["handle"] or "vulve" in raw["author"]["handle"] or raw["author"]["handle"] in blacklist:
                            raise SpamError(f"spam in {raw['author'].handle}")

                        #from pdb import set_trace;set_trace()
                        if post.record.langs and set(post.record.langs) & {'fr',}:
                            mesure+=mdict(nb_fr=1)
                            dbg(".")
                            if uri not in evicted:
                                scorer_fr[uri] = post.like_count+post.repost_count+post.quote_count+post.reply_count
                                last=dict({ uri : post.like_count+post.repost_count+post.quote_count+post.reply_count})

                        else:
                            scorer[uri] = post.like_count+post.repost_count+post.quote_count+post.reply_count
                            # mesure+=mdict(nb_not_fr=1)

                    except IndexError:

                        dbg("-")
                        mesure+=mdict(nb_block=1)
                        pass

                    except KeyError:
                        pass
                    except SpamError:
                        mesure+=mdict(nb_spam=1)
                        dbg('*')
                    except Exception as e:
                        dbg(e)
        if mesure:
            mesure_queue.put(mesure)
        # TIME
        if time() - last_step > 120:
            dbg("pick")
            last_step = time()

            #dbg(nb_fr+nb_repost_fr)
            #with open(os.path.expanduser("~/trollometre.csv"), "a") as f:
            #    f.write(f"{int(time())},{nb_fr},{nb_not_fr},{nb_spam},{nb_block},{nb_repost_fr}\n")
            nb_fr=0
            nb_spam=0
            nb_block=0
            nb_not_fr=0
            nb_repost_fr=0
            mydict = ( scorer_fr, scorer_fr, scorer_fr, scorer_fr, scorer_fr, scorer_fr, scorer_fr,)[j%7]
            picked = False
            evicted = set()

            cur.execute("select uri from posts")
            for l in cur.fetchall():
                evicted |= set(l)

            while not picked and { k:v for k, v in mydict.items() if k not in evicted }:

                for p in sorted({ k:v for k, v in mydict.items() if k not in evicted }.items(),
                    key=lambda x : x[1] )[::-1][0:1]:
## SCORE
                    if mydict[p[0]]<score.value:

                        picked = True
                        break


                    dbg(p)
                    try:

                        raw = bsc.get_posts([p[0]])
                        _,_,did,collection, rkey = p[0].split("/")
                        url = f"https://bsky.app/profile/{did}/post/{rkey}"
                        dbg("\n")

                        dbg(f"{url}\n")
                        dbg("\n")
                        post = raw.posts[0]
                        maybe_spam = is_a_spam(post, blacklist)
                        json = post.model_dump_json()

                        #dbg(dumps(loads(raw.posts[0].json()),indent=4))
                        try:
                            cur.execute("INSERT INTO posts (uri, url, post, score, maybe_spam) VALUES(%s, %s, %s, %s, %s)",
                                [ p[0], url, json, post.like_count+post.repost_count+post.quote_count+post.reply_count, maybe_spam])
                        except:
                            con.rollback()
                        finally:
                            con.commit()
                        q.put(json)


                        if maybe_spam == False:
                            picked = True
                            dbg("before send")
                            #send_post(get_root_refs(p[0], f"[BOT] le niveau d'agitation ici est de : {p[1]}"))
                            repost_root_refs(bsc,p[0])
                            dbg("sent")

                    except KeyError:
                        dbg("invalid post")
                        dbg(raw)
                    finally:
                        evicted |= {p[0],}
                        try:
                            with lock_config:
                                with open(os.path.expanduser("~/.trollometre.json"), "w") as f:
                                    json.dump(dict(evicted=list(evicted)), f)
                        except Exception as e:
                            dbg(e)


import asyncio
def websocket_server(q):
    async def echo(websocket):
        while message:=q.get():
            await websocket.send(message)#
    async def main():
        async with serve(echo, "0.0.0.0", 8765) as server:
            await server.serve_forever()

    asyncio.run(main())

def mesure_collector(mesure_queue):

    global all_mesure
    all_mesure=mdict(nb_fr=0, nb_not_fr=0, nb_spam=0, nb_block=0, nb_repost_fr=0,repost=0, like=0)

    def handler(signum, stack):
        signal.alarm(300)
        global all_mesure
        print(all_mesure, flush=True)

        with open(os.path.expanduser("~/trollometre.csv"), "a") as f:
            f.write(f"{int(time())},{all_mesure["nb_fr"]},{all_mesure["nb_not_fr"]},{all_mesure["nb_spam"]},{all_mesure["nb_block"]},{all_mesure["repost"]},{all_mesure["like"]}\n")
        dbg(f"({all_mesure["repost"]+all_mesure["nb_fr"]+all_mesure["like"]})")
        all_mesure=mdict(nb_fr=0, nb_not_fr=0, nb_spam=0, nb_block=0, nb_repost_fr=0,repost=0, like=0)


    signal.signal(signal.SIGALRM, handler)
    signal.alarm(295)
    print("started mesure collector")
    while mesure := mesure_queue.get():
        all_mesure += mdict(mesure)





mesure_queue = multiprocessing.Queue()


p = Process(target=websocket_server, args =(q,))
p.start()


workers_count = 4 # multiprocessing.cpu_count() * 2 - 1
print(f"{workers_count} process started")
message_queue = multiprocessing.Queue(maxsize=1000)
start_cursor = None
params = None
cursor = multiprocessing.Value('i', 0)
if start_cursor is not None:
    cursor = multiprocessing.Value('i', start_cursor)
    params = get_firehose_params(cursor)


def score_setter(score):
    con = sq.connect(dbname="trollo", user="jul")
    cur = con.cursor()
    def score_handler(signum, stack):
        signal.alarm(1200)
        cur.execute("select statement_timestamp() - interval '1d', statement_timestamp()")
        yesterday, now = cur.fetchone()
        dbg(f"{now}::{yesterday}")

        cur.execute("select count(*) from posts where maybe_spam is false and is_spam is not true and  created_at BETWEEN  statement_timestamp() - interval '1d' AND statement_timestamp()")
        in_last_day = cur.fetchone()[0]
        dbg(f'in_last_day {in_last_day}')
        if in_last_day > 115:
            score.value += 1
        if in_last_day < 105:
            score.value -= 1
        update_score()
        with open(os.path.expanduser("~/trolloscore.csv"), "a") as f:
            f.write(f"{int(time())},{score.value},{in_last_day}\n")
        dbg(f"//SCORE {score.value}")
    signal.signal(signal.SIGALRM, score_handler)
    signal.alarm(1200)
    while 1:
        sleep(100)

ss = Process(target=score_setter, args=(score,))
ss.start()
client = FirehoseSubscribeReposClient(params)

pool = multiprocessing.Pool(workers_count, worker_main, ( message_queue,mesure_queue, cursor, score))

mc = Process(target=mesure_collector, args =(mesure_queue,))
mc.start()

def dispatcher(message):
    if cursor.value:
    # we are using updating the cursor state here because of multiprocessing
    # typically you can call client.update_params() directly on commit processing
        client.update_params(get_firehose_params(cursor))

    message_queue.put(message)




while [ 1 ]:
    try:
        client.start(dispatcher)
    except Exception as e:
        print(e)
        pass
p.terminate()
p.join()
pool.terminate()
pool.join()
mc.terminate()
mc.join()
ss.terminate()
ss.join()
