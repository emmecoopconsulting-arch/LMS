import json
from sqlalchemy.orm import Session
from app.models import AuditLog


def write_audit(
    db: Session,
    actor_user_id: int | None,
    action: str,
    entity: str,
    entity_id: str,
    metadata: dict | None = None,
) -> None:
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata or {}),
    )
    db.add(log)
    db.commit()
