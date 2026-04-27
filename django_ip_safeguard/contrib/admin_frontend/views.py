from django.http import FileResponse, HttpResponse
from django.template import loader
from django.views import View
from django.conf import settings
import os
import django_ip_safeguard


def _get_frontend_static_dir():
    pkg_dir = os.path.dirname(django_ip_safeguard.__file__)
    return os.path.join(pkg_dir, "contrib", "admin_frontend", "static", "admin_frontend")


class FrontendIndexView(View):
    def get(self, request, path=""):
        static_dir = _get_frontend_static_dir()
        index_path = os.path.join(static_dir, "index.html")

        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            return HttpResponse(content, content_type="text/html")
        else:
            return HttpResponse(
                "Frontend not built. Run 'python manage.py build_frontend' first.",
                status=503,
                content_type="text/plain",
            )


def serve_frontend_assets(request, path=""):
    static_dir = _get_frontend_static_dir()
    if not path:
        path = "index.html"
    file_path = os.path.join(static_dir, path)

    if os.path.exists(file_path) and os.path.isfile(file_path):
        ext = os.path.splitext(path)[1].lower()
        content_types = {
            ".js": "application/javascript",
            ".css": "text/css",
            ".json": "application/json",
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
    else:
        return HttpResponse("Not Found", status=404)
