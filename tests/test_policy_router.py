"""policy_router 单元测试：仅基于纯内存 CompiledPolicy，不需要 DB。"""

from django_ip_safeguard.services.policy_router import CompiledPolicy, select_policy


def _p(name, **kw):
    return CompiledPolicy(name=name, priority=kw.pop("priority", 100), enabled=kw.pop("enabled", True), **kw)


def test_select_returns_first_by_priority_when_match():
    high = _p("api", priority=10, match_path_prefixes=("/api/",))
    default = _p("default", priority=10000)
    chosen = select_policy([default, high], host="example.com", path="/api/x", method="GET")
    assert chosen is not None
    assert chosen.name == "api"


def test_select_skips_disabled():
    disabled = _p("api", priority=10, enabled=False, match_path_prefixes=("/api/",))
    default = _p("default", priority=10000)
    chosen = select_policy([disabled, default], host="example.com", path="/api/x", method="GET")
    assert chosen is None or chosen.name == "default"


def test_host_regex_filter():
    api = _p("api", priority=10, match_host_regex=r"^api\.")
    default = _p("default", priority=10000)
    assert select_policy([api, default], host="api.example.com", path="/x", method="GET").name == "api"
    # host 不匹配则跳过 api，落到 default
    assert select_policy([api, default], host="www.example.com", path="/x", method="GET").name == "default"


def test_method_filter():
    write = _p("writes", priority=10, match_methods=("POST", "PUT"))
    default = _p("default", priority=10000)
    assert select_policy([write, default], host="x", path="/y", method="POST").name == "writes"
    assert select_policy([write, default], host="x", path="/y", method="GET").name == "default"


def test_no_filters_means_match_all():
    only = _p("only", priority=1)
    chosen = select_policy([only], host="", path="", method="")
    assert chosen.name == "only"
