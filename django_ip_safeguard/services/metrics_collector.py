import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ProviderMetrics:
    name: str = ""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    circuit_breaker_open: int = 0
    last_request_at: str = ""
    last_success_at: str = ""
    last_failure_at: str = ""


@dataclass
class RiskEngineMetrics:
    total_evaluations: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    blocked_requests: int = 0
    allowed_requests: int = 0
    avg_risk_score: float = 0.0
    avg_evaluation_time_ms: float = 0.0


@dataclass
class CacheMetrics:
    total_operations: int = 0
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    hit_rate: float = 0.0
    memory_used_bytes: int = 0


@dataclass
class GeoPoolMetrics:
    total_lookups: int = 0
    china_hits: int = 0
    international_hits: int = 0
    unknown_hits: int = 0
    sync_count: int = 0
    last_sync_at: str = ""
    pool_size_china: int = 0
    pool_size_international: int = 0


@dataclass
class SystemMetrics:
    uptime_seconds: float = 0.0
    start_time: str = ""
    total_requests_processed: int = 0
    active_connections: int = 0
    redis_connected: bool = True
    geoip2_available: bool = False
    threat_intel_entries: int = 0


@dataclass
class PerformanceStats:
    providers: Dict[str, ProviderMetrics] = field(default_factory=dict)
    risk_engine: RiskEngineMetrics = field(default_factory=RiskEngineMetrics)
    cache: CacheMetrics = field(default_factory=CacheMetrics)
    geo_pool: GeoPoolMetrics = field(default_factory=GeoPoolMetrics)
    system: SystemMetrics = field(default_factory=SystemMetrics)
    last_updated: str = ""


class MetricsCollector:
    """性能指标收集器 - 线程安全"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._start_time = time.time()
            self._provider_metrics: Dict[str, ProviderMetrics] = {}
            self._risk_metrics = RiskEngineMetrics()
            self._cache_metrics = CacheMetrics()
            self._geo_pool_metrics = GeoPoolMetrics()
            self._system_metrics = SystemMetrics(start_time=datetime.now().isoformat())
            self._request_times: List[float] = []
            self._max_request_times = 1000
            self._risk_scores: List[int] = []
            self._max_risk_scores = 10000
            self._initialized = True

    def record_provider_request(
        self,
        provider_name: str,
        latency_ms: float,
        success: bool,
        cached: bool = False,
    ) -> None:
        with self._lock:
            if provider_name not in self._provider_metrics:
                self._provider_metrics[provider_name] = ProviderMetrics(name=provider_name)

            m = self._provider_metrics[provider_name]
            m.total_requests += 1
            m.total_latency_ms += latency_ms
            m.last_request_at = datetime.now().isoformat()

            if success:
                m.successful_requests += 1
                m.last_success_at = datetime.now().isoformat()
            else:
                m.failed_requests += 1
                m.last_failure_at = datetime.now().isoformat()

            if cached:
                m.cache_hits += 1
            else:
                m.cache_misses += 1

    def record_cache_operation(self, operation: str, hit: bool = False) -> None:
        with self._lock:
            self._cache_metrics.total_operations += 1
            if operation == "get":
                if hit:
                    self._cache_metrics.hits += 1
                else:
                    self._cache_metrics.misses += 1
            elif operation == "set":
                self._cache_metrics.sets += 1
            elif operation == "delete":
                self._cache_metrics.deletes += 1

            total = self._cache_metrics.hits + self._cache_metrics.misses
            if total > 0:
                self._cache_metrics.hit_rate = round(
                    self._cache_metrics.hits / total * 100, 2
                )

    def record_risk_evaluation(
        self,
        risk_score: int,
        risk_level: str,
        blocked: bool,
        evaluation_time_ms: float,
    ) -> None:
        with self._lock:
            self._risk_metrics.total_evaluations += 1
            self._risk_metrics.avg_evaluation_time_ms = (
                self._risk_metrics.avg_evaluation_time_ms * 0.9 + evaluation_time_ms * 0.1
            )

            self._risk_scores.append(risk_score)
            if len(self._risk_scores) > self._max_risk_scores:
                self._risk_scores = self._risk_scores[-self._max_risk_scores:]

            avg_score = sum(self._risk_scores) / len(self._risk_scores)
            self._risk_metrics.avg_risk_score = round(avg_score, 2)

            if risk_level == "high":
                self._risk_metrics.high_risk_count += 1
            elif risk_level == "medium":
                self._risk_metrics.medium_risk_count += 1
            else:
                self._risk_metrics.low_risk_count += 1

            if blocked:
                self._risk_metrics.blocked_requests += 1
            else:
                self._risk_metrics.allowed_requests += 1

    def record_geo_pool_lookup(self, result: str) -> None:
        with self._lock:
            self._geo_pool_metrics.total_lookups += 1
            if result == "china":
                self._geo_pool_metrics.china_hits += 1
            elif result == "international":
                self._geo_pool_metrics.international_hits += 1
            else:
                self._geo_pool_metrics.unknown_hits += 1

    def record_geo_pool_sync(self, pool_size_china: int, pool_size_international: int) -> None:
        with self._lock:
            self._geo_pool_metrics.sync_count += 1
            self._geo_pool_metrics.last_sync_at = datetime.now().isoformat()
            self._geo_pool_metrics.pool_size_china = pool_size_china
            self._geo_pool_metrics.pool_size_international = pool_size_international

    def record_request_time(self, latency_ms: float) -> None:
        with self._lock:
            self._request_times.append(latency_ms)
            if len(self._request_times) > self._max_request_times:
                self._request_times = self._request_times[-self._max_request_times:]

    def record_circuit_breaker_open(self, provider_name: str) -> None:
        with self._lock:
            if provider_name not in self._provider_metrics:
                self._provider_metrics[provider_name] = ProviderMetrics(name=provider_name)
            self._provider_metrics[provider_name].circuit_breaker_open += 1

    def update_system_status(
        self,
        redis_connected: bool,
        geoip2_available: bool,
        threat_intel_entries: int,
    ) -> None:
        with self._lock:
            self._system_metrics.redis_connected = redis_connected
            self._system_metrics.geoip2_available = geoip2_available
            self._system_metrics.threat_intel_entries = threat_intel_entries
            self._system_metrics.uptime_seconds = time.time() - self._start_time

    def get_stats(self) -> PerformanceStats:
        with self._lock:
            stats = PerformanceStats()
            stats.providers = dict(self._provider_metrics)
            stats.risk_engine = self._risk_metrics
            stats.cache = self._cache_metrics
            stats.geo_pool = self._geo_pool_metrics
            stats.system = self._system_metrics
            stats.system.uptime_seconds = time.time() - self._start_time
            stats.last_updated = datetime.now().isoformat()
            return stats

    def get_summary(self) -> Dict[str, Any]:
        stats = self.get_stats()
        return {
            "uptime_seconds": round(stats.system.uptime_seconds, 2),
            "total_requests": stats.risk_engine.total_evaluations,
            "blocked_requests": stats.risk_engine.blocked_requests,
            "cache_hit_rate": stats.cache.hit_rate,
            "avg_risk_score": stats.risk_engine.avg_risk_score,
            "avg_evaluation_time_ms": round(stats.risk_engine.avg_evaluation_time_ms, 2),
            "providers": {
                name: {
                    "requests": m.total_requests,
                    "success_rate": round(
                        m.successful_requests / m.total_requests * 100, 2
                    ) if m.total_requests > 0 else 0,
                    "avg_latency_ms": round(m.total_latency_ms / m.total_requests, 2)
                    if m.total_requests > 0 else 0,
                    "cache_hit_rate": round(
                        m.cache_hits / (m.cache_hits + m.cache_misses) * 100, 2
                    )
                    if (m.cache_hits + m.cache_misses) > 0
                    else 0,
                }
                for name, m in stats.providers.items()
            },
            "geo_pool": {
                "china_size": stats.geo_pool.pool_size_china,
                "international_size": stats.geo_pool.pool_size_international,
                "last_sync": stats.geo_pool.last_sync_at,
            },
        }

    def reset(self) -> None:
        with self._lock:
            self._provider_metrics.clear()
            self._risk_metrics = RiskEngineMetrics()
            self._cache_metrics = CacheMetrics()
            self._geo_pool_metrics = GeoPoolMetrics()
            self._request_times.clear()
            self._risk_scores.clear()


metrics_collector = MetricsCollector()
