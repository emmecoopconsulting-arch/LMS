from sqlalchemy.orm import Session
from app.models import Setting


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(Setting, key)
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if not row:
        row = Setting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
