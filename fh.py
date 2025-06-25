import json
import os
from atproto_client.models import get_or_create
from atproto import CAR, models, Client, client_utils
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

    def default(self, obj):
        try:
            result = json.JSONEncoder.default(self, obj)
            return result
        except:
            return repr(obj)

client = FirehoseSubscribeReposClient()

bsc = Client()
bsc.login(handle, password)


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
                        _,_,did,_,rkey = uri.split("/")
                        url = f"https://bsky.app/profile/{did}/post/{rkey}"
                        at[url] = uri
                        i+=1
                        if url not in evicted:
                            counter += mdict({ url : 1 })
                
                except KeyError:
                    pass
                if i> 100:
                    i=0
                    for p in sorted({ k:v for k, v in counter.items() if k not in evicted }.items(),
                        key=lambda x : x[1] )[::-1][0:2]:
                        print(p)
                        print(p[0].split("/")[-1])
                        raw = bsc.get_posts([at[p[0]]]).posts[0]
                       
                        print(json.dumps(raw, cls=JSONExtra, indent=2))
                        text = client_utils.TextBuilder().text("").link(raw.record.text,p[0])

                        post = bsc.send_post(text)
                        evicted |= {p[0],}

                        

             
client.start(on_message_handler)

