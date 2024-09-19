import asyncio
import json
import logging
import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
from importlib import import_module
from typing import Any, Iterable

from app.objects.secondclass.c_fact import OriginType
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_result import Result
from app.service.data_svc import DataService
from app.service.executing_svc import ExecutingService
from app.service.file_svc import FileService
from app.service.learning_svc import LearningService
from app.utility.base_object import BaseObject
from app.utility.base_service import BaseService


class Operation(BaseObject):
    def __init__(self, adversary=None, name="Calder-alone", agents: Iterable[Any] = None, source=None, planner=None,
                 obfuscator='plain-text', visibility=50, state='running'):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.name = name
        self.start, self.finish = None, None
        self.access, self.group = BaseService.Access.RED, "red"
        self.agents = agents
        self.adversary = adversary
        self.source = source
        self.planner = planner
        self.obfuscator = obfuscator
        self.visibility = visibility
        self.objective = None
        self.chain, self.potential_links, self.rules = [], [], []
        self.ignored_links = set()
        self.use_learning_parsers = True
        self.state = state
        self.base_timeout = 180
        self.link_timeout = 30
        self.autonomous = True
        if source:
            self.rules = source.rules

    def store(self, ram):
        existing = self.retrieve(ram['operations'], self.unique)
        if not existing:
            ram['operations'].append(self)
            return self.retrieve(ram['operations'], self.unique)
        existing.update('state', self.state)
        existing.update('obfuscator', self.obfuscator)
        return existing

    @property
    def unique(self):
        return self.hash('%s' % self.id)

    @property
    def states(self):
        return {state.name: state.value for state in self.States}

    def link_status(self):
        return -3 if self.autonomous else -1

    def add_link(self, link):
        self.chain.append(link)

    def has_link(self, link_id):
        return any(lnk.id == link_id for lnk in self.potential_links + self.chain)

    async def has_fact(self, trait, value):
        for f in await self.all_facts():
            if f.trait == trait and f.value == value:
                return True
        return False

    async def apply(self, link):
        while self.state != self.states['RUNNING']:
            if self.state == self.states['RUN_ONE_LINK']:
                self.add_link(link)
                self.state = self.states['PAUSED']
                return link.id
            else:
                await asyncio.sleep(15)
        self.add_link(link)
        return link.id

    async def _init_source(self):
        # seed knowledge_svc with source facts
        if self.source:
            knowledge_svc_handle = BaseService.get_service('knowledge_svc')
            for f in self.source.facts:
                f.origin_type = OriginType.SEEDED
                f.source = self.source.id
                await knowledge_svc_handle.add_fact(f)
            for r in self.source.relationships:
                r.origin = self.source.id
                await knowledge_svc_handle.add_relationship(r)

    async def run(self, services):
        self.start = datetime.now(timezone.utc)
        await self._init_source()
        # print(self.source.display)
        data_svc = services.get('data_svc')
        await self._load_objective(data_svc)
        try:
            await self.cede_control_to_planner(services)

            await self.write_event_logs_to_disk(services.get('file_svc'), data_svc, output=True)
        except Exception as e:
            logging.error(e, exc_info=True)

    async def write_event_logs_to_disk(self, file_svc, data_svc, output=False):
        event_logs = await self.event_logs(file_svc, data_svc, output=output)
        event_logs_dir = await file_svc.create_exfil_sub_directory('%s/event_logs' % self.get_config('reports_dir'))
        file_name = 'operation_%s.json' % self.id
        await self._write_logs_to_disk(event_logs, file_name, event_logs_dir, file_svc)
        logging.debug('Wrote event logs for operation %s to disk at %s/%s' % (self.name, event_logs_dir, file_name))

    @staticmethod
    async def _write_logs_to_disk(logs, file_name, dest_dir, file_svc):
        logs_dumps = json.dumps(logs) + os.linesep
        await file_svc.save_file(file_name, logs_dumps.encode(), dest_dir, encrypt=False, event_logs=True)

    async def event_logs(self, file_svc, data_svc, output=False):
        # Ignore discarded / high visibility links that did not actually run.
        return [await self._convert_link_to_event_log(step, file_svc, data_svc, output=output) for step in self.chain
                if not step.can_ignore()]

    async def _convert_link_to_event_log(self, link, file_svc, data_svc, output=False):
        event_dict = dict(command=self.decode_bytes(link.command),
                          plaintext_command=self.decode_bytes(link.plaintext_command),
                          delegated_timestamp=link.decide.strftime(self.TIME_FORMAT),
                          collected_timestamp=link.collect.strftime(self.TIME_FORMAT) if link.collect else None,
                          finished_timestamp=link.finish,
                          status=link.status,
                          platform=link.executor.platform,
                          executor=link.executor.name,
                          pid=link.pid,
                          agent_metadata=await self._get_agent_info_for_event_log(link.paw, data_svc),
                          ability_metadata=self._get_ability_metadata_for_event_log(link.ability),
                          operation_metadata=self._get_operation_metadata_for_event_log(),
                          attack_metadata=self._get_attack_metadata_for_event_log(link.ability))
        if output and link.output:
            results = self.decode_bytes(file_svc.read_result_file(link.unique))
            event_dict['output'] = json.loads(results.replace('\\r\\n', '').replace('\\n', ''))
        if link.agent_reported_time:
            event_dict['agent_reported_time'] = link.agent_reported_time.strftime(self.TIME_FORMAT)
        return event_dict

    @staticmethod
    async def _get_agent_info_for_event_log(agent_paw, data_svc):
        agent_search_results = await data_svc.locate('agents', match=dict(paw=agent_paw))
        if not agent_search_results:
            return {}
        else:
            # We expect only one agent per paw.
            agent = agent_search_results[0]
            return dict(paw=agent.paw,
                        group=agent.group,
                        architecture=agent.architecture,
                        username=agent.username,
                        location=agent.location,
                        pid=agent.pid,
                        ppid=agent.ppid,
                        privilege=agent.privilege,
                        host=agent.host,
                        contact=agent.contact,
                        created=agent.created.strftime(BaseObject.TIME_FORMAT))

    @staticmethod
    def _get_ability_metadata_for_event_log(ability):
        return dict(ability_id=ability.ability_id,
                    ability_name=ability.name,
                    ability_description=ability.description)

    def _get_operation_metadata_for_event_log(self):
        return dict(operation_name=self.name,
                    operation_start=self.start.strftime(self.TIME_FORMAT),
                    operation_adversary=self.adversary.name)

    @staticmethod
    def _get_attack_metadata_for_event_log(ability):
        return dict(tactic=ability.tactic,
                    technique_name=ability.technique_name,
                    technique_id=ability.technique_id)

    async def wait_for_links_completion(self, link_ids):
        for link_id in link_ids:
            link = [link for link in self.chain if link.id == link_id][0]
            executing_svc = ExecutingService()
            result = executing_svc.running(link)
            await self._save(result, link)
            if link.can_ignore():
                self.add_ignored_link(link.id)
            while not (link.finish or link.can_ignore()):
                await asyncio.sleep(5)

    async def _save(self, result: Result, link: Link):

        loop = asyncio.get_event_loop()
        link.finish = DataService.get_current_timestamp()
        link.status = int(result.status)
        if result.agent_reported_time:
            link.agent_reported_time = result.agent_reported_time
        if result.output or result.stderr:
            link.output = True
            result.output = await self._postprocess_link_result(result.output, link)
            command_results = json.dumps(dict(
                stdout=result.output,
                stderr=result.stderr,
                exit_code=result.exit_code))
            encoded_command_results = self.encode_string(command_results)
            # print(encoded_command_results)

            FileService().write_result_file(result.id, encoded_command_results)

            if link.executor.parsers:
                await loop.create_task(link.parse(self, result.output))
            elif self.use_learning_parsers:
                all_facts = await self.all_facts()
                await loop.create_task(LearningService().learn(all_facts, link, result.output, operation=self))

    async def _postprocess_link_result(self, result, link):
        if link.ability.HOOKS and link.executor.name in link.ability.HOOKS:
            return self.encode_string(await link.ability.HOOKS[link.executor.name].postprocess(result))
        return result

    def add_ignored_link(self, link_id):
        self.ignored_links.add(link_id)

    async def _load_objective(self, data_svc):
        obj = await data_svc.locate('objectives', match=dict(id=self.adversary.objective))
        if not obj:
            obj = await data_svc.locate('objectives', match=dict(name='default'))
        self.objective = deepcopy(obj[0])

    async def cede_control_to_planner(self, services):
        planner = await self._get_planning_module(services)
        await planner.execute()
        # for fact in services["knowledge_svc"].loaded_knowledge_module.fact_ram["facts"]:
        #     print(fact.display)
        while not await self.is_closeable():
            await asyncio.sleep(10)
        await self.close(services)

    async def is_closeable(self):
        if await self.is_finished():
            self.state = self.states['FINISHED']
            return True
        return False

    async def is_finished(self):
        if self.state in [self.states['FINISHED'], self.states['OUT_OF_TIME'], self.states['CLEANUP']] \
                or (self.objective and self.objective.completed(await self.all_facts())):
            return True
        return False

    async def all_facts(self):
        knowledge_svc_handle = BaseService.get_service('knowledge_svc')
        data_svc_handle = BaseService.get_service('data_svc')
        seeded_facts = []
        if self.source:
            seeded_facts = await data_svc_handle.get_facts_from_source(self.source.id)
        learned_facts = await knowledge_svc_handle.get_facts(criteria=dict(source=self.id))
        learned_facts = [f for f in learned_facts if f.score > 0]
        return seeded_facts + learned_facts

    async def _get_planning_module(self, services):
        planning_module = import_module(self.planner.module)
        return planning_module.LogicalPlanner(self, services.get('planning_svc'), **self.planner.params,
                                              stopping_conditions=self.planner.stopping_conditions)

    async def close(self, services):
        await self._cleanup_operation(services)
        await self._save_new_source(services)
        if self.state not in [self.states['FINISHED'], self.states['OUT_OF_TIME']]:
            self.state = self.states['FINISHED']
        self.finish = self.get_current_timestamp()

    async def _cleanup_operation(self, services):
        for member in self.agents:
            for link in await services.get('planning_svc').get_cleanup_links(self, member):
                self.add_link(link)
                executing_svc = ExecutingService()
                executing_svc.running(link)

    async def _save_new_source(self, services):
        def fact_to_dict(f):
            if f:
                return dict(trait=f.trait, value=f.value, score=f.score)

        data = dict(
            id=str(uuid.uuid4()),
            name=self.name,
            facts=[fact_to_dict(f) for link in self.chain for f in link.facts],
            relationships=[dict(source=fact_to_dict(r.source), edge=r.edge,
                                target=fact_to_dict(r.target), score=r.score)
                           for link in self.chain for r in link.relationships]
        )
        new_source = await services.get('rest_svc').persist_source(dict(access=[self.access]), data)
        # print(new_source)

    class States(Enum):
        RUNNING = 'running'
        RUN_ONE_LINK = 'run_one_link'
        PAUSED = 'paused'
        OUT_OF_TIME = 'out_of_time'
        FINISHED = 'finished'
        CLEANUP = 'cleanup'
