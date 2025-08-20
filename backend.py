from flask import Flask
from flask import request
import os
import requests
from atproto_client.models import get_or_create
from atproto import CAR, models, Client, client_utils
from atproto_firehose import FirehoseSubscribeReposClient, parse_subscribe_repos_message
from json import load
cfg = load(open(os.path.expanduser("~/.bluesky.json")))
handle = cfg["handle"]
password= cfg["password"]
client = FirehoseSubscribeReposClient()
bsc = Client()
import psycopg2 as sq

con = sq.connect(database="trollo", user="jul")
cur = con.cursor()


def repost_root_refs(parent_uri: str) :
    global bsc
    bsc.login(handle, password)
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
def send_post(payload):
    global bsc
    bsc.login(handle, password)
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



app = Flask(__name__)




@app.get('/spam/<path:uri>/<is_spam>')
def spam(uri, is_spam):
    print("spam")
    print(f"<{uri}>")
    print(is_spam)
    cur.execute("update posts SET is_spam= %s where uri = %s", [ is_spam=="true", uri, ])
    con.commit()

    return "is_spam %r" % is_spam

@app.get('/post/<path:uri>')
def post(uri):
    try:
        cur.execute("select score from posts where uri = %s", (uri,))
        score = cur.fetchone()[0]
        repost_root_refs(uri)
        print("sent")
        return "ok"
    except Exception as e:
        print(e)
        return "ko"



