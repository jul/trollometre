import json
import os
from atproto_client.models import get_or_create
from atproto import CAR, models, Client, client_utils
import requests
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message
from archery import mdict

from json import load, dumps

cfg = load(open(os.path.expanduser("~/.bluesky.json")))
handle = cfg["handle"]
password= cfg["password"]



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
from pdb import set_trace;set_trace()
import re
def parse_url(text: str) :
    spans = []
    # partial/naive URL regex based on: https://stackoverflow.com/a/3809435
    # tweaked to disallow some training punctuation
    url_regex = rb"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
    text_bytes = text.encode("UTF-8")
    for m in re.finditer(url_regex, text_bytes):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "url": m.group(1).decode("UTF-8"),
        })
    return spans

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
    print(json.dumps(resp.json(), indent=2))
    resp.raise_for_status()


# all of this undocumented horseshit is based on cargo-culting the bollocks out of
# https://github.com/MarshalX/atproto/blob/main/examples/firehose/sub_repos.py
# and
# https://github.com/MarshalX/bluesky-feed-generator/blob/main/server/data_stream.py

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
                # other types include "app.bsky.feed.like" etc which we ignore
                # note that this data does not include who posted this skeet
                # or possibly it does as a "CID" which you have to look up somehow
                # who the hell knows? not me
                try:
                    if "fr" in raw["langs"]:
                        #print(dumps(raw,indent=2, cls=JSONExtra))
                        #print(json.dumps(raw, cls=JSONExtra, indent=2))
                        uri = raw["reply"]["root"]["uri"]
                        _,_,did,collection,rkey = uri.split("/")
                        url = f"https://bsky.app/profile/{did}/post/{rkey}"
                        at[url] = uri
                        i+=1
                        if url not in evicted:
                            counter += mdict({ url : 1 })
                
                except KeyError:
                    pass
                if i> 200:
                    i=0
                    for p in sorted({ k:v for k, v in counter.items() if k not in evicted }.items(),
                        key=lambda x : x[1] )[::-1][0:2]:
                        print(p)
                        print(p[0].split("/")[-1])
                        raw = bsc.get_posts([at[p[0]]]).posts[0]
                       
                        send_post(get_root_refs(at[p[0]], f"seen here trolllevel : {p[1]}"))

                        evicted |= {p[0],}

                        

             
client.start(on_message_handler)

