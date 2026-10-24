# -*- coding: utf-8 -*-

from src.apps.ai.api.serializers.agent_context import AiAgentContextSerializer
from src.apps.ai.models import AiAgentContext
from src.common.responses.model_crud import ModelCRUD


class AiAgentContextCRUD(ModelCRUD):
    model = AiAgentContext
    queryset = AiAgentContext.objects.all()
    serializer_class = AiAgentContextSerializer
    serializer = AiAgentContextSerializer
    page_permission_key = 'ai.task'
    not_matching_str = ModelCRUD.not_matching_str + ["suite_id", "manual_case_id", "context_type", "context_hash",
                                                     "task"]
