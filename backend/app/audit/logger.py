from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.audit.models import AuditRecord, Base, SecurityEvent


class AuditStore:
    def __init__(self, database_url: str) -> None:
        if database_url.startswith("sqlite:///") and not database_url.endswith(":memory:"):
            path = database_url.removeprefix("sqlite:///")
            if path and path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, connect_args=connect_args)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def save_record(self, **values) -> None:
        with self.sessions() as session:
            session.add(AuditRecord(**values))
            session.commit()

    def save_security_event(
        self, request_id: str, event_type: str, details: dict
    ) -> None:
        with self.sessions() as session:
            session.add(
                SecurityEvent(
                    request_id=request_id,
                    event_type=event_type,
                    details=json.dumps(details, separators=(",", ":")),
                )
            )
            session.commit()

    @staticmethod
    def _record_dict(record: AuditRecord) -> dict:
        return {
            "request_id": record.request_id,
            "timestamp": record.timestamp.isoformat(),
            "status": record.status,
            "entity_counts": json.loads(record.entity_counts),
            "outbound_payload": record.outbound_payload,
            "provider": record.provider,
            "model": record.model,
            "leakage_verified": record.leakage_verified,
            "processing_latency_ms": record.processing_latency_ms,
            "restoration_status": json.loads(record.restoration_status),
            "security_events": json.loads(record.security_events),
        }

    def get(self, request_id: str) -> dict | None:
        with self.sessions() as session:
            record = session.get(AuditRecord, request_id)
            if record is None:
                return None
            result = self._record_dict(record)
            result["security_events"] = self._security_events(session, request_id)
            return result

    @staticmethod
    def _security_events(session: Session, request_id: str) -> list[dict]:
        events = session.scalars(
            select(SecurityEvent)
            .where(SecurityEvent.request_id == request_id)
            .order_by(SecurityEvent.timestamp)
        ).all()
        return [
            {
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "details": json.loads(event.details),
            }
            for event in events
        ]

    def list_recent(self, limit: int = 50) -> list[dict]:
        with self.sessions() as session:
            records = session.scalars(
                select(AuditRecord)
                .order_by(AuditRecord.timestamp.desc())
                .limit(limit)
            ).all()
            result = []
            for record in records:
                item = self._record_dict(record)
                item["security_events"] = self._security_events(
                    session, record.request_id
                )
                result.append(item)
            return result

    def metrics(self) -> dict:
        with self.sessions() as session:
            total = session.scalar(select(func.count()).select_from(AuditRecord)) or 0
            blocked = session.scalar(
                select(func.count())
                .select_from(AuditRecord)
                .where(AuditRecord.status == "blocked")
            ) or 0
            failed = session.scalar(
                select(func.count())
                .select_from(AuditRecord)
                .where(AuditRecord.status == "failed")
            ) or 0
            average = session.scalar(
                select(func.avg(AuditRecord.processing_latency_ms))
            ) or 0.0

            # Calculate live entity totals and trends from real audit records
            records = session.scalars(
                select(AuditRecord).order_by(AuditRecord.timestamp.desc()).limit(200)
            ).all()

            category_counter: dict[str, int] = {}
            trend_map: dict[str, int] = {}
            total_pii = 0
            errors_count = 0

            for rec in records:
                day_str = rec.timestamp.strftime("%b %d")
                trend_map[day_str] = trend_map.get(day_str, 0) + 1

                if rec.status in {"failed", "blocked"}:
                    errors_count += 1

                try:
                    counts = json.loads(rec.entity_counts)
                    if isinstance(counts, dict):
                        for cat, cnt in counts.items():
                            val = int(cnt)
                            category_counter[cat] = category_counter.get(cat, 0) + val
                            total_pii += val
                except Exception:
                    pass

            pii_by_category = [
                {"name": cat, "value": count}
                for cat, count in sorted(category_counter.items(), key=lambda x: x[1], reverse=True)
            ]

            request_trend = [
                {"day": day, "requests": count}
                for day, count in reversed(list(trend_map.items())[-7:])
            ]

            return {
                "total_requests": int(total),
                "leakage_blocked": int(blocked),
                "failed_requests": int(failed),
                "average_processing_latency_ms": round(float(average), 2),
                "total_pii_detected": total_pii,
                "documents_with_errors": errors_count,
                "pii_by_category": pii_by_category,
                "request_trend": request_trend,
                "language_distribution": {"English": total},
                "risk_distribution": {"High": blocked, "Medium": errors_count - blocked, "Low": max(0, total - errors_count)},
            }
