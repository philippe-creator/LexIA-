import io
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from api.core.dependencies import CurrentUser
from api.schemas.legal_documents import DocumentGenerationRequest
from generation.legal_documents import list_document_types, build_document
from generation.document_renderers import render_docx, render_pdf

router = APIRouter(prefix="/legal-documents", tags=["Documents juridiques"])

_FORMATS = {
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", render_docx),
    "pdf": ("application/pdf", render_pdf),
}


@router.get("/types")
async def get_document_types(current_user: CurrentUser):
    """Liste les modèles disponibles et leurs champs (pour construire le formulaire)."""
    return {"types": list_document_types()}


@router.post("/{doc_type}/preview")
async def preview_document(doc_type: str, request: DocumentGenerationRequest, current_user: CurrentUser):
    """Construit le document et renvoie ses blocs pour un aperçu à l'écran."""
    try:
        return build_document(doc_type, request.data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{doc_type}/download")
async def download_document(
    doc_type: str,
    request: DocumentGenerationRequest,
    current_user: CurrentUser,
    format: str = Query("docx", pattern="^(docx|pdf)$"),
):
    """Génère et télécharge le document au format DOCX ou PDF."""
    try:
        document = build_document(doc_type, request.data)
    except ValueError as e:
        raise HTTPException(400, str(e))

    media_type, renderer = _FORMATS[format]
    content = renderer(document)
    filename = f"{document['filename']}.{format}"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
