
from atproto_client import Client, models
from atproto_core.uri import AtUri
from atproto_identity.resolver import IdResolver
from json import loads, dumps, load
from sys import argv
import os

cfg = load(open(os.path.expanduser("~/.bluesky.json")))
handle = cfg["handle"]
password= cfg["password"]

path_to_config = os.path.expanduser("~/.trollometre.vect.json")

client = Client()
client.login(handle, password)
c= client.app.bsky.actor.get_profile(params=dict(actor=handle))
this = loads(c.model_dump_json())
print(this)

print(dumps(this, indent=4))
