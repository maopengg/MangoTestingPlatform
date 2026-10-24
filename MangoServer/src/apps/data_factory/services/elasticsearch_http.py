from urllib import request as urllib_request


def open_elasticsearch_request(request, *, timeout, context=None):
    # 数据源连接与数据库驱动一样直连，不能继承进程为外部 HTTP 服务设置的代理。
    opener = urllib_request.build_opener(
        urllib_request.ProxyHandler({}),
        urllib_request.HTTPSHandler(context=context),
    )
    return opener.open(request, timeout=timeout)
