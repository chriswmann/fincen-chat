import inspect

from typing import Callable
from functools import wraps
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


def instrument(fn: Callable) -> Callable:
    """Instrument a function, whether it's async or not."""
    if inspect.iscoroutinefunction(fn):

        @wraps(fn)
        async def async_wrapper(*args, **kwargs) -> Callable:
            with tracer.start_as_current_span(fn.__name__) as span:
                span.set_attribute("args", str(args))
                span.set_attribute("kwargs", str(kwargs))

                return await fn(*args, **kwargs)

        return async_wrapper

    else:

        @wraps(fn)
        def sync_wrapper(*args, **kwargs) -> Callable:
            with tracer.start_as_current_span(fn.__name__) as span:
                span.set_attribute("args", str(args))
                span.set_attribute("kwargs", str(kwargs))

                return fn(*args, **kwargs)

        return sync_wrapper
