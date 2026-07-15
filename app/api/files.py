"""GET /api/files/{id} — téléchargement des .docx générés."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.files.store import get_file

router = APIRouter()

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/api/files/{file_id}")
def download_file(file_id: str) -> Response:
    f = get_file(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return Response(
        content=f["content"],
        media_type=DOCX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{f["filename"]}"'},
    )
