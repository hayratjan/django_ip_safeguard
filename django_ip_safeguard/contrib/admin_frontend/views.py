from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
import os
import django_ip_safeguard


def _get_frontend_static_dir():
    pkg_dir = os.path.dirname(django_ip_safeguard.__file__)
    return os.path.normpath(
        os.path.join(pkg_dir, "contrib", "admin_frontend", "static", "admin_frontend")
    )


def _is_path_under(base_dir: str, candidate: str) -> bool:
    base = os.path.abspath(base_dir)
    full = os.path.abspath(candidate)
    return full == base or full.startswith(base + os.sep)


def serve_frontend_build_file(request, path):
    """提供 Vite 构建产物（如 assets/*.js），path 为 assets/ 之后的相对路径"""
    static_dir = _get_frontend_static_dir()
    file_path = os.path.normpath(os.path.join(static_dir, "assets", path))
    if not _is_path_under(static_dir, file_path):
        return HttpResponse("Not Found", status=404)
    if not (os.path.exists(file_path) and os.path.isfile(file_path)):
        return HttpResponse("Not Found", status=404)
    ext = os.path.splitext(path)[1].lower()
    # 默认 application/octet-stream 会让浏览器把 index.html 当成附件下载
    content_types = {
        ".html": "text/html",
        ".htm": "text/html",
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".map": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".eot": "application/vnd.ms-fontobject",
    }
    content_type = content_types.get(ext, "application/octet-stream")
    with open(file_path, "rb") as f:
        return HttpResponse(f.read(), content_type=content_type)


@require_http_methods(["GET", "HEAD"])
def serve_frontend_spa(request, path=""):
    """Vue 单页：除 /api、/assets 外的路径统一返回 index.html"""
    static_dir = _get_frontend_static_dir()
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.isfile(index_path):
        return HttpResponse(
            "Frontend not built. Run 'python manage.py build_frontend' first.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    if request.method == "HEAD":
        return HttpResponse(content_type="text/html; charset=utf-8")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HttpResponse(content, content_type="text/html; charset=utf-8")
