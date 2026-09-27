from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.webhook_event_model import WebhookEvent


class WebhookEventRepository:

    def get_by_event_id(
        self,
        event_id: str,
        session: Session,
    ) -> Optional[WebhookEvent]:
        stmt = select(WebhookEvent).where(WebhookEvent.event_id == event_id)

        return session.scalar(stmt)

    def create(
        self,
        event_id: str,
        event_type: str,
        payload: dict,
        session: Session,
    ) -> WebhookEvent:

        event = WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            processed=False,
        )

        session.add(event)
        session.flush()

        return event

    def mark_processed(
        self,
        event: WebhookEvent,
        session: Session,
    ) -> WebhookEvent:

        event.processed = True
        event.processed_at = datetime.now(timezone.utc)

        session.flush()

        return event
