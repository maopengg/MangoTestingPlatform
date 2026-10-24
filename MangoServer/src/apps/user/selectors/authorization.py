class AuthorizationScopeSelector:
    """统一构造授权范围查询，避免协议适配层直接访问模型 Manager。"""

    @staticmethod
    def queryset(model):
        return model._default_manager.all()
