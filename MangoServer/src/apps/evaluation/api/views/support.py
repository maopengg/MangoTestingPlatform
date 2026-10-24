from src.apps.evaluation.selectors.scope import ensure_product_scope


def request_user(request):
    return getattr(getattr(request, "user", None), "user_obj", None)


def ensure_scope(request, project_product_id):
    ensure_product_scope(request_user(request), project_product_id)


def paginate(request, queryset, serializer_class):
    try:
        page = max(1, int(request.query_params.get("page") or 1))
        page_size = min(100, max(1, int(request.query_params.get("pageSize") or 10)))
    except (TypeError, ValueError):
        page, page_size = 1, 10
    count = queryset.count()
    items = queryset[(page - 1) * page_size:page * page_size]
    return {"items": serializer_class(items, many=True).data, "count": count, "page": page, "pageSize": page_size}
