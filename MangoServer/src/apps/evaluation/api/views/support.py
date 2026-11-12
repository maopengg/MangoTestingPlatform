from src.apps.evaluation.selectors.scope import ensure_product_scope


def request_user(request):
    """获取当前请求用户"""
    return getattr(getattr(request, "user", None), "user_obj", None)


def ensure_scope(request, project_product_id):
    """检查当前用户对评测资产的访问范围"""
    ensure_product_scope(request_user(request), project_product_id)


def paginate(request, queryset, serializer_class):
    """分页查询并构建评测数据响应"""
    try:
        page = max(1, int(request.query_params.get("page") or 1))
        page_size = min(100, max(1, int(request.query_params.get("pageSize") or 10)))
    except (TypeError, ValueError):
        page, page_size = 1, 10
    count = queryset.count()
    items = queryset[(page - 1) * page_size:page * page_size]
    return {"items": serializer_class(items, many=True).data, "count": count, "page": page, "pageSize": page_size}
