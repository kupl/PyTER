from monkeytype.config import DefaultConfig
from monkeytype import trace

from monkeytype.tracing import CallTracer

CONFIG = DefaultConfig()

logger = CONFIG.trace_logger()
tracer = CallTracer(
    logger=logger,
    max_typed_dict_size = CONFIG.max_typed_dict_size(),
    code_filter = CONFIG.code_filter(),
    sample_rate = CONFIG.sample_rate()
)


with trace() :
    a = 3
    print(a)
    print(CONFIG)