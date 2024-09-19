from importlib import import_module

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.objects.secondclass.c_rule import Rule
from app.utility.base_knowledge_svc import BaseKnowledgeService
from app.utility.base_service import BaseService


class KnowledgeService(BaseService):

    def __init__(self):
        self.log = self.add_service('knowledge_svc', self)
        self.loaded_knowledge_module = BaseKnowledgeService()

    @staticmethod
    def _load_module(module_type, module_info):
        module = import_module(module_info['module'])
        return getattr(module, module_type)(module_info)

    async def add_fact(self, fact, constraints=None):
        if isinstance(fact, Fact):
            return await self.loaded_knowledge_module.add_fact(fact, constraints)

    async def update_fact(self, criteria, updates):
        return await self.loaded_knowledge_module.update_fact(criteria, updates)

    async def get_facts(self, criteria, restrictions=None):
        return await self.loaded_knowledge_module.get_facts(criteria, restrictions)

    async def delete_fact(self, criteria):
        return await self.loaded_knowledge_module.delete_fact(criteria)

    async def get_meta_facts(self, meta_fact=None, agent=None, group=None):
        return await self.loaded_knowledge_module.get_meta_facts(meta_fact, agent, group)

    async def get_fact_origin(self, fact):
        return await self.loaded_knowledge_module.get_fact_origin(fact)

    async def check_fact_exists(self, fact, listing=None):
        searchable = fact.display
        if not listing:
            results = await self.get_facts(criteria=searchable)
        else:
            results = any([fact == x for x in listing])
        if results:
            return True
        return False

    # -- Relationships --

    async def get_relationships(self, criteria, restrictions=None):
        return await self.loaded_knowledge_module.get_relationships(criteria, restrictions)

    async def add_relationship(self, relationship, constraints=None):
        if isinstance(relationship, Relationship):
            return await self.loaded_knowledge_module.add_relationship(relationship, constraints)

    async def update_relationship(self, criteria, updates):
        return await self.loaded_knowledge_module.update_relationship(criteria, updates)

    async def delete_relationship(self, criteria):
        return await self.loaded_knowledge_module.delete_relationship(criteria)

    # --- Rules ---
    async def add_rule(self, rule, constraints=None):
        if isinstance(rule, Rule):
            return await self.loaded_knowledge_module.add_rule(rule, constraints)

    async def get_rules(self, criteria, restrictions=None):
        return await self.loaded_knowledge_module.get_rules(criteria)

    async def delete_rule(self, criteria):
        return await self.loaded_knowledge_module.delete_rule(criteria)

    async def save_state(self):
        return await self.loaded_knowledge_module.save_state()

    async def restore_state(self):
        return await self.loaded_knowledge_module.restore_state()

    async def destroy(self):
        return self.loaded_knowledge_module.destroy()
