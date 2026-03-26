from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(tags=["ui"])

_UI_DIR = Path(__file__).resolve().parents[1] / "ui"
_TEMPLATE_PATH = _UI_DIR / "templates" / "ui.html"
_STATIC_DIR = _UI_DIR / "static"
_ALLOWED_ASSETS = {
    "ui.css": "text/css; charset=utf-8",
    "ui.js": "application/javascript; charset=utf-8",
    "ui_payload.js": "application/javascript; charset=utf-8",
    "ui_status.js": "application/javascript; charset=utf-8",
    "ui_svg.js": "application/javascript; charset=utf-8",
}


def _load_ui_html() -> str:
    if not _TEMPLATE_PATH.exists():
        raise RuntimeError(f"UI template not found: {_TEMPLATE_PATH}")
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


UI_HTML = _load_ui_html()


@router.get("/ui", response_class=HTMLResponse)
def ui_page() -> HTMLResponse:
    return HTMLResponse(content=UI_HTML)


@router.get("/ui/static/{asset_name}")
def ui_asset(asset_name: str) -> FileResponse:
    media_type = _ALLOWED_ASSETS.get(asset_name)
    if media_type is None:
        raise HTTPException(status_code=404, detail="asset_not_found")

    asset_path = _STATIC_DIR / asset_name
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="asset_not_found")

    return FileResponse(asset_path, media_type=media_type)
