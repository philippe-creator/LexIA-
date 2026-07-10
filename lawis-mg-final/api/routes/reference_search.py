import re
from fastapi import APIRouter, HTTPException
from api.core.dependencies import CurrentUser
from api.schemas.chat import ReferenceRequest, safe_url
from retrieval.keyword_search import keyword_search
from retrieval.vector_search import vector_search
from processing.indexer import DOMAINS

router = APIRouter(prefix="/reference", tags=["Référence"])
PATTERNS = [r"(?i)loi\s+(?:n°?\s*)?\d+[-./]\d+",r"(?i)dahir\s+(?:n°?\s*)?\d+[-./]\d+[-./]\d+",r"(?i)article\s+\d+",r"(?i)(?:CGI|Code\s+Général\s+des\s+Impôts)\s*\d{4}",r"(?i)(?:code\s+du\s+travail|loi\s+65-99)",r"(?i)(?:loi\s+de\s+finances)\s*\d{4}",r"(?i)note\s+circulaire\s+(?:n°?\s*)?\d+"]

def detect_refs(text):
    found=[]
    for p in PATTERNS: found.extend(re.findall(p,text))
    return list(set(found)) or [text]

def classify_ref(ref):
    r=ref.lower()
    if "article" in r: return "article"
    if "dahir" in r: return "dahir"
    if "décret" in r: return "décret"
    if "loi de finances" in r: return "loi_de_finances"
    return "loi"

@router.post("/")
async def search_reference(request: ReferenceRequest, current_user: CurrentUser):
    if request.domain and request.domain not in DOMAINS:
        raise HTTPException(400, f"Domaine invalide : {request.domain}")
    refs = detect_refs(request.reference)
    domains = [request.domain] if request.domain else list(DOMAINS)
    all_results=[]
    for ref in refs:
        ref_type=classify_ref(ref)
        for domain in domains:
            for hit in keyword_search(ref,domain,n_results=request.top_k):
                if ref.lower()[:8] in hit["text"].lower():
                    all_results.append({**hit,"reference_detected":ref,"reference_type":ref_type,"domain":domain})
        if len(all_results)<2:
            for domain in domains:
                for hit in vector_search(ref,domain,n_results=2):
                    all_results.append({**hit,"reference_detected":ref,"reference_type":ref_type,"domain":domain,"score":hit["score"]*0.7})
    seen,final=[],[]
    for r in sorted(all_results,key=lambda x:x.get("score",0),reverse=True):
        key=r["text"][:80]
        if key not in seen:
            seen.append(key)
            meta=r.get("metadata",{})
            final.append({"reference_detected":r["reference_detected"],"reference_type":r["reference_type"],"text":r["text"],"domain":r["domain"],"source":meta.get("source","N/A"),"filename":meta.get("filename","N/A"),"url":safe_url(meta.get("url")),"score":float(r.get("score",0)),"excerpt":r["text"][:300]+"..." if len(r["text"])>300 else r["text"]})
        if len(final)>=request.top_k: break
    return {"query":request.reference,"references_found":refs,"results":final,"domains_searched":domains}
