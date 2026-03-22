"""
API Router - Sessions de tracking
"""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db, Runner, Session as TrackSession

router = APIRouter()


class SessionCreate(BaseModel):
    runner_id: int


@router.post("/sessions", response_model=dict, status_code=201)
async def start_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Démarre une session de tracking pour un coureur."""
    runner = await db.get(Runner, body.runner_id)
    if not runner:
        raise HTTPException(404, detail="Coureur introuvable")

    # Fermer sessions actives existantes
    await db.execute(
        update(TrackSession)
        .where(TrackSession.runner_id == body.runner_id, TrackSession.is_active == True)
        .values(is_active=False, ended_at=datetime.now(timezone.utc))
    )

    session = TrackSession(runner_id=body.runner_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"id": session.id, "runner_id": body.runner_id, "started_at": session.started_at.isoformat()}


@router.delete("/sessions/{session_id}")
async def stop_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Arrête une session de tracking."""
    session = await db.get(TrackSession, session_id)
    if not session:
        raise HTTPException(404, detail="Session introuvable")
    session.is_active = False
    session.ended_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Session terminée", "distance_m": session.total_distance_m}


@router.get("/sessions/{session_id}")
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    session = await db.get(TrackSession, session_id)
    if not session:
        raise HTTPException(404, detail="Session introuvable")
    return {
        "id": session.id,
        "runner_id": session.runner_id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "is_active": session.is_active,
        "total_distance_m": session.total_distance_m,
        "total_distance_km": round((session.total_distance_m or 0) / 1000, 3)
    }


@router.get("/runners/{runner_id}/sessions")
async def get_runner_sessions(runner_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrackSession).where(TrackSession.runner_id == runner_id))
    sessions = result.scalars().all()
    return [
        {"id": s.id, "started_at": s.started_at.isoformat() if s.started_at else None,
         "is_active": s.is_active, "distance_m": s.total_distance_m}
        for s in sessions
    ]
