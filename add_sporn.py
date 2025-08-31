
from atproto_client import Client, models
from atproto_core.uri import AtUri
from atproto_identity.resolver import IdResolver
from json import load
import os

cfg = load(open(os.path.expanduser("~/.bluesky.json")))
handle = cfg["handle"]
password= cfg["password"]

path_to_config = os.path.expanduser("~/.trollometre.vect.json")

blacklist= load(open(path_to_config))["blacklist"]

client = Client()
client.login(handle, password)
# https://bsky.app/profile/did:plc:sbnrwzz7i4nwm4umhfqaqakr/lists/3lxjv3j2nzj2k
# https://bsky.app/profile/did:plc:33dgbvoqbzyklsjwfhdbu5xr/lists/3lxh6fljblr26
mod_list_uri = 'at://did:plc:sbnrwzz7i4nwm4umhfqaqakr/app.bsky.graph.list/3lxjv3j2nzj2k'

mod_list_owner = AtUri.from_str(mod_list_uri).host

for user_handle_to_add in blacklist:
    user_to_add = IdResolver().handle.resolve(user_handle_to_add)
    print(f'Adding {user_handle_to_add} to the list {mod_list_uri} (owned by {mod_list_owner})')

    try:
        created_list_item = client.app.bsky.graph.listitem.create(
            mod_list_owner,
            models.AppBskyGraphListitem.Record(
                list=mod_list_uri,
                subject=user_to_add,
                created_at=client.get_current_time_iso(),
            ),
        )
    except:
        print(f"problem with user {user_handle_to_add}")


