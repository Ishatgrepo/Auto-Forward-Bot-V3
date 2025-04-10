import time as tm
from database import db 
from .test import parse_buttons

STATUS = {}


class STS:
    def __init__(self, id):
        self.id = id
        self.data = STATUS

    def verify(self):
        return self.data.get(self.id)

    def store(self, From, to, skip, limit, bot):
        self.data[self.id] = {
            "FROM": From,
            'TO': to,
            'total_files': 0,
            'skip': skip,
            'limit': limit,
            'fetched': skip,
            'filtered': 0,
            'deleted': 0,
            'duplicate': 0,
            'total': limit,
            'start': 0,
            'bot': bot  # Store the selected bot
        }
        self.get(full=True)
        return STS(self.id)

    async def get_data(self, user_id):
        k = self.get(full=True)
        _bot = k.bot  # Retrieve the selected bot
        configs = await db.get_configs(user_id)
        filters = await db.get_filters(user_id)
        size = None
        if configs['duplicate']:
            duplicate = [configs['db_uri'], self.TO]
        else:
            duplicate = False
        button = parse_buttons(configs['button'] if configs['button'] else '')
        if configs['file_size'] != 0:
            size = [configs['file_size'], configs['size_limit']]
        return _bot, configs['caption'], configs['forward_tag'], {
            'chat_id': k.FROM,
            'limit': k.limit,
            'offset': k.skip,
            'filters': filters,
            'keywords': configs['keywords'],
            'media_size': size,
            'extensions': configs['extension'],
            'skip_duplicate': duplicate
        }, configs['protect'], button

    # ... (rest of the class remains unchanged)