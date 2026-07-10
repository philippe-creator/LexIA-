import difflib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.core.database import get_db
from api.core.dependencies import CurrentUser
from api.schemas.chat import CompareRequest, SnapshotInfo
from api.repositories.snapshot_repo import list_snapshots, get_snapshot
from processing.indexer import DOMAINS

router = APIRouter(prefix="/compare", tags=["Comparaison"])


def _validate_domain(domain: str) -> str:
    if domain not in DOMAINS:
        raise HTTPException(400, f"Domaine invalide : {domain}")
    return domain


@router.get("/versions/{domain}", response_model=list[SnapshotInfo])
async def list_versions(domain: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    _validate_domain(domain)
    rows = list_snapshots(db, domain)
    return [SnapshotInfo(id=r.id, filename=r.filename, created_at=r.created_at.isoformat(), char_count=r.char_count) for r in rows]


@router.post("/")
async def compare(request: CompareRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    s1 = get_snapshot(db, request.snapshot_id_1)
    s2 = get_snapshot(db, request.snapshot_id_2)
    if not s1: raise HTTPException(404, "Version 1 introuvable.")
    if not s2: raise HTTPException(404, "Version 2 introuvable.")
    if s1.domain != s2.domain:
        raise HTTPException(400, "Les deux versions doivent appartenir au même domaine juridique.")

    t1, t2 = s1.full_text.splitlines(), s2.full_text.splitlines()
    blocks = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, t1, t2).get_opcodes():
        if tag == "insert":
            blocks.append({"type": "added", "lines_v1": [], "lines_v2": t2[j1:j2], "line_number_v1": i1 + 1, "line_number_v2": j1 + 1})
        elif tag == "delete":
            blocks.append({"type": "removed", "lines_v1": t1[i1:i2], "lines_v2": [], "line_number_v1": i1 + 1, "line_number_v2": j1 + 1})
        elif tag == "replace":
            blocks.append({"type": "changed", "lines_v1": t1[i1:i2], "lines_v2": t2[j1:j2], "line_number_v1": i1 + 1, "line_number_v2": j1 + 1})

    added = sum(len(b["lines_v2"]) for b in blocks if b["type"] == "added")
    removed = sum(len(b["lines_v1"]) for b in blocks if b["type"] == "removed")
    changed = len([b for b in blocks if b["type"] == "changed"])
    parts = ([f"{added} ligne(s) ajoutée(s)"] if added else []) + ([f"{removed} ligne(s) supprimée(s)"] if removed else []) + ([f"{changed} section(s) modifiée(s)"] if changed else [])
    summary = f"{s1.filename} → {s2.filename} : {', '.join(parts)}." if parts else "Aucune différence détectée."

    return {
        "filename_v1": s1.filename, "filename_v2": s2.filename, "domain": s1.domain,
        "total_added": added, "total_removed": removed, "total_changed": changed,
        "diff_blocks": blocks[:200], "summary": summary,
    }
