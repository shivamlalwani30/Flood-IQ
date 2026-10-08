"""
routers/verification.py

POST /verify — "Judge Verification Mode". Re-runs the actual core test
suite live and returns real results. See core/verification.py for what
this actually executes.
"""

from fastapi import APIRouter

from core.verification import run_full_verification

router = APIRouter(tags=["verification"])


@router.post("/verify")
def verify():
    """
    Runs the full live verification suite and returns the results.
    Safe to call repeatedly — it's read-mostly (the input-validation check
    confirms it never mutates zone state, since set_flood_depth rejects
    bad input before touching state at all) and takes roughly 1-4 seconds
    depending on whether the ML model needs to be loaded from disk first.
    """
    return run_full_verification()


@router.get("/incident-report")
def incident_report():
    """
    Generates a point-in-time incident report (JSON) from current live
    state — active flood zones, vehicle status, and 6h predictions.
    Demonstrates the data structure that would feed an NDMA Integrated
    Control Room or State Disaster Management Authority dashboard.
    """
    from core.incident_report import generate_incident_report
    return generate_incident_report()


@router.get("/incident-report/markdown")
def incident_report_markdown():
    """Same report, rendered as a downloadable Markdown document."""
    from fastapi.responses import PlainTextResponse
    from core.incident_report import generate_incident_report, render_report_markdown

    report = generate_incident_report()
    md = render_report_markdown(report)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{report["report_id"]}.md"'},
    )


@router.post("/reset")
async def reset():
    """
    Demo-day recovery: clears every flood zone back to dry and removes
    all vehicles, without restarting the backend process. Broadcasts the
    change to every connected WebSocket client so their local state
    actually reflects the reset, not just whoever called this endpoint.
    """
    from core.state import state
    from core.websocket_manager import manager

    state.reset_all()
    await manager.broadcast("state_reset", {"message": "All zones dry, all vehicles cleared."})
    return {"status": "ok", "message": "All zones dry, all vehicles cleared."}
