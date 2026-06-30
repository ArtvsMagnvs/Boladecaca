# Config API Endpoints
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import Config
from app.db.schemas import ConfigCreate, ConfigResponse

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/", response_model=List[ConfigResponse])
def get_all_config(db: Session = Depends(get_db)):
    """Get all configuration key/value pairs."""
    return db.query(Config).all()


@router.get("/{key}", response_model=ConfigResponse)
def get_config(key: str, db: Session = Depends(get_db)):
    """Get a single configuration value by key."""
    config = db.query(Config).filter(Config.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config key not found")
    return config


@router.post("/", response_model=ConfigResponse)
def create_or_update_config(config_data: ConfigCreate, db: Session = Depends(get_db)):
    """Create a configuration key, or update its value if it already exists."""
    existing = db.query(Config).filter(Config.key == config_data.key).first()
    if existing:
        existing.value = config_data.value
        db.commit()
        db.refresh(existing)
        return existing

    new_config = Config(key=config_data.key, value=config_data.value)
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return new_config
