#!/usr/bin/env python
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
def dbg(msg): sys.stderr.write(repr(msg));sys.stderr.flush()

counter = mdict()
seen = set([])
at=dict()
evicted = set([])
i=0

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

client = FirehoseSubscribeReposClient()

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

def on_message_handler(message):
    commit = parse_subscribe_repos_message(message)
    global counter, evicted,i, bsc
    if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
        return
    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
        if op.action in ["create"] and op.cid:
            raw = car.blocks.get(op.cid)
            cooked = get_or_create(raw, strict=False)
            if cooked and cooked.py_type == "app.bsky.feed.post":
                toprint=""
                try:
                    if { "fr", } & set(raw["langs"]):
                        uri = raw["reply"]["root"]["uri"]
                        toprint = raw = bsc.get_posts([uri])
                        post = raw = raw.posts[0]
                        if "market" in raw["author"].handle:
                            raise SpamError(f"market in {raw['author'].handle}")

                        _,_,did,collection,rkey = uri.split("/")
                        url = f"https://bsky.app/profile/{did}/post/{rkey}"
                        at[url] = uri
                        i+=1
                        #from pdb import set_trace;set_trace()
                        if set(post.record.langs) & {'fr',}:
                            sys.stderr.write(".")
                            sys.stderr.flush()
                            if url not in evicted:

                                counter[url] = post.like_count+post.repost_count+post.quote_count+post.reply_count
                
                except IndexError:
                    dbg(toprint)
                    pass

                except KeyError:
                    pass
                except Exception as e:
                    dbg(e)

                if i> 200:
                    i=0
                    for p in sorted({ k:v for k, v in counter.items() if k not in evicted }.items(),
                        key=lambda x : x[1] )[::-1][0:1]:
                        dbg(p)
                        dbg(p[0].split("/")[-1])
                        if p[1]>25:
                            try:
                                raw = bsc.get_posts([at[p[0]]])
                                dbg(raw)
                                send_post(get_root_refs(at[p[0]], f"[BOT] le niveau d'agitation ici est de : {p[1]}"))
                            except KeyError:
                                dbg("invalid post")
                                dbg(raw)
                            finally:
                                evicted |= {p[0],}

                        

while [ 1 ]:             
    try:
        client.start(on_message_handler)
    except:
        pass

