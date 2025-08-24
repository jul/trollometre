#!/usr/bin/env python
# licence WTFPL 2.0 fait ce que tu veux avec sauf dire que tu l'as fait @jul 2025
#basé sur https://gist.github.com/stuartlangridge/20ffe860fee0ecc315d3878c1ea77c35

import os
import sys
from atproto_client.models import get_or_create
from atproto import CAR, models, Client, client_utils
import requests
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message
from archery import mdict, vdict
from time import time, sleep
import re
from json import load, dumps, loads, dump
import psycopg2 as sq

import asyncio
from websockets.asyncio.server import serve
from multiprocessing import Process, Queue
q= Queue()



con = sq.connect(dbname="trollo", user="jul")
cur = con.cursor()


cfg = load(open(os.path.expanduser("~/.bluesky.json")))
handle = cfg["handle"]
password= cfg["password"]
def dbg(msg): sys.stderr.write(str(msg));sys.stderr.flush()

path_to_config= os.path.expanduser("~/.trollometre.vect.json")

settings = load(open(path_to_config))
training_set = vdict(settings["ham_spam"])
blacklist = set(settings["blacklist"])

def save_settings():
    global blacklist, training_set
    with open(path_to_config, 'w') as f:
        dump(dict(ham_spam = training_set,blacklist=list(blacklist)), f)



import spacy
from langdetect import detect
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
stemmer = SnowballStemmer(language='french')

stop_words = set(stopwords.words('french')) | {',', ':', '#', '-', '\n', '\n\n', '.', '!', '(', ')',  }

nlp = spacy.load("fr_core_news_sm")
def fcounter(list_of_words):
    res = vdict({})
    for i in list_of_words:
        res += vdict({ i : 1 })
    return res

print(fcounter(['a','a', 'b']))
def return_token_sent(sentence):
    # Tokeniser la phrase
    doc = nlp(sentence)
    # Retourner le texte de chaque phrase
    return [X.text for X in doc.sents]

def return_stem(sentence):
    doc = nlp(sentence)
    return [stemmer.stem(X.text) for X in doc if X.text not in stop_words]

from emoji import is_emoji
def parse(post):
    global blacklist
    text = post["record"]["text"]
    #from pdb import set_trace; set_trace()
    if post["labels"]:
        for i in post["labels"]:
            if i["val"] == "porn":
                blacklist |= set([post["author"]["handle"]])
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
        res1 = map(return_stem, return_token_sent(text))
        res2 = map(fcounter, res1)
        res3 = sum(res2, vdict())
        print("lol")
        print(res3)
        res = vdict(res3)
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


def is_a_spam(post):
    vtext = parse(post)
    if "SPAM" in vtext or not vtext:
        dbg("SPAM in vtext?")
        dbg("SPAM" in vtext)
        return True
    dbg(f"""c1 : {vtext.dot(training_set["spam"])}""")
    dbg(f"""c2 {vtext.dot(training_set["ham"])}""")
    return vtext.dot(training_set["spam"]) > vtext.dot(training_set["ham"])




counter = mdict()
scorer_fr = mdict()
scorer = mdict()
seen = set()
at=dict()
evicted = set()
try:
    cur.execute("select uri from posts")
    for l in cur.fetchall():
        evicted |= set(l)

    print(evicted)
except Exception as e:
    dbg(e)
nb_fr=0
nb_spam=0
j=0


client = FirehoseSubscribeReposClient()

bsc = Client()
bsc.login(handle, password)


def repost_root_refs(parent_uri: str) :
    global bsc
    print(parent_uri.split("/"))
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

def get_root_refs(parent_uri: str, text : str) :
    global bsc
    print(parent_uri.split("/"))
    _,_,did,collection, rkey = parent_uri.split("/")
    print(f" {did} {collection} {rkey}")
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


def send_post(payload):
    global bsc
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
last_step=time()
def on_message_handler(message):
    commit = parse_subscribe_repos_message(message)
    global counter, evicted,nb_fr,nb_repost_fr, nb_spam, bsc, j, nb_not_fr, last_step, last, blacklist, nb_block
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return
    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
        if op.action in ["create"] and op.cid:
            raw = car.blocks.get(op.cid)
            cooked = get_or_create(raw, strict=False)

            if cooked and cooked.py_type in { "app.bsky.feed.repost" }:
### DRY
                toprint=""
                try:
                    uri = raw["subject"]["uri"]
                    toprint = raw = bsc.get_posts([uri])
                    post = raw = raw.posts[0]
                    if "market" in raw["author"]["handle"] or "yuno-wov" in raw["author"]["handle"] or "vulve" in raw["author"]["handle"] or raw["author"]["handle"] in blacklist:
                        raise SpamError(f"spam in {raw['author'].handle}")

                    #from pdb import set_trace;set_trace()
                    if post.record.langs and set(post.record.langs) & {'fr',}:
                        nb_repost_fr+=1
                        dbg("r")
                        if uri not in evicted:
                            counter += mdict({uri : 1 })
                            scorer_fr[uri] = post.like_count+post.repost_count+post.quote_count+post.reply_count
                            last=dict({ uri : post.like_count+post.repost_count+post.quote_count+post.reply_count})

                    else:
                        scorer[uri] = post.like_count+post.repost_count+post.quote_count+post.reply_count

                except IndexError:
                    dbg("b")
                    nb_repost_fr+=1
                    pass

                except KeyError:
                    print(raw)
                    pass
                except SpamError:
                    dbg('%')
                    nb_repost_fr+=1

                except Exception as e:
                    dbg(e)
            if cooked and cooked.py_type in { "app.bsky.feed.post" }:
### DRY
                toprint=""
                try:
                    uri = raw["reply"]["root"]["uri"]
                    toprint = raw = bsc.get_posts([uri])
                    post = raw = raw.posts[0]
                    if "market" in raw["author"]["handle"] or "yuno-wov" in raw["author"]["handle"] or "vulve" in raw["author"]["handle"] or raw["author"]["handle"] in blacklist:
                        raise SpamError(f"spam in {raw['author'].handle}")

                    #from pdb import set_trace;set_trace()
                    if post.record.langs and set(post.record.langs) & {'fr',}:
                        nb_fr+=1
                        dbg(".")
                        if uri not in evicted:
                            counter += mdict({uri : 1 })
                            scorer_fr[uri] = post.like_count+post.repost_count+post.quote_count+post.reply_count
                            last=dict({ uri : post.like_count+post.repost_count+post.quote_count+post.reply_count})

                    else:
                        scorer[uri] = post.like_count+post.repost_count+post.quote_count+post.reply_count
                        nb_not_fr+=1
                except IndexError:

                    dbg("-")
                    nb_block+=1
                    pass

                except KeyError:
                    pass
                except SpamError:
                    nb_spam+=1
                    dbg('*')

                except Exception as e:
                    dbg(e)
                # TIME
                if time() - last_step > 300:
                    j+=1
                    dbg(nb_fr+nb_repost_fr)
                    with open(os.path.expanduser("~/trollometre.csv"), "a") as f:
                        f.write(f"{int(time())},{nb_fr},{nb_not_fr},{nb_spam},{nb_block},{nb_repost_fr}\n")
                    save_settings()
                    nb_fr=0
                    nb_spam=0
                    nb_block=0
                    nb_not_fr=0
                    nb_repost_fr=0
                    mydict = ( scorer_fr, scorer_fr, scorer_fr, scorer_fr, scorer_fr, scorer_fr, scorer_fr,)[j%7]
                    picked = False
                    while not picked and { k:v for k, v in mydict.items() if k not in evicted }:

                        for p in sorted({ k:v for k, v in mydict.items() if k not in evicted }.items(),
                            key=lambda x : x[1] )[::-1][0:1]:
## SCORE
                            if mydict[p[0]]<100:
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
                                maybe_spam = is_a_spam(post)
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
                                    repost_root_refs(p[0])
                                    dbg("sent")
                            except KeyError:
                                dbg("invalid post")
                                dbg(raw)
                            finally:
                                evicted |= {p[0],}
                                #try:
                                #    with open(os.path.expanduser("~/.trollometre.json"), "w") as f:
                                #        json.dump(dict(evicted=list(evicted)), f)
                                #except Exception as e:
                                #    dbg(e)

                    last_step = time()

def websocket_server(q):
    async def echo(websocket):
        while message:=q.get():
            await websocket.send(message)

    async def main():
        async with serve(echo, "0.0.0.0", 8765) as server:
            await server.serve_forever()

    asyncio.run(main())

p = Process(target=websocket_server, args =(q,))
p.start()

while [ 1 ]:
    try:
        client.start(on_message_handler)
    except:
        pass

p.join()
