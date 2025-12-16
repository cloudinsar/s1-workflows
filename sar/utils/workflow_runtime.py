import os
import typing
from typing import Type, Union

# File derived from runtime.py from openeo-geopyspark-driver
ENV_VAR_OPENEO_BATCH_JOB_ID = "OPENEO_BATCH_JOB_ID"


def _is_exception_like(value) -> bool:
    """Is given value an exception or exception type (so that it can be raised)?"""
    return isinstance(value, Exception) or (isinstance(value, type) and issubclass(value, Exception))


def get_job_id(*, default: Union[None, str] = None) -> Union[str, None]:
    """
    Get job id from batch job context,
    or a default/exception if not in batch job context.
    """
    return os.environ.get(ENV_VAR_OPENEO_BATCH_JOB_ID, default)


def in_batch_job_context() -> bool:
    return bool(get_job_id(default=None))
