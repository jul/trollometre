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



@app.get("/hello/<name>")
def hello(name):
    print(name)
    return "name"

@app.get('/spam/<path:uri>/<is_spam>')
def spam(uri, is_spam):
    print("spam")
    print(f"<{uri}>")
    print(is_spam)
    cur.execute("select is_spam from posts where is_spam is NULL and uri = %s", (uri,))
    if cur.fetchone() is not None:
        if is_spam != "true":
        
            cur.execute("select score from posts where uri = %s", (uri,))
            score = cur.fetchone()[0]

            print(f"score for uri is {score}")
            send_post(get_root_refs(uri, f"[BOT] le niveau d'agitation ici est de : {score}"))

            print("is ham")
        cur.execute("update posts SET is_spam= %s where uri = %s", [ is_spam=="true", uri, ])
        con.commit()

    return "spam"
