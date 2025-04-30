from urllib.parse import urlparse
import re
import socket


def is_valid_url(url):
    """综合校验URL合法性"""
    try:
        # 基本URL解析
        result = urlparse(url)

        # 1. 检查协议
        if result.scheme not in ('http', 'https'):
            return False, "协议必须是http或https"

        # 2. 检查网络位置部分(host:port)
        netloc = result.netloc
        if not netloc:
            return False, "缺少主机地址"

        # 3. 分离主机和端口
        host = netloc.split(':')[0]
        port = None
        if ':' in netloc:
            try:
                port = int(netloc.split(':')[1])
                if not (1 <= port <= 65535):
                    return False, "端口必须在1-65535范围内"
            except ValueError:
                return False, "端口必须是数字"

        # 4. 校验主机部分(IP或域名)
        # 4.1 尝试作为IP地址校验
        try:
            # 处理IPv6地址(如[::1])
            if host.startswith('[') and host.endswith(']'):
                host = host[1:-1]
                socket.inet_pton(socket.AF_INET6, host)
                return True, "合法的IPv6地址"
            else:
                socket.inet_pton(socket.AF_INET, host)
                return True, "合法的IPv4地址"
        except socket.error:
            pass  # 不是IP地址，继续校验域名

        # 4.2 校验域名
        if not re.match(
                r'^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$',
                host
        ):
            return False, "域名格式不合法"

        # 5. 额外检查腾讯域名
        if host.endswith('.tencent.com'):
            if not re.match(r'^[a-zA-Z0-9-]+\.tencent\.com$', host):
                return False, "非法的腾讯子域名"

        return True, "合法的URL"

    except Exception as e:
        return False, f"URL解析错误: {str(e)}"


# 要校验的URL列表
urls = [
    "https://yuanbao.tencent.com/",
    "https://127.0.0.1:8000",
    "https://yuanbao.tencent.com",
    "http://127.0.0.1:8000",
    "http://.1:8000",
    "http://yuanbao.tencent.com",
    "http//yuanbao.tencent.com"
]

# 校验并打印结果
print("{:<30} {:<10} {:<20}".format("URL", "是否合法", "说明"))
print("-" * 60)
for url in urls:
    valid, reason = is_valid_url(url)
    print(valid, reason)
    print("{:<30} {:<10} {:<20}".format(
        url,
        "✅" if valid else "❌",
        reason
    ))