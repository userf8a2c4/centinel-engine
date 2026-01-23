"""Honduras JSON data source implementation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base import DataSource, SourceData

logger = logging.getLogger(__name__)


class HondurasJsonDataSource(DataSource):
    """Fetch Honduras election JSON data from configured endpoints."""

    def fetch_current_data(self) -> List[SourceData]:
        datasource_cfg = self.config
        sources = datasource_cfg.get("sources", [])
        headers = datasource_cfg.get("headers", {})
        timeout = int(datasource_cfg.get("timeout_seconds", 15))
        retries = int(datasource_cfg.get("retries", 3))
        fetched_at = datetime.now(timezone.utc).isoformat()

        session = self._build_session(retries=retries)
        payloads: List[SourceData] = []
        for source in sources:
            endpoint = source.get("endpoint")
            if not endpoint:
                logger.warning("missing_endpoint source=%s", source.get("name"))
                continue
            response = session.get(endpoint, headers=headers, timeout=timeout)
            response.raise_for_status()
            raw_data = response.json()
            payloads.append(
                SourceData(
                    name=source.get("name", "unknown"),
                    scope=source.get("scope", "NATIONAL"),
                    endpoint=endpoint,
                    level=source.get("level", "PRES"),
                    department_code=str(source.get("department_code", "00")),
                    fetched_at_utc=fetched_at,
                    raw_data=raw_data,
                )
            )

        return payloads

    @staticmethod
    def _build_session(retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
