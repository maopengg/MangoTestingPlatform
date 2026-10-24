from decimal import Decimal, InvalidOperation

from math import ceil

from src.apps.perf.enums import PerfLoadTypeEnum
from src.apps.perf.exceptions import (
    PERF_SCENARIO_CONFIG_PERF_INVALID,
    PerfError,
)


class PerfLoadStageService:
    """Persist one load profile; expand it to k6 stages at compile time."""

    PROFILE_TYPES = {
        "constant_concurrency": PerfLoadTypeEnum.CONCURRENCY.value,
        "fixed_iterations": PerfLoadTypeEnum.CONCURRENCY.value,
        "staircase": PerfLoadTypeEnum.CONCURRENCY.value,
        "linear_ramp": PerfLoadTypeEnum.CONCURRENCY.value,
        "spike": PerfLoadTypeEnum.CONCURRENCY.value,
        "soak": PerfLoadTypeEnum.CONCURRENCY.value,
        "constant_arrival_rate": PerfLoadTypeEnum.ARRIVAL_RATE.value,
        "constant_iteration_rate": PerfLoadTypeEnum.ITERATION_RATE.value,
    }
    RATE_PROFILES = {"constant_arrival_rate", "constant_iteration_rate"}
    FIELD_NAMES = ("total_iterations", "start_users", "step_users", "step_interval_seconds",
                   "ramp_seconds", "hold_seconds", "baseline_seconds", "recovery_seconds")

    @classmethod
    def default_payload(cls, load_type=PerfLoadTypeEnum.CONCURRENCY.value) -> dict:
        rate = load_type != PerfLoadTypeEnum.CONCURRENCY.value
        profile = ("constant_concurrency" if not rate else "constant_arrival_rate"
        if load_type == PerfLoadTypeEnum.ARRIVAL_RATE.value else "constant_iteration_rate")
        return {"name": "基础负载", "profile": profile, "duration_seconds": 60,
                "target_users": None if rate else 10, "target_rate": 10 if rate else None,
                "rate_time_unit": "second" if rate else None, "preallocated_vus": 10 if rate else None,
                "max_vus": 100 if rate else None, "ramp_type": "step", "spawn_rate": None,
                "user_wait_min_ms": 0, "user_wait_max_ms": 0,
                **{key: None for key in cls.FIELD_NAMES}}

    @classmethod
    def serialize(cls, scenario) -> dict:
        profile = scenario.load_profile
        if cls.PROFILE_TYPES.get(profile) != scenario.load_type:
            profile = cls.default_payload(scenario.load_type)["profile"]
        return {"name": scenario.load_name, "profile": profile, "duration_seconds": scenario.duration_seconds,
                "target_users": scenario.target_users,
                "target_rate": float(scenario.target_rate) if scenario.target_rate is not None else None,
                "rate_time_unit": scenario.rate_time_unit, "preallocated_vus": scenario.preallocated_vus,
                "max_vus": scenario.max_vus, "ramp_type": scenario.ramp_type,
                "spawn_rate": float(scenario.spawn_rate) if scenario.spawn_rate is not None else None,
                "user_wait_min_ms": scenario.user_wait_min_ms,
                "user_wait_max_ms": scenario.user_wait_max_ms,
                **{key: getattr(scenario, key) for key in cls.FIELD_NAMES}}

    @staticmethod
    def _invalid(message):
        raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=(f"负载配置无效：{message}",))

    @classmethod
    def _integer(cls, payload, key, label, *, minimum=1, default=None):
        value = payload.get(key, default)
        if value is None and default is not None:
            value = default
        if value is None or value == "":
            cls._invalid(f"请填写{label}")
        try:
            number = int(value)
            if str(number) != str(value).strip():
                raise ValueError
        except (TypeError, ValueError):
            cls._invalid(f"{label}必须是整数")
        if number < minimum or number > 1_000_000_000:
            cls._invalid(f"{label}必须在 {minimum}～1000000000 之间")
        return number

    @classmethod
    def normalize_payload(cls, payload: dict, executor_count: int = 1) -> dict:
        profile = payload.get("profile") or "constant_concurrency"
        load_type = cls.PROFILE_TYPES.get(profile)
        if not load_type:
            cls._invalid("请选择有效的压测方案")
        name = str(payload.get("name", "基础负载") or "").strip()
        if not name or len(name) > 64:
            cls._invalid("配置名称不能为空且不能超过 64 字")
        result = {"load_profile": profile, "load_type": load_type, "load_name": name,
                  "target_users": None, "target_rate": None, "rate_time_unit": None,
                  "preallocated_vus": None, "max_vus": None, "ramp_type": "step", "spawn_rate": None,
                  **{key: None for key in cls.FIELD_NAMES}}
        wait_min = cls._integer(payload, "user_wait_min_ms", "最小迭代等待", minimum=0, default=0)
        wait_max = cls._integer(payload, "user_wait_max_ms", "最大迭代等待", minimum=0, default=0)
        if wait_max < wait_min or wait_max > 3_600_000:
            cls._invalid("最大迭代等待不能小于最小值，且不能超过 3600000 ms")
        result.update(user_wait_min_ms=wait_min, user_wait_max_ms=wait_max)
        if profile in cls.RATE_PROFILES:
            try:
                rate = Decimal(str(payload.get("target_rate")))
            except (InvalidOperation, TypeError):
                cls._invalid("目标速率必须是正数")
            if not rate.is_finite() or rate <= 0 or rate > 10_000_000:
                cls._invalid("目标速率必须在 0～10000000 之间")
            unit = payload.get("rate_time_unit") or "second"
            if unit not in ("second", "minute"):
                cls._invalid("速率单位无效")
            rate_per_minute = rate * (1 if unit == "minute" else 60)
            if rate_per_minute < executor_count:
                cls._invalid("每分钟目标速率不能低于执行器数量，否则多节点会超发")
            if rate_per_minute != int(rate_per_minute):
                cls._invalid("目标速率换算为每分钟后必须是整数")
            preallocated = cls._integer(payload, "preallocated_vus", "预分配 VU")
            maximum = cls._integer(payload, "max_vus", "最大 VU")
            if maximum < preallocated or preallocated < executor_count:
                cls._invalid("最大 VU 不得小于预分配 VU，预分配 VU 不得少于执行器数")
            result.update(target_rate=rate, rate_time_unit=unit, preallocated_vus=preallocated, max_vus=maximum)
        else:
            users = cls._integer(payload, "target_users", "目标并发")
            if users < executor_count:
                cls._invalid("目标并发不能少于执行器数量")
            result["target_users"] = users
            if profile == "fixed_iterations":
                iterations = cls._integer(payload, "total_iterations", "总执行次数")
                if iterations < users:
                    cls._invalid("总执行次数不能少于目标并发用户数")
                result["total_iterations"] = iterations
            elif profile == "staircase":
                step = cls._integer(payload, "step_users", "每阶增加用户数")
                interval = cls._integer(payload, "step_interval_seconds", "阶梯间隔")
                hold = cls._integer(payload, "hold_seconds", "峰值保持时间", minimum=0, default=0)
                if step < executor_count or ceil(users / step) > 99:
                    cls._invalid("每阶增加用户数不能少于执行器数，且最多 99 阶")
                result.update(step_users=step, step_interval_seconds=interval, hold_seconds=hold)
            elif profile == "linear_ramp":
                start = cls._integer(payload, "start_users", "起始并发", minimum=0)
                ramp = cls._integer(payload, "ramp_seconds", "爬坡时间")
                hold = cls._integer(payload, "hold_seconds", "峰值保持时间", minimum=0, default=0)
                if start >= users:
                    cls._invalid("起始并发必须小于目标并发")
                result.update(start_users=start, ramp_seconds=ramp, hold_seconds=hold, ramp_type="linear")
            elif profile == "spike":
                start = cls._integer(payload, "start_users", "基线并发")
                if start < executor_count or start >= users:
                    cls._invalid("基线并发必须小于峰值且不少于执行器数")
                result.update(start_users=start,
                              baseline_seconds=cls._integer(payload, "baseline_seconds", "基线时间"),
                              ramp_seconds=cls._integer(payload, "ramp_seconds", "突刺上升时间"),
                              hold_seconds=cls._integer(payload, "hold_seconds", "峰值保持时间"),
                              recovery_seconds=cls._integer(payload, "recovery_seconds", "恢复时间"),
                              ramp_type="linear")
        if profile == "staircase":
            duration = ceil(result["target_users"] / result["step_users"]) * result["step_interval_seconds"] + result[
                "hold_seconds"]
        elif profile == "linear_ramp":
            duration = result["ramp_seconds"] + result["hold_seconds"]
        elif profile == "spike":
            duration = sum(
                result[key] for key in ("baseline_seconds", "ramp_seconds", "hold_seconds", "recovery_seconds"))
        else:
            duration = cls._integer(payload, "duration_seconds", "持续时间")
        if duration < 1 or duration > 86400:
            cls._invalid("总时长必须在 1 秒到 24 小时之间")
        result["duration_seconds"] = duration
        return result

    @classmethod
    def build_stages(cls, scenario) -> list[dict]:
        config = cls.normalize_payload(cls.serialize(scenario), scenario.default_executor_count)
        profile = config["load_profile"]
        common = {"target_rate": float(config["target_rate"]) if config["target_rate"] is not None else None,
                  "rate_time_unit": config["rate_time_unit"], "preallocated_vus": config["preallocated_vus"],
                  "max_vus": config["max_vus"], "spawn_rate": None}
        stages = []

        def add(name, seconds, users=None, ramp="step"):
            if seconds:
                stages.append({"stage_key": f"load-{len(stages) + 1}", "name": name,
                               "duration_seconds": seconds, "target_users": users,
                               "ramp_type": ramp, **common})

        users = config["target_users"]
        if profile == "staircase":
            for target in range(config["step_users"], users, config["step_users"]):
                add(f"阶梯 {len(stages) + 1}", config["step_interval_seconds"], target)
            add("目标阶梯", config["step_interval_seconds"], users)
            add("峰值保持", config["hold_seconds"], users)
        elif profile == "linear_ramp":
            add("线性爬坡", config["ramp_seconds"], users, "linear")
            add("峰值保持", config["hold_seconds"], users)
        elif profile == "spike":
            add("基线", config["baseline_seconds"], config["start_users"])
            add("突刺上升", config["ramp_seconds"], users, "linear")
            add("峰值保持", config["hold_seconds"], users)
            add("恢复", config["recovery_seconds"], config["start_users"], "linear")
        else:
            add(config["load_name"], config["duration_seconds"], users)
        return stages
