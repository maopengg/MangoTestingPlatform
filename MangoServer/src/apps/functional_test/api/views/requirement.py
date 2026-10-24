# -*- coding: utf-8 -*-

from src.apps.functional_test.api.serializers.requirement import FunctionalTestRequirementSerializer, \
    FunctionalTestRequirementSerializerC
from src.apps.functional_test.models import FunctionalTestRequirement
from src.common.responses.model_crud import ModelCRUD


class FunctionalTestRequirementCRUD(ModelCRUD):
    model = FunctionalTestRequirement
    queryset = FunctionalTestRequirement.objects.all()
    serializer_class = FunctionalTestRequirementSerializerC
    serializer = FunctionalTestRequirementSerializer
    page_permission_key = "functional.suite"
    not_matching_str = ModelCRUD.not_matching_str + ["owner"]
