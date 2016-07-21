import ee
import json
from tiles import cache
from werkzeug.exceptions import BadRequest
import sys
import time
import random

BASE_URL = 'https://earthengine.googleapis.com/'


def build_cache_key(use_hash=True, **kwargs):
    """
    Builds a unique key for the map to go into the cache.
    :param kwargs:
    :return:
    """

    j = json.dumps(kwargs, sort_keys=True)
    print(j)
    if use_hash:
        h = hash(json.dumps(kwargs, sort_keys=True))
        h += sys.maxsize + 1
        return str(h)
    return j


def get_map(**kwargs):
    """
    Gets map from cache if it exists or calls method to build it.

    Cache expiration has a fuzzy expiration to prevent future build
    calls occurring at the same time.

    If exception raised by ee, such as 429, try again with linear delay
    :param kwargs:
    :return:
    """
    key = build_cache_key(**kwargs)
    map_id = cache.get(key)

    tries = 0
    while map_id is None:
        try:
            map_id = build_map(**kwargs)
        except ee.EEException as e:
            # check tries, increment and sleep
            if tries > 5:
                raise e
            tries += 1
            time.sleep(tries * random.random())

            # check if other got the map during delay
            map_id = cache.get(key)
        else:
            # set key
            cache.set(key, map_id, timeout=3600 - int(random.randrange(0, 300)))

    return map_id


def get_vis_params(img, col, **kwargs):
    vis_params = {}

    # user specified
    if 'palette' in kwargs:
        vis_params['palette'] = kwargs['palette']

        if 'min' in kwargs:
            vis_params['min'] = float(kwargs['min'])

        if 'max' in kwargs:
            vis_params['max'] = float(kwargs['max'])

    # defaults and from image metadata
    elif 'band' in kwargs:
        band = kwargs['band']
        if band == 'class':
            try:
                if col is not None:
                    properties = ee.Image(col.first()).toDictionary().getInfo()
                elif img is not None:
                    properties = img.toDictionary().getInfo()
                else:
                    return vis_params
            except ee.EEException as e:
                if '429' in str(e):
                    raise e
                raise BadRequest("No images found.")
            else:
                # set vis from image
                vis_params['palette'] = properties['class_palette']
                vis_params['min'] = 0
                vis_params['max'] = len(vis_params['palette'].split(',')) - 1  # zero based

        elif band == 'cropland':
            vis_params['palette'] = '000000,00ff00'
            vis_params['min'] = 0
            vis_params['max'] = 1

        elif band == 'water':
            vis_params['palette'] = '000000,0000ff,00ffff'
            vis_params['min'] = 1
            vis_params['max'] = 2

        elif band == 'intensity':
            vis_params['palette'] = '000000,0000ff,00ff00,ff0000,ffff00'
            vis_params['min'] = 1
            vis_params['max'] = 4

            # TODO crop type

    return vis_params


def get_expiration(z, **kwargs):
    if z > 15:
        return 300
    elif z > 13:
        return 3600

    if 'id' in kwargs:
        return 3600 * 24 * 50

    return 3600 * 24 * 10


def build_map(**kwargs):
    """
    Creates a map in Google Earth Engine using the python api and returns the map id and token.
    :param kwargs:
    :return: mapid object
    """

    reducer = getattr(ee.Reducer, kwargs.get('reducer', 'mode'))()

    if 'collection' in kwargs:
        collection = ee.ImageCollection(kwargs['collection'])
        collection = collection.select(kwargs.get('band', ['.*']))

        if 'id' in kwargs:
            collection = collection.filterMetadata('id', 'equals', kwargs['id'])
            vis_params = get_vis_params(None, collection, **kwargs)
        else:
            vis_params = get_vis_params(None, None, **kwargs)

        image = ee.Image(collection.reduce(reducer))

    elif 'image' in kwargs:
        image = ee.Image(kwargs['image'])
        image = image.select(kwargs.get('band', ['.*']))
        vis_params = get_vis_params(image, None, **kwargs)

    else:
        raise ee.EEException("No image or collection specified")

    mapid = image.getMapId(vis_params=vis_params)

    del mapid['image']
    return mapid


def build_url(map_id, token, x, y, z):
    """
    Generates the url for the tile. Builtin function is buggy.
    :param map_id: String
    :param token: String
    :param x: int
    :param y: int
    :param z: int
    :return: String
    """
    return '%s/map/%s/%d/%d/%d?token=%s' % (BASE_URL, map_id, z, x, y, token)