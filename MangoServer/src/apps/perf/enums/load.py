from src.common.enums.base import BaseEnum


class PerfLoadTypeEnum(BaseEnum):
    CONCURRENCY = ("concurrency", "并发用户")
    ARRIVAL_RATE = ("arrival_rate", "到达率")
    ITERATION_RATE = ("iteration_rate", "迭代率")


class PerfLoadProfileEnum(BaseEnum):
    CONSTANT_CONCURRENCY = ("constant_concurrency", "固定并发")
    FIXED_ITERATIONS = ("fixed_iterations", "定量任务")
    STAIRCASE = ("staircase", "阶梯加压")
    LINEAR_RAMP = ("linear_ramp", "线性爬坡")
    SPIKE = ("spike", "突刺测试")
    SOAK = ("soak", "长稳态测试")
    CONSTANT_ARRIVAL_RATE = ("constant_arrival_rate", "固定到达率")
    CONSTANT_ITERATION_RATE = ("constant_iteration_rate", "固定迭代率")
