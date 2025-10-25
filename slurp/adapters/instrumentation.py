import os
from dataclasses import dataclass
from logging import info

import logfire


@dataclass
class InstrumentationConfig:
    token: str

    @staticmethod
    def from_env() -> "InstrumentationConfig":
        return InstrumentationConfig(os.environ.get("LOGFIRE_TOKEN", ""))

    def setup(self):
        """Sets up the instrumentation with the provided FastAPI app."""
        if not self.token:
            info("No LOGFIRE_TOKEN provided, skipping instrumentation setup.")
            return
        logfire.configure(token=self.token)
        logfire.instrument_httpx()
        logfire.instrument_requests()
        logfire.instrument_sqlalchemy()
