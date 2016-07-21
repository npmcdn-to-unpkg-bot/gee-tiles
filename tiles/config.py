import os
import json
import base64

GOOGLE_SERVICE_ACCOUNT = json.loads(
    base64.b64decode(os.environ.get('GOOGLE_SERVICE_ACCOUNT_ENC')).decode('utf-8'))
GOOGLE_SERVICE_ACCOUNT_SCOPES = ['https://www.googleapis.com/auth/fusiontables',
                                 'https://www.googleapis.com/auth/earthengine']

CACHE_TYPE = 'simple'
CACHE_REDIS_URL = 'redis://localhost:6379'

TILE_CACHE_SIZE_LIMIT = 2 ** 30 * 10  # 10GB
TILE_CACHE_EVICTION = 'least-recently-used'
TILE_CACHE_EXPIRATION = 3600 * 24 * 100 # 100 days
TILE_CACHE_SHARDS = 16