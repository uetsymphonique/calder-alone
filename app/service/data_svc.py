import copy
import pathlib

from app.objects.c_ability import Ability
from app.objects.c_adversary import Adversary
from app.objects.c_objective import Objective
from app.objects.c_planner import Planner
from app.objects.c_source import Source
from app.objects.secondclass.c_executor import Executor, ExecutorSchema
from app.objects.secondclass.c_parser import Parser
from app.objects.secondclass.c_requirement import Requirement, RequirementSchema
from app.utility.base_service import BaseService
from app.utility.base_world import BaseWorld


class DataService(BaseService):
    def __init__(self):
        self.log = self.add_service('data_svc', self)
        self.schema = dict(agents=[], planners=[], adversaries=[], abilities=[], sources=[], operations=[],
                           schedules=[], plugins=[], obfuscators=[], objectives=[], data_encoders=[])
        self.ram = copy.deepcopy(self.schema)

    async def store(self, c_object):
        try:
            return c_object.store(self.ram)
        except Exception as e:
            self.log.error('[!] can only store first-class objects: %s' % e)

    async def locate(self, object_name, match=None):
        try:
            return [obj for obj in self.ram[object_name] if obj.match(match)]
        except Exception as e:
            self.log.error('[!] LOCATE: %s' % e)

    async def load_adversary_file(self, filename, access=BaseWorld.Access.RED):
        await self.load_yaml_file(Adversary, filename, access)

    async def load_source_file(self, filename, access=BaseWorld.Access.RED):
        await self.load_yaml_file(Source, filename, access)

    async def load_objective_file(self, filename, access=BaseWorld.Access.RED):
        await self.load_yaml_file(Objective, filename, access)

    async def load_planner_file(self, filename, access=BaseWorld.Access.RED):
        await self.load_yaml_file(Planner, filename, access)

    async def load_ability_file(self, filename, access=BaseWorld.Access.RED):
        for entries in self.strip_yml(filename):
            for ab in entries:
                ability_id = ab.pop('id', None)
                name = ab.pop('name', '')
                description = ab.pop('description', '')
                tactic = ab.pop('tactic', None)
                executors = await self.convert_v0_ability_executor(ab)
                technique_id = self.convert_v0_ability_technique_id(ab)
                technique_name = self.convert_v0_ability_technique_name(ab)
                privilege = ab.pop('privilege', None)
                repeatable = ab.pop('repeatable', False)
                singleton = ab.pop('singleton', False)
                requirements = await self.convert_v0_ability_requirements(ab.pop('requirements', []))
                buckets = ab.pop('buckets', [tactic])
                ab.pop('access', None)
                plugin = self._get_plugin_name(filename)
                ab.pop('plugin', plugin)

                if tactic and tactic not in filename:
                    self.log.warning('Ability=%s has wrong tactic' % ability_id)

                await self._create_ability(ability_id=ability_id, name=name, description=description, tactic=tactic,
                                           technique_id=technique_id, technique_name=technique_name,
                                           executors=executors, requirements=requirements, privilege=privilege,
                                           repeatable=repeatable, buckets=buckets, access=access, singleton=singleton,
                                           plugin=plugin,
                                           **ab)

    async def _create_ability(self, ability_id, name=None, description=None, tactic=None, technique_id=None,
                              technique_name=None, executors=None, requirements=None, privilege=None,
                              repeatable=False, buckets=None, access=None, singleton=False, plugin='', **kwargs):
        ability = Ability(ability_id=ability_id, name=name, description=description, tactic=tactic,
                          technique_id=technique_id, technique_name=technique_name, executors=executors,
                          requirements=requirements, privilege=privilege, repeatable=repeatable, buckets=buckets,
                          access=access, singleton=singleton, plugin=plugin, **kwargs)
        return await self.store(ability)

    async def convert_v0_ability_requirements(self, requirements_data: list):
        """Checks if ability file follows v0 requirement format, otherwise assumes v1 ability formatting."""
        if requirements_data and 'relationship_match' not in requirements_data[0]:
            return await self._load_ability_requirements(requirements_data)
        return await self.load_requirements_from_list(requirements_data)

    @staticmethod
    async def load_requirements_from_list(requirements: list):
        return [RequirementSchema().load(entry) for entry in requirements]

    @staticmethod
    async def _load_ability_requirements(requirements):
        loaded_reqs = []
        for requirement in requirements:
            for module in requirement:
                loaded_reqs.append(Requirement.load(dict(module=module, relationship_match=requirement[module])))
        return loaded_reqs

    @staticmethod
    def convert_v0_ability_technique_name(ability_data: dict):
        """Checks if ability file follows v0 technique_name format, otherwise assumes v1 ability formatting."""
        if 'technique' in ability_data:
            return ability_data.pop('technique', dict()).get('name')
        return ability_data.pop('technique_name')

    @staticmethod
    def convert_v0_ability_technique_id(ability_data: dict):
        """Checks if ability file follows v0 technique_id format, otherwise assumes v1 ability formatting."""
        if 'technique' in ability_data:
            return ability_data.get('technique', dict()).get('attack_id')
        return ability_data.pop('technique_id')

    async def convert_v0_ability_executor(self, ability_data: dict):
        """Checks if ability file follows v0 executor format, otherwise assumes v1 ability formatting."""
        if 'platforms' in ability_data:
            return await self.load_executors_from_platform_dict(ability_data.pop('platforms', dict()))
        return await self.load_executors_from_list(ability_data.pop('executors', []))

    @staticmethod
    async def load_executors_from_list(executors: list):
        return [ExecutorSchema().load(entry) for entry in executors]

    async def load_executors_from_platform_dict(self, platforms):
        executors = []
        for platform_names, platform_executors in platforms.items():
            for executor_names, executor in platform_executors.items():

                command = executor['command'].strip() if executor.get('command') else None
                cleanup = executor['cleanup'].strip() if executor.get('cleanup') else None

                code = executor['code'].strip() if executor.get('code') else None
                if code:
                    _, code_path = await self.get_service('file_svc').find_file_path(code)
                    if code_path:
                        _, code_data = await self.get_service('file_svc').read_file(code)
                        code = code_data.decode('utf-8').strip()

                language = executor.get('language')
                build_target = executor.get('build_target')
                payloads = executor.get('payloads')
                uploads = executor.get('uploads')
                timeout = executor.get('timeout', 60)
                variations = executor.get('variations', [])

                parsers = await self._load_executor_parsers(executor.get('parsers', []))

                for platform_name in platform_names.split(','):
                    for executor_name in executor_names.split(','):
                        executors.append(Executor(name=executor_name, platform=platform_name, command=command,
                                                  code=code, language=language, build_target=build_target,
                                                  payloads=payloads, uploads=uploads, timeout=timeout,
                                                  parsers=parsers, cleanup=cleanup, variations=variations))
        return executors

    @staticmethod
    async def _load_executor_parsers(parsers):
        ps = []
        for module in parsers:
            ps.append(Parser.load(dict(module=module, parserconfigs=parsers[module])))
        return ps

    async def load_yaml_file(self, object_class, filename, access):
        for src in self.strip_yml(filename):
            obj = object_class.load(src)
            obj.access = access
            # obj.plugin = self._get_plugin_name(filename)
            await self.store(obj)

    @staticmethod
    def _get_plugin_name(filename):
        plugin_path = pathlib.PurePath(filename).parts
        return plugin_path[1] if 'plugins' in plugin_path else ''

    async def get_facts_from_source(self, fact_source_id):
        fact_sources = await self.locate('sources', match=dict(id=fact_source_id))
        if len(fact_sources) == 0:
            return []
        elif len(fact_sources) > 1:
            self.log.error('Found multiple fact sources with the same id', fact_source_id)
            return []
        return fact_sources[0].facts
