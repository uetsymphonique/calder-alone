import re
from base64 import b64decode
from datetime import datetime, timezone
from typing import Iterable

from app.objects.c_ability import Ability
from app.utility.base_object import BaseObject


class Agent(BaseObject):
    RESERVED = dict(server='#{server}', group='#{group}', agent_paw='#{paw}', location='#{location}',
                    exe_name='#{exe_name}', upstream_dest='#{upstream_dest}',
                    payload=re.compile('#{payload:(.*?)}', flags=re.DOTALL))

    def __init__(self, paw=None, host='unknown', username='unknown', architecture='unknown', platform='unknown',
                 executors=(), privilege='User', origin_link_id='', deadman_enabled=False, host_ip_addresses=None,
                 location='unknown'):
        super().__init__()
        self.paw = paw if paw else self.generate_name(6)
        self.host = host
        self.username = username
        self.architecture = architecture
        self.platform = platform
        self.group = 'red'
        self.created = datetime.now(timezone.utc)
        self.executors = executors
        self.location = location
        self.privilege = privilege
        self.links = []
        self.access = self.Access.RED
        self.origin_link_id = origin_link_id
        self.deadman_enabled = deadman_enabled
        self.host_ip_addresses = host_ip_addresses if host_ip_addresses else []
        self._executor_change_to_assign = None
        self.log = self.create_logger('agent')

    @property
    def unique(self):
        return self.hash(self.paw)

    def store(self, ram):
        existing = self.retrieve(ram['agents'], self.unique)
        if not existing:
            ram['agents'].append(self)
            return self.retrieve(ram['agents'], self.unique)
        existing.update('group', self.group)
        return existing

    def replace(self, encoded_cmd, file_svc):
        decoded_cmd = b64decode(encoded_cmd).decode('utf-8', errors='ignore').replace('\n', '')
        # decoded_cmd = decoded_cmd.replace(self.RESERVED['server'], self.server)
        # decoded_cmd = decoded_cmd.replace(self.RESERVED['group'], self.group)
        # decoded_cmd = decoded_cmd.replace(self.RESERVED['agent_paw'], self.paw)
        # decoded_cmd = decoded_cmd.replace(self.RESERVED['location'], self.location)
        # decoded_cmd = decoded_cmd.replace(self.RESERVED['exe_name'], self.exe_name)
        # decoded_cmd = decoded_cmd.replace(self.RESERVED['upstream_dest'], self.upstream_dest)
        # decoded_cmd = self._replace_payload_data(decoded_cmd, file_svc)
        return decoded_cmd

    # def _replace_payload_data(self, decoded_cmd, file_svc):
    #     for uuid in re.findall(self.RESERVED['payload'], decoded_cmd):
    #         if self.is_uuid4(uuid):
    #             _, display_name = file_svc.get_payload_name_from_uuid(uuid)
    #             decoded_cmd = decoded_cmd.replace('#{payload:%s}' % uuid, display_name)
    #     return decoded_cmd

    async def capabilities(self, abilities: Iterable[Ability]):
        """Get abilities that the agent is capable of running
        :param abilities: List of abilities to check agent capability
        :type abilities: List[Ability]
        :return: List of abilities the agents is capable of running
        :rtype: List[Ability]
        """
        capabilities = []
        for ability in abilities:
            if self.privileged_to_run(ability) and ability.find_executors(self.executors, self.platform):
                capabilities.append(ability)
        return capabilities

    def privileged_to_run(self, ability):
        if not ability.privilege or self.Privileges[self.privilege].value >= self.Privileges[ability.privilege].value:
            return True
        return False

    async def get_preferred_executor(self, ability: Ability):
        """Get preferred executor for ability
        Will return None if the agent is not capable of running any
        executors in the given ability.
        :param ability: Ability to get preferred executor for
        :type ability: Ability
        :return: Preferred executor or None
        :rtype: Union[Executor, None]
        """
        potential_executors = ability.find_executors(self.executors, self.platform)
        if not potential_executors:
            return None

        preferred_executor_name = self._get_preferred_executor_name()
        for executor in potential_executors:
            if executor.name == preferred_executor_name:
                return executor
        return potential_executors[0]

    def _get_preferred_executor_name(self):
        if 'psh' in self.executors:
            return 'psh'
        elif 'sh' in self.executors:
            return 'sh'
        return self.executors[0]