import asyncio
import logging
import uuid

import yaml

from app.objects.c_source import Source
from app.utility.base_service import BaseService


class RestService(BaseService):
    def __init__(self):
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        self.log = self.add_service('rest_svc', self)
        self.loop = asyncio.get_event_loop()

    async def persist_source(self, access, data):
        """Persist sources. Accepts single source or bulk set of sources.
        For bulk, supply dict of form {"bulk": [{<sourc>}, {<source>},...]}.
        """
        if data.get('bulk', False):
            data = data['bulk']
        else:
            data = [data]
        r = []
        for source in data:
            r.extend(await self._persist_source(access, source))
        return r

    async def _persist_source(self, access, source):
        return await self._persist_item(access, 'sources', Source, source)

    async def _persist_item(self, access, object_class_name, object_class, item):
        if not item.get('id') or not item['id']:
            item['id'] = str(uuid.uuid4())
        _, file_path = await self.get_service('file_svc').find_file_path('%s.yml' % item['id'], location='data')
        if file_path:
            current_item = dict(self.strip_yml(file_path)[0])
            allowed = (await self.get_service('data_svc').locate(object_class_name, dict(id=item['id'])))[0].access
            current_item.update(item)
            final = item
        else:
            file_path = 'data/%s/%s.yml' % (object_class_name, item['id'])
            allowed = self._get_allowed_from_access(access)
            final = item
        await self._save_and_refresh_item(file_path, object_class, final, allowed)
        return [i.display for i in await self.get_service('data_svc').locate(object_class_name, dict(id=final['id']))]

    def _get_allowed_from_access(self, access):
        if self.Access.HIDDEN in access['access']:
            return self.Access.HIDDEN
        elif self.Access.BLUE in access['access']:
            return self.Access.BLUE
        else:
            return self.Access.RED

    async def _save_and_refresh_item(self, file_path, object_class, final, allowed):
        await self.get_service('file_svc').save_file(file_path, yaml.dump(final, encoding='utf-8', sort_keys=False),
                                                     '', encrypt=False)
        await self.get_service('data_svc').load_yaml_file(object_class, file_path, allowed)
