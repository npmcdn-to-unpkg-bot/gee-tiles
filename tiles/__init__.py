from flask import Flask, Response, request
from flask.ext.cache import Cache
import requests
from diskcache import FanoutCache as DiskCache

cache = Cache()

from tiles.gee import get_map, build_url, build_cache_key
from oauth2client.service_account import ServiceAccountCredentials
from collections import OrderedDict
import ee

app = Flask(__name__)

# Configure the flask app
app.config.from_object("tiles.config")

# initialize all of the extensions
cache.init_app(app)

disk = DiskCache('tile_cache', shards=app.config.get('TILE_CACHE_SHARDS'), size_limit=app.config.get('TILE_CACHE_SIZE_LIMIT'),
                   eviction_policy=app.config.get('TILE_CACHE_EVICTION'))

# initialize google earth engine
ee.Initialize(ServiceAccountCredentials._from_parsed_json_keyfile(
    app.config['GOOGLE_SERVICE_ACCOUNT'],
    scopes=app.config['GOOGLE_SERVICE_ACCOUNT_SCOPES']))  # debugging sitemap


def parse_request_args_values(key):
    """
    Takes in values for query parameters and returns a single
    element if the length of the array is one.
    :param values: *
    :return: *
    """
    values = request.args.getlist(key)
    if type(values) is list and len(values) == 1:
        return values[0]
    return values


@app.route('/<z>/<x>/<y>/tile.png')
def tile_proxy(z, x, y):
    map_args = {}

    # add query parameters to map arguments
    for k, v in request.args.items():
        map_args[k] = parse_request_args_values(k)

    map_args = OrderedDict(sorted(map_args.items(), key=lambda t: t[0]))

    # get the map information from google earth engine
    _map = get_map(**map_args)

    # build the url for tiles
    url = build_url(_map['mapid'], _map['token'], int(x), int(y), int(z))

    key = ("tile_%s_%s_%s_%s" % (build_cache_key(use_hash=True, **map_args), z, x, y))

    tile = disk.get(key)
    if tile is None:
        req = requests.get(url)
        tile = req.content
        disk.set(key, tile, expire=app.config.get('TILE_CACHE_EXPIRATION',0))
        content_type = req.headers['content-type']
    else:
        content_type = 'image/png'

    response = Response(tile, content_type=content_type)
    response.cache_control.max_age = 0
    return response