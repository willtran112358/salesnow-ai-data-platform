"""Write crawled records to S3 bronze layer with date partitioning."""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def bronze_s3_key(source: str, entity: str, ts: datetime | None = None) -> str:
    """Generate partitioned S3 key for bronze landing zone."""
    ts = ts or datetime.now(timezone.utc)
    return (
        f"bronze/{source}/{entity}/"
        f"dt={ts.strftime('%Y-%m-%d')}/hour={ts.strftime('%H')}/"
        f"part-{uuid4().hex}.jsonl.gz"
    )


def serialize_records(records: list[dict[str, Any]]) -> bytes:
    """Serialize records to gzipped JSON Lines."""
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    payload = "\n".join(lines).encode("utf-8")
    return gzip.compress(payload)
