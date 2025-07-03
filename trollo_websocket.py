import asyncio
import websockets
#!/usr/bin/env python
# licence WTFPL 2.0 fait ce que tu veux avec sauf dire que tu l'as fait @jul 2025
#basé sur https://gist.github.com/stuartlangridge/20ffe860fee0ecc315d3878c1ea77c35

import json
import os
import sys
from atproto_client.models import get_or_create
from atproto import CAR, models, Client, client_utils
import requests
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message
from archery import mdict

from json import load, dumps

cfg = load(open(os.path.expanduser("~/.bluesky.json")))
handle = cfg["handle"]
password= cfg["password"]
def dbg(msg): sys.stderr.write(str(msg));sys.stderr.flush()



counter = mdict()
scorer_fr = mdict()
scorer = mdict()
seen = set()
at=dict()
evicted = set()
try:
    evicted = set(load(open(os.path.expanduser("~/.trollometre.json")))["evicted"])
    print(evicted)
except Exception as e:
    dbg(e)
i=0
j=0

class JSONExtra(json.JSONEncoder):
    """raw objects sometimes contain CID() objects, which
    seem to be references to something elsewhere in bluesky.
    So, we 'serialise' these as a string representation,
    which is a hack but whatevAAAAR"""
    def default(self, obj):
        try:
            result = json.JSONEncoder.default(self, obj)
            return result
        except:
            return repr(obj)


bsc = Client()
bsc.login(handle, password)
import re

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
pds_url = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"
k=0
async def listen_to_websocket():
    async with websockets.connect(pds_url) as websocket:
        global counter, evicted,i, bsc, j, k
        while True:
            try:
                message = await websocket.recv()
                message = json.loads(message)
                if not "commit" in message:
                    continue

                try:
                    if message["commit"]["operation"] == "create" and message["commit"]["cid"]:
                        toprint=""

                        uri = message["commit"]["record"
                            ]["reply"]["root"]["uri"]
                        toprint = raw = bsc.get_posts([uri])
                        post = raw = raw.posts[0]
                        if "market" in raw["author"].handle:
                            raise SpamError(f"market in {raw['author'].handle}")

                        #from pdb import set_trace;set_trace()
                        if post.record.langs and set(post.record.langs) & {'fr',}:
                            i+=1
                            dbg(".")
                            if uri not in evicted:
                                counter += mdict({uri : 1 })
                                scorer_fr[uri] = post.like_count+post.repost_count+post.quote_count+post.reply_count

                        else:
                            scorer[uri] = post.like_count+post.repost_count+post.quote_count+post.reply_count
                            dbg("+")
                            k+=1
                except IndexError:
                    dbg(toprint)
                    pass

                except KeyError:
                    pass

                except Exception as e:
                    dbg(e)

                if i> 150:
                    j+=1
                    i=0
                    mydict = ( scorer_fr, scorer, scorer_fr, scorer_fr, counter)[j%5]

                    for p in sorted({ k:v for k, v in mydict.items() if k not in evicted }.items(),
                        key=lambda x : x[1] )[::-1][0:1]:
                        dbg(p)
                        if p[1]>25:
                            try:
                                raw = bsc.get_posts([p[0]])
                                dbg(raw)
                                send_post(get_root_refs(p[0], f"[BOT] le niveau d'agitation ici est de : {p[1]}"))
                            except KeyError:
                                dbg("invalid post")
                                dbg(raw)
                            finally:
                                evicted |= {p[0],}
                                try:
                                    with open(os.path.expanduser("~/.trollometre.json"), "w") as f:
                                        json.dump(dict(evicted=list(evicted)), f)
                                except Exception as e:
                                    dbg(e)


            except websockets.ConnectionClosed as e:
                print(f"Connection closed: {e}")
                break
            except Exception as e:
                print(f"Error: {e}")

asyncio.get_event_loop().run_until_complete(listen_to_websocket())


