"""Next-best-action orchestration service."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.core.database import (
    QueryCache,
    QueryMonitor,
    SlowQueryDetector,
    ConnectionPool,
    DatabaseConfig,
    get_query_cache,
)
from src.core.database.cache import CacheStrategy
from src.core.database.repositories import SqlUsageAnalyticsRepository

if TYPE_CHECKING:
    from src.core.database.repositories import SqlMealPlanRepository, SqlUserRepository

logger = logging.getLogger(__name__)

DEFAULT_DECISION_TTL = 15 * 60  # seconds
DEFAULT_CONTEXT_TTL = 10 * 60   # seconds
PUSH_CHANNELS = {"sms", "whatsapp"}


@dataclass(slots=True)
class NextBestActionInput:
    """Normalized input payload for NBA scoring."""

    user_id: str
    channel: str
    locale: str
    timezone: str
    user_name: Optional[str]
    diet: Optional[str]
    allergies: Tuple[str, ...]
    goal: Optional[str]
    plan_day: Optional[int]
    streak: int
    tokens: int
    quiet_hours: Optional[Tuple[dt_time, dt_time]]
    recent_actions: Tuple[Dict[str, Any], ...]
    cost_flags: Dict[str, Any]
    plan_status: Dict[str, Any]
    channel_preferences: Tuple[str, ...]
    feature_flags: Dict[str, bool]
    initiated_by_user: bool
    correlation_id: Optional[str]
    journey_override: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "NextBestActionInput":
        prefs = payload.get("channel_preferences") or payload.get("preferred_channels") or []
        quiet_hours = cls._parse_quiet_hours(payload.get("quiet_hours"))
        plan_day = payload.get("plan_day")
        try:
            plan_day_value = int(plan_day) if plan_day is not None else None
        except (TypeError, ValueError):
            plan_day_value = None
        allergies = tuple(payload.get("allergies") or (payload.get("dietary_allergies") or ()))
        feature_flags = payload.get("feature_flags") or {}
        cost_flags = payload.get("cost_flags") or {}
        plan_status = payload.get("plan_status") or {}
        recent_actions = tuple(payload.get("recent_actions") or ())
        return cls(
            user_id=str(payload.get("user_id")),
            channel=(payload.get("channel") or "app").lower(),
            locale=(payload.get("locale") or "en-US"),
            timezone=(payload.get("timezone") or "UTC"),
            user_name=payload.get("user_name") or payload.get("profile", {}).get("first_name"),
            diet=payload.get("diet") or payload.get("dietary_pattern"),
            allergies=allergies,
            goal=payload.get("goal") or payload.get("primary_goal"),
            plan_day=plan_day_value,
            streak=int(payload.get("streak") or 0),
            tokens=int(payload.get("tokens") or 0),
            quiet_hours=quiet_hours,
            recent_actions=recent_actions,
            cost_flags=dict(cost_flags),
            plan_status=dict(plan_status),
            channel_preferences=tuple(prefs),
            feature_flags={k: bool(v) for k, v in feature_flags.items()},
            initiated_by_user=bool(payload.get("initiated_by_user", False)),
            correlation_id=payload.get("correlation_id"),
            journey_override=payload.get("journey_override"),
        )

    def context_summary(self) -> str:
        diet = self.diet or "general"
        allergies = ",".join(self.allergies) if self.allergies else "none"
        goal = self.goal or "balanced"
        day = f"Day {self.plan_day}" if self.plan_day is not None else "Day ?"
        display_name = self.user_name or "Friend"
        return (
            f"{self.channel} | {self.locale} | {self.timezone} | {display_name} | "
            f"{diet}/{allergies} | {goal} | {day} | {self.streak} | {self.tokens}"
        )

    def prefers_channel(self, channel: str) -> bool:
        return channel in self.channel_preferences

    def allows_feature(self, flag: str, default: bool = True) -> bool:
        return self.feature_flags.get(flag, default)

    @staticmethod
    def _parse_quiet_hours(value: Any) -> Optional[Tuple[dt_time, dt_time]]:
        if not value:
            return None
        if isinstance(value, dict):
            start_raw = value.get("start")
            end_raw = value.get("end")
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            start_raw, end_raw = value
        elif isinstance(value, str) and "-" in value:
            start_raw, end_raw = value.split("-", 1)
        else:
            return None
        start = _parse_time_of_day(start_raw)
        end = _parse_time_of_day(end_raw)
        if start and end:
            return start, end
        return None


@dataclass(slots=True)
class Candidate:
    journey: str
    primary_message: str
    cta_label: str
    path: str
    score: float
    effort: int
    cost: int
    channel_fit: Dict[str, float]
    reasons: List[str] = field(default_factory=list)
    secondary: Optional[Dict[str, str]] = None


@dataclass(slots=True)
class ScoredCandidate:
    candidate: Candidate
    final_score: float
    score_breakdown: Dict[str, float]


class NextBestActionService:
    def _create_usage_repository(self) -> Optional[SqlUsageAnalyticsRepository]:
        """Initialise a lightweight usage analytics repository."""

        try:
            pool = ConnectionPool(DatabaseConfig(dsn=os.getenv("NBA_ANALYTICS_DB", ":memory:")))
            return SqlUsageAnalyticsRepository(pool, monitor=self.monitor)
        except Exception as exc:  # pragma: no cover - best effort
            logger.debug("Unable to initialise usage analytics repository: %s", exc)
            return None


    """Scores next-best action journeys and returns messaging metadata."""

    def __init__(
        self,
        *,
        user_repo: Optional["SqlUserRepository"] = None,
        meal_plan_repo: Optional["SqlMealPlanRepository"] = None,
        usage_repo: Optional[SqlUsageAnalyticsRepository] = None,
        cache: Optional[QueryCache] = None,
        monitor: Optional[QueryMonitor] = None,
        slow_detector: Optional[SlowQueryDetector] = None,
        decision_ttl: int = DEFAULT_DECISION_TTL,
        context_ttl: int = DEFAULT_CONTEXT_TTL,
        clock: Optional[callable] = None,
    ) -> None:
        self.user_repo = user_repo
        self.meal_plan_repo = meal_plan_repo
        self.cache = cache or get_query_cache()
        self.monitor = monitor or QueryMonitor()
        if usage_repo is None:
            usage_repo = self._create_usage_repository()
        self._usage_repo = usage_repo
        self._slow_detector = slow_detector or SlowQueryDetector(self.monitor, threshold=0.6)
        if usage_repo is not None:
            # Persist slow query events for dashboards without PII
            usage_repo.attach_to_monitor(self.monitor, channel="nba", locale=None)
        self._decision_ttl = decision_ttl
        self._context_ttl = context_ttl
        self._clock = clock or (lambda: datetime.utcnow())
        self._enabled_env = os.getenv("NBA_ORCHESTRATION_ENABLED", "true").lower() not in {"0", "false", "off"}
        self._release = os.getenv("APP_RELEASE", os.getenv("GIT_COMMIT", "dev"))


    async def select_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = NextBestActionInput.from_payload(payload)
        if not self._feature_enabled(request):
            return self._default_response(request)

        decision_start = time.perf_counter()
        decision_cache_key = self._decision_cache_key(request)
        cached_decision, cached_hit = await self._cache_get(decision_cache_key)
        if cached_hit and cached_decision:
            if not self._should_refresh_cached_decision(cached_decision, request):
                result = dict(cached_decision)
                metadata = dict(result.get("metadata", {}))
                metadata.update(
                    {
                        "cache_hit": True,
                        "context": request.context_summary(),
                        "correlation_id": metadata.get("correlation_id") or request.correlation_id or str(uuid4()),
                        "decision_ms": round((time.perf_counter() - decision_start) * 1000, 1),
                    }
                )
                result["metadata"] = metadata
                self._record_monitor(request, result, time.perf_counter() - decision_start, cache_hit=True)
                return result

        context_cache_key = f"nba:context:{request.user_id}"
        context, context_hit = await self._cache_get(context_cache_key)
        if not context:
            context = self._compose_live_context(request)
            await self._cache_set(context_cache_key, context, ttl=self._context_ttl)
        else:
            context = dict(context)
        context["_cache_hit"] = context_hit

        scored_candidates = self._score_candidates(request, context)
        if not scored_candidates:
            result = self._default_response(request)
            result["metadata"]["context_cache_hit"] = context_hit
            await self._cache_set(decision_cache_key, result, ttl=self._decision_ttl)
            self._record_monitor(request, result, time.perf_counter() - decision_start)
            return result

        best = self._choose_best(scored_candidates, request)
        result = self._build_decision_payload(request, best, context)
        elapsed = time.perf_counter() - decision_start
        result.setdefault("metadata", {})["decision_ms"] = round(elapsed * 1000, 1)
        result["metadata"]["context_cache_hit"] = context_hit
        await self._cache_set(decision_cache_key, result, ttl=self._decision_ttl)
        self._record_monitor(request, result, elapsed)
        return result

    def _feature_enabled(self, request: NextBestActionInput) -> bool:
        if not self._enabled_env:
            return False
        return request.allows_feature("unified_orchestration", True)

    async def _cache_get(self, key: str) -> Tuple[Any, bool]:
        if not self.cache:
            return None, False
        result = await self._maybe_await(self.cache.get(key))
        if isinstance(result, tuple) and len(result) == 2:
            value, hit = result
            return value, bool(hit)
        return result, result is not None

    async def _cache_set(self, key: str, value: Any, *, ttl: int) -> None:
        if not self.cache:
            return
        try:
            await self._maybe_await(self.cache.set(key, value, ttl=ttl, strategy=CacheStrategy.WRITE_THROUGH))
        except TypeError:
            await self._maybe_await(self.cache.set(key, value))

    def _decision_cache_key(self, request: NextBestActionInput) -> str:
        return f"nba:decision:{request.user_id}:{request.channel}"

    def _should_refresh_cached_decision(self, cached: Dict[str, Any], request: NextBestActionInput) -> bool:
        metadata = cached.get("metadata") or {}
        if request.allows_feature("force_refresh", False):
            return True
        if metadata.get("tokens") != request.tokens:
            return True
        cached_action_id = metadata.get("last_action_id")
        return cached_action_id != self._last_action_identifier(request)

    def _compose_live_context(self, request: NextBestActionInput) -> Dict[str, Any]:
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo("UTC"))
        context: Dict[str, Any] = {
            "skipped_meals": 0,
            "last_log_delta_hours": None,
            "last_action_id": self._last_action_identifier(request),
            "needs_groceries": False,
            "grocery_completed": bool(request.plan_status.get("grocery_completed")),
            "swap_requested": False,
            "cost_sensitive": bool(request.cost_flags.get("limit_reached") or request.cost_flags.get("budget_hold")),
            "streak_drop": False,
            "plan_freshness_hours": None,
            "plan_day": request.plan_day,
        }

        last_log_at: Optional[datetime] = None
        for action in request.recent_actions:
            action_type = (action.get("type") or action.get("kind") or "").lower()
            timestamp = self._parse_timestamp(action.get("timestamp") or action.get("at"))
            if action_type in {"meal_log", "log_meal", "meal_logged"}:
                if timestamp and (last_log_at is None or timestamp > last_log_at):
                    last_log_at = timestamp
            status = (action.get("status") or action.get("state") or "").lower()
            if status in {"skipped", "missed"} or action_type in {"skip_meal", "meal_skipped"}:
                context["skipped_meals"] += 1
                context["swap_requested"] = True
            if action_type in {"grocery_list_opened", "grocery_reminder", "shopping_pending"}:
                context["needs_groceries"] = True
            if action_type in {"grocery_completed", "shopping_complete"}:
                context["grocery_completed"] = True
                context["needs_groceries"] = False
            if action_type in {"streak_reset", "lapse"}:
                context["streak_drop"] = True
        if last_log_at:
            delta = now - last_log_at
            context["last_log_delta_hours"] = max(delta.total_seconds() / 3600, 0.0)
        plan_generated = self._parse_timestamp(
            request.plan_status.get("generated_at") or request.plan_status.get("plan_generated_at")
        )
        if plan_generated:
            context["plan_freshness_hours"] = max((now - plan_generated).total_seconds() / 3600, 0.0)
        prev_streak = request.plan_status.get("previous_streak")
        if isinstance(prev_streak, int) and prev_streak > request.streak:
            context["streak_drop"] = True
        if not context["grocery_completed"] and request.plan_day is not None:
            if request.plan_day in {0, 6}:
                context["needs_groceries"] = True
        context["tokens"] = request.tokens
        return context

    def _score_candidates(self, request: NextBestActionInput, context: Dict[str, Any]) -> List[ScoredCandidate]:
        candidates = self._build_candidates(request, context)
        if request.journey_override:
            filtered = [candidate for candidate in candidates if candidate.journey == request.journey_override]
            if filtered:
                candidates = filtered
        scored: List[ScoredCandidate] = []
        for candidate in candidates:
            breakdown: Dict[str, float] = {"base": candidate.score}
            channel_adjust = candidate.channel_fit.get(request.channel, 0.0)
            if channel_adjust:
                breakdown["channel_fit"] = channel_adjust
            if context.get("cost_sensitive") and candidate.cost > 1:
                breakdown["cost_penalty"] = -6.0
            final_score = sum(breakdown.values())
            scored.append(
                ScoredCandidate(
                    candidate=candidate,
                    final_score=final_score,
                    score_breakdown=breakdown,
                )
            )
        return scored

    def _choose_best(self, scored: List[ScoredCandidate], request: NextBestActionInput) -> ScoredCandidate:
        return max(
            scored,
            key=lambda item: (
                item.final_score,
                -item.candidate.effort,
                -item.candidate.cost,
                item.candidate.channel_fit.get(request.channel, 0.0),
            ),
        )

    def _build_decision_payload(
        self,
        request: NextBestActionInput,
        scored: ScoredCandidate,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        candidate = scored.candidate
        deep_link = self._build_deep_link(candidate.path, request, candidate.journey)
        metadata: Dict[str, Any] = {
            "score": round(scored.final_score, 2),
            "score_breakdown": scored.score_breakdown,
            "reasons": candidate.reasons,
            "context": request.context_summary(),
            "tokens": request.tokens,
            "last_action_id": context.get("last_action_id"),
            "analytics_tags": {
                "channel": request.channel,
                "locale": request.locale,
                "release": self._release,
                "route": "nba",
                "journey": candidate.journey,
                "correlation_id": request.correlation_id or str(uuid4()),
            },
        }
        timezone = self._resolve_timezone(request.timezone)
        local_now = self._now(timezone)
        queue, resume_at = self._should_queue(request, local_now, candidate)
        metadata["should_queue"] = queue
        if resume_at:
            metadata["resume_at"] = resume_at.isoformat()
        if request.quiet_hours:
            metadata["quiet_hours"] = f"{request.quiet_hours[0].strftime('%H:%M')}-{request.quiet_hours[1].strftime('%H:%M')}"
        if candidate.secondary:
            metadata["secondary_cta"] = {
                "label": candidate.secondary["label"],
                "deep_link": self._build_deep_link(candidate.secondary["path"], request, candidate.journey),
            }
        return {
            "journey": candidate.journey,
            "channel": request.channel,
            "primary_message": candidate.primary_message,
            "cta_label": candidate.cta_label,
            "deep_link": deep_link,
            "metadata": metadata,
        }

    def _should_queue(
        self,
        request: NextBestActionInput,
        local_now: datetime,
        candidate: Candidate,
    ) -> Tuple[bool, Optional[datetime]]:
        if request.initiated_by_user:
            return False, None
        if not request.quiet_hours:
            return False, None
        if request.channel not in PUSH_CHANNELS:
            return False, None
        start, end = request.quiet_hours
        if not self._is_within_quiet_hours(local_now.time(), start, end):
            return False, None
        resume_at = self._next_quiet_end(local_now, start, end)
        return True, resume_at

    def _resolve_timezone(self, name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            return ZoneInfo("UTC")

    def _now(self, tz: ZoneInfo) -> datetime:
        current = self._clock()
        if current.tzinfo is None:
            current = current.replace(tzinfo=ZoneInfo("UTC"))
        return current.astimezone(tz)

    def _is_within_quiet_hours(self, current: dt_time, start: dt_time, end: dt_time) -> bool:
        if start <= end:
            return start <= current < end
        return current >= start or current < end

    def _next_quiet_end(self, local_now: datetime, start: dt_time, end: dt_time) -> datetime:
        candidate = datetime.combine(local_now.date(), end, tzinfo=local_now.tzinfo)
        if start <= end:
            if local_now.time() < end:
                return candidate
            return candidate + timedelta(days=1)
        if local_now.time() < end:
            return candidate
        return candidate + timedelta(days=1)

    def _build_deep_link(self, path: str, request: NextBestActionInput, journey: str) -> str:
        try:
            from services.messaging.templates import build_deep_link
        except ImportError:  # pragma: no cover - fallback for direct module execution
            from src.services.messaging.templates import build_deep_link
        return build_deep_link(path, channel=request.channel, journey=journey, locale=request.locale)

    def _record_monitor(
        self,
        request: NextBestActionInput,
        result: Dict[str, Any],
        duration: float,
        *,
        cache_hit: bool = False,
    ) -> None:
        if not self.monitor:
            return
        payload = {
            "operation": "nba_decision",
            "journey": result.get("journey"),
            "channel": request.channel,
            "locale": request.locale,
            "streak": request.streak,
            "cache_hit": cache_hit,
        }
        self.monitor.record(payload, duration=duration, rowcount=None, origin="next_best_action")

    def _default_response(self, request: NextBestActionInput) -> Dict[str, Any]:
        candidate = Candidate(
            journey="today",
            primary_message=self._localize("today_primary", request.locale),
            cta_label=self._localize("today_cta", request.locale),
            path=f"/plans/{self._today_identifier(request)}",
            score=50.0,
            effort=1,
            cost=1,
            channel_fit={"sms": 3.0, "whatsapp": 4.0, "app": 5.0, "web": 5.0},
            reasons=["fallback"],
        )
        result = self._build_decision_payload(
            request,
            ScoredCandidate(candidate=candidate, final_score=candidate.score, score_breakdown={"base": candidate.score}),
            {"last_action_id": self._last_action_identifier(request)},
        )
        result.setdefault("metadata", {})["fallback"] = True
        return result

    def _last_action_identifier(self, request: NextBestActionInput) -> Optional[str]:
        if not request.recent_actions:
            return None
        first = request.recent_actions[0]
        return str(first.get("id") or first.get("timestamp") or first.get("at"))

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        if asyncio.iscoroutine(value):
            return await value
        return value

    def _build_candidates(self, request: NextBestActionInput, context: Dict[str, Any]) -> List[Candidate]:
        today_path = f"/plans/{self._today_identifier(request)}"
        candidates: List[Candidate] = []

        summary_reasons: List[str] = ["plan_overview"]
        if context.get("plan_freshness_hours") is not None and context["plan_freshness_hours"] < 12:
            summary_reasons.append("plan_recent")
        summary_candidate = Candidate(
            journey="today",
            primary_message=self._localize("today_primary", request.locale),
            cta_label=self._localize("today_cta", request.locale),
            path=today_path,
            score=68.0,
            effort=1,
            cost=1,
            channel_fit={"sms": 4.0, "whatsapp": 5.5, "app": 6.0, "web": 7.0},
            reasons=summary_reasons,
        )
        candidates.append(summary_candidate)

        quick_score = 72.0
        quick_reasons: List[str] = []
        last_delta = context.get("last_log_delta_hours")
        if last_delta is None or last_delta > 4:
            quick_score += 18.0
            quick_reasons.append("log_overdue")
        if context.get("skipped_meals"):
            quick_score += 6.0
            quick_reasons.append("meal_skipped")
        quick_candidate = Candidate(
            journey="quick_log",
            primary_message=self._localize("quick_log_primary", request.locale),
            cta_label=self._localize("quick_log_cta", request.locale),
            path="/track/quick",
            score=quick_score,
            effort=1,
            cost=0,
            channel_fit={"sms": 5.0, "whatsapp": 6.5, "app": 8.0, "web": 6.0},
            reasons=quick_reasons,
        )
        candidates.append(quick_candidate)

        groceries_score = 64.0
        groceries_reasons: List[str] = []
        if context.get("needs_groceries"):
            groceries_score += 18.0
            groceries_reasons.append("list_ready")
        if not context.get("grocery_completed"):
            groceries_reasons.append("not_completed")
        groceries_candidate = Candidate(
            journey="groceries",
            primary_message=self._localize("groceries_primary", request.locale),
            cta_label=self._localize("groceries_cta", request.locale),
            path="/groceries",
            score=groceries_score,
            effort=2,
            cost=1,
            channel_fit={"sms": 3.0, "whatsapp": 5.0, "app": 6.5, "web": 7.5},
            reasons=groceries_reasons,
            secondary={"label": self._localize("groceries_secondary_label", request.locale), "path": "/pantry"},
        )
        candidates.append(groceries_candidate)

        if context.get("swap_requested") or context.get("skipped_meals"):
            swaps_score = 66.0
            swaps_reasons: List[str] = ["swap_requested"]
            if context.get("cost_sensitive"):
                swaps_score += 4.0
                swaps_reasons.append("budget-aware")
            swaps_candidate = Candidate(
                journey="smart_swaps",
                primary_message=self._localize("smart_swaps_primary", request.locale),
                cta_label=self._localize("smart_swaps_cta", request.locale),
                path=f"{today_path}/swap",
                score=swaps_score,
                effort=2,
                cost=1,
                channel_fit={"sms": 4.0, "whatsapp": 5.5, "app": 7.5, "web": 7.5},
                reasons=swaps_reasons,
                secondary={"label": self._localize("swaps_secondary_label", request.locale), "path": today_path},
            )
            candidates.append(swaps_candidate)

        if context.get("streak_drop"):
            recovery_score = 62.0 + (4.0 if context.get("skipped_meals") else 0.0)
            recovery_candidate = Candidate(
                journey="recovery",
                primary_message=self._localize("recovery_primary", request.locale),
                cta_label=self._localize("recovery_cta", request.locale),
                path="/progress/recovery",
                score=recovery_score,
                effort=1,
                cost=0,
                channel_fit={"sms": 5.0, "whatsapp": 6.0, "app": 6.0, "web": 5.5},
                reasons=["streak_support"],
            )
            candidates.append(recovery_candidate)

        return candidates

    def _today_identifier(self, request: NextBestActionInput) -> str:
        tz = self._resolve_timezone(request.timezone)
        return self._now(tz).date().isoformat()

    def _localize(self, key: str, locale: str) -> str:
        lang = (locale or "en").split("-")[0].lower()
        mapping = _LOCALE_STRINGS.get(key, {})
        return mapping.get(lang) or mapping.get("en") or key

    @staticmethod
    def _parse_timestamp(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=ZoneInfo("UTC"))
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=ZoneInfo("UTC"))
        if isinstance(value, str):
            cleaned = value.replace("Z", "+00:00")
            try:
                dt_value = datetime.fromisoformat(cleaned)
                return dt_value if dt_value.tzinfo else dt_value.replace(tzinfo=ZoneInfo("UTC"))
            except ValueError:
                return None
        return None


_LOCALE_STRINGS: Dict[str, Dict[str, str]] = {
    "today_primary": {
        "en": "Your plan for today is ready—here's the next best step to stay on track.",
        "es": "Tu plan de hoy está listo: este es el siguiente paso para mantenerte al día.",
        "fr": "Votre plan du jour est prêt—voici la prochaine étape pour rester aligné.",
    },
    "today_cta": {
        "en": "View today",
        "es": "Ver hoy",
        "fr": "Voir aujourd'hui",
    },
    "quick_log_primary": {
        "en": "Two taps to log your last meal and keep your streak alive.",
        "es": "Dos toques para registrar tu última comida y mantener tu racha.",
        "fr": "Deux gestes pour enregistrer votre repas et garder votre série.",
    },
    "quick_log_cta": {
        "en": "Log meal",
        "es": "Registrar comida",
        "fr": "Enregistrer le repas",
    },
    "groceries_primary": {
        "en": "Your grocery list is grouped and ready whenever you are.",
        "es": "Tu lista de compras está organizada y lista cuando tú lo estés.",
        "fr": "Votre liste de courses est organisée et prête quand vous l'êtes.",
    },
    "groceries_cta": {
        "en": "Open groceries",
        "es": "Abrir compras",
        "fr": "Ouvrir les courses",
    },
    "groceries_secondary_label": {
        "en": "Check pantry",
        "es": "Revisar despensa",
        "fr": "Vérifier le garde-manger",
    },
    "smart_swaps_primary": {
        "en": "Need a quick swap? Here's a meal that still fits your plan.",
        "es": "¿Necesitas un cambio rápido? Aquí tienes una comida que sigue tu plan.",
        "fr": "Besoin d'un échange rapide ? Voici un repas qui respecte votre plan.",
    },
    "smart_swaps_cta": {
        "en": "Review swap",
        "es": "Revisar cambio",
        "fr": "Voir l'alternative",
    },
    "swaps_secondary_label": {
        "en": "View full plan",
        "es": "Ver plan completo",
        "fr": "Voir le plan complet",
    },
    "recovery_primary": {
        "en": "No stress about the pause—here's a gentle way to restart.",
        "es": "Sin estrés por la pausa: aquí tienes una forma suave de retomar.",
        "fr": "Pas de stress pour la pause—voici une reprise en douceur.",
    },
    "recovery_cta": {
        "en": "Restart gently",
        "es": "Reiniciar con calma",
        "fr": "Redémarrer en douceur",
    },
}


def _parse_time_of_day(value: Any) -> Optional[dt_time]:
    if isinstance(value, dt_time):
        return value
    if isinstance(value, (int, float)):
        hour = int(value) % 24
        return dt_time(hour=hour)
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%H:%M", "%H"):
            try:
                return datetime.strptime(text, fmt).time()
            except ValueError:
                continue
    return None
