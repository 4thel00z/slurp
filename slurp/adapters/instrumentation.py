import logging

import logfire


logger = logging.getLogger(__name__)


def setup_instrumentation(token: str | None) -> None:
    """Configure logfire instrumentation when a token is provided."""
    if not token:
        logger.info("No logfire token provided, skipping instrumentation setup.")
        return
    logfire.configure(token=token)
    logfire.instrument_httpx()
    logfire.instrument_requests()
    logfire.instrument_sqlalchemy()
