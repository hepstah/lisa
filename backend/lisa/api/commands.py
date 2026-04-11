from fastapi import APIRouter
from lisa.models import TextCommandRequest, CommandRecord
from lisa.api.ws import manager
from lisa.db import get_db

router = APIRouter(prefix="/api/commands", tags=["commands"])

device_service = None  # Set in main.py


@router.get("/history", response_model=list[CommandRecord])
async def get_command_history(limit: int = 50, offset: int = 0):
    """Get command history with error details. Per DASH-02, ERR-02."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM command_log ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            CommandRecord(
                id=r["id"],
                timestamp=r["timestamp"],
                source=r["source"],
                raw_input=r["raw_input"],
                device_id=r["device_id"],
                action=r["action"],
                status=r["status"],
                error_message=r["error_message"],
                error_stage=r["error_stage"],
                duration_ms=r["duration_ms"],
            )
            for r in rows
        ]
    finally:
        await db.close()


@router.post("/text", response_model=dict)
async def text_command(req: TextCommandRequest):
    """Process a typed text command. Per DASH-04.

    Simple parser for Phase 1. Matches: 'turn on/off [the] {device_alias}'.
    Phase 2 replaces this with LLM intent parsing.
    """
    text = req.text.strip().lower()

    # Parse action
    action = None
    if text.startswith("turn on"):
        action = "turn_on"
        remainder = text[len("turn on") :].strip()
    elif text.startswith("turn off"):
        action = "turn_off"
        remainder = text[len("turn off") :].strip()

    if not action:
        # Unknown command pattern
        log = await _log_unknown(req.text, req.source)
        await manager.broadcast({"type": "command_logged", "command": log})
        return log

    # Remove optional "the"
    if remainder.startswith("the "):
        remainder = remainder[4:]

    # Match against known device aliases
    device_id = await _match_device_alias(remainder)
    if not device_id:
        log = await _log_no_match(req.text, req.source, remainder)
        await manager.broadcast({"type": "command_logged", "command": log})
        return log

    # Execute through device service
    new_state, log = await device_service.execute_command(
        device_id=device_id,
        action=action,
        source=req.source,
        raw_input=req.text,
    )
    if new_state:
        await manager.broadcast(
            {
                "type": "device_state",
                "device_id": new_state.device_id,
                "alias": new_state.alias,
                "is_on": new_state.is_on,
                "is_reachable": new_state.is_reachable,
            }
        )
    await manager.broadcast({"type": "command_logged", "command": log})
    return log


async def _match_device_alias(query: str) -> str | None:
    """Find device_id by fuzzy alias match."""
    states = await device_service.get_all_states()
    query = query.lower().strip()
    for s in states:
        if s.alias.lower() == query:
            return s.device_id
    # Partial match fallback
    for s in states:
        if query in s.alias.lower() or s.alias.lower() in query:
            return s.device_id
    return None


async def _log_unknown(text: str, source: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO command_log (source, raw_input, status, error_message, error_stage)
               VALUES (?, ?, 'rejected', 'Could not understand that command. Try something like: turn on the bedroom lamp', 'validation')""",
            (source, text),
        )
        await db.commit()
        return {
            "id": cursor.lastrowid,
            "source": source,
            "raw_input": text,
            "status": "rejected",
            "error_message": "Could not understand that command. Try something like: turn on the bedroom lamp",
            "error_stage": "validation",
        }
    finally:
        await db.close()


async def _log_no_match(text: str, source: str, query: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO command_log (source, raw_input, status, error_message, error_stage)
               VALUES (?, ?, 'rejected', ?, 'validation')""",
            (source, text, f"No device found matching '{query}'"),
        )
        await db.commit()
        return {
            "id": cursor.lastrowid,
            "source": source,
            "raw_input": text,
            "status": "rejected",
            "error_message": f"No device found matching '{query}'",
            "error_stage": "validation",
        }
    finally:
        await db.close()
