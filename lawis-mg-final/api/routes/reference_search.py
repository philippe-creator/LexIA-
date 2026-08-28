import re
from fastapi import APIRouter, HTTPException
from api.core.dependencies import CurrentUser
from api.schemas.chat import ReferenceRequest, safe_url
from retrieval.keyword_search import keyword_search
from retrieval.vector_search import vector_search
from processing.indexer import get_collection
from core.domains import DOMAINS

router = APIRouter(prefix="/reference", tags=["Référence"])
PATTERNS = [r"(?i)loi\s+(?:n°?\s*)?\d+[-./]\d+",r"(?i)dahir\s+(?:n°?\s*)?\d+[-./]\d+[-./]\d+",r"(?i)article\s+\d+",r"(?i)(?:CGI|Code\s+Général\s+des\s+Impôts)\s*\d{4}",r"(?i)(?:code\s+du\s+travail|loi\s+65-99)",r"(?i)(?:loi\s+de\s+finances)\s*\d{4}",r"(?i)note\s+circulaire\s+(?:n°?\s*)?\d+"]

# Certaines références désignent un TEXTE entier (un code, une loi-cadre) et non
# un passage précis. Elles doivent restreindre le PÉRIMÈTRE de la recherche, pas
# être cherchées comme chaîne : le corps d'un article ne contient jamais le nom
# du code qui le porte (« code du travail » n'apparaît pas dans l'article 62).
# Sans cela, « article 62 code du travail » remontait l'article 62 du code de
# commerce ou du CGI, et aucun résultat du code du travail.
# Un domaine ne suffit pas comme périmètre : le domaine « travail » contient à
# la fois le code du travail et la loi 65-00 (AMO), qui ont chacun un article 62.
# Chaque entrée porte donc aussi un fragment de nom de fichier, pour privilégier
# le document effectivement nommé dans la requête.
SCOPE_PATTERNS = [
    (r"(?i)code\s+du\s+travail|loi\s+65[-./]99", "travail", "code-du-travail"),
    (r"(?i)loi\s+de\s+finances", "fiscal", "loi-finances"),
    (r"(?i)\bCGI\b|code\s+g[ée]n[ée]ral\s+des\s+imp[ôo]ts", "fiscal", "cgi"),
    (r"(?i)code\s+de\s+commerce|loi\s+15[-./]95", "societes", "code-de-commerce"),
    (r"(?i)loi\s+17[-./]95", "societes", "17-95"),
    (r"(?i)loi\s+5[-./]96", "societes", "5-96"),
    (r"(?i)loi\s+09[-./]08", "donnees_personnelles", "09-08"),
]

def detect_scope(text):
    """(domaine, fragment de nom de fichier) déduits d'une référence à un texte
    entier ; (None, None) si la requête ne nomme aucun code."""
    for pattern, domain, file_hint in SCOPE_PATTERNS:
        if re.search(pattern, text):
            return domain, file_hint
    return None, None

def detect_scope_domain(text):
    """Domaine déduit d'une référence à un texte entier, sinon None."""
    return detect_scope(text)[0]

def filename_boost(metadata, file_hint):
    """Privilégie le document nommé dans la requête, à domaine égal."""
    if not file_hint:
        return 1.0
    filename = (metadata or {}).get("filename", "") or ""
    return 2.0 if file_hint in filename.lower().replace("_", "-") else 1.0

def detect_refs(text):
    found=[]
    for p in PATTERNS: found.extend(re.findall(p,text))
    return list(set(found)) or [text]

def exact_ref_boost(text, ref):
    """Le passage qui EST l'article cherché doit primer sur ceux qui s'y réfèrent.

    BM25 seul classe « voir note correspondant à l'article 389 » aussi haut que
    l'article 62 lui-même : les jetons « article » et un nombre suffisent. Le
    rerankeur applique bien un bonus d'article, mais cette route interroge
    keyword/vector search en direct — d'où ce bonus local.
    """
    t = " ".join(text.split()).lower()
    r = " ".join(ref.split()).lower()
    if t.startswith(r):    # le passage débute par « Article 62 » → c'est lui
        return 3.0
    if r in t[:200]:       # cité dès l'en-tête du passage
        return 1.5
    return 1.0

def classify_ref(ref):
    r=ref.lower()
    if "article" in r: return "article"
    if "dahir" in r: return "dahir"
    if "décret" in r: return "décret"
    if "loi de finances" in r: return "loi_de_finances"
    return "loi"

# Mots-outils ignorés pour juger de la pertinence d'un passage.
_STOP = {"de","des","du","la","le","les","un","une","et","en","au","aux","pour",
         "par","sur","dans","ce","cette","que","qui","numero","numéro","loi","article"}

def content_tokens(text):
    """Mots significatifs d'une requête : mots de 3+ lettres et nombres (un
    numéro d'article/loi comme « 62 » compte), hors mots-outils."""
    return [t for t in re.findall(r"[a-zà-ÿ]{3,}|\d+", text.lower()) if t not in _STOP]

def has_lexical_overlap(text, tokens):
    """Vrai si au moins un mot significatif de la requête figure dans le passage.

    Le repli vectoriel renvoie toujours les voisins les plus proches, même hors
    sujet (sur un corpus juridique homogène, tout se ressemble ~0.8). Exiger la
    présence d'un mot de la requête évite d'afficher du bruit pour une référence
    absente du corpus (ex. « note circulaire TVA » — aucune circulaire indexée)."""
    if not tokens:
        return True
    low = text.lower()
    # Bornes de mot : sinon "62" matche à l'intérieur de "3620" ou "462", et un
    # nombre isolé finit presque toujours par apparaître quelque part dans un
    # document juridique de plusieurs pages (dates, autres articles cités...).
    return any(re.search(rf"\b{re.escape(t)}\b", low) for t in tokens)

def _full_article_text(text: str, metadata: dict, domain: str) -> str:
    """Recolle un article découpé en plusieurs chunks (chunk_idx "5_0", "5_1"...
    — voir processing/chunker.py, un article dépassant 1600 caractères est
    re-découpé par taille) pour renvoyer le texte complet au lieu d'un seul
    fragment. Sans ça, l'utilisateur voit un article coupé en plein milieu."""
    chunk_idx = str(metadata.get("chunk_idx", ""))
    filename = metadata.get("filename")
    if "_" not in chunk_idx or not filename:
        return text
    prefix = chunk_idx.split("_")[0] + "_"
    try:
        col = get_collection(domain)
        res = col.get(where={"filename": {"$eq": filename}}, include=["documents", "metadatas"])
    except Exception:
        return text
    siblings = [
        (m.get("chunk_idx", ""), d)
        for d, m in zip(res["documents"], res["metadatas"])
        if str(m.get("chunk_idx", "")).startswith(prefix)
    ]
    if len(siblings) <= 1:
        return text

    def _suffix(idx: str) -> int:
        try:
            return int(idx.split("_")[1])
        except (IndexError, ValueError):
            return 0

    siblings.sort(key=lambda item: _suffix(item[0]))
    return " ".join(d for _, d in siblings)


@router.post("/")
async def search_reference(request: ReferenceRequest, current_user: CurrentUser):
    if request.domain and request.domain not in DOMAINS:
        raise HTTPException(400, f"Domaine invalide : {request.domain}")
    refs = detect_refs(request.reference)
    # Le domaine explicite prime ; sinon on le déduit d'une référence à un code.
    detected_domain, file_hint = detect_scope(request.reference)
    scope_domain = request.domain or detected_domain
    domains = [scope_domain] if scope_domain in DOMAINS else list(DOMAINS)
    # On ne cherche pas le nom du code comme chaîne : il a servi de périmètre.
    # (Sauf si c'était la seule référence — la requête porte alors sur le texte.)
    search_refs = [r for r in refs if detect_scope_domain(r) is None] or refs
    all_results=[]
    # On récupère un vivier large avant d'appliquer les bonus : avec seulement
    # top_k candidats BM25, l'article exact peut ne jamais entrer dans la liste,
    # et le bonus n'a alors rien à remonter. On cherche large, on reclasse, on
    # tranche à top_k plus bas.
    pool_size = max(request.top_k * 5, 25)
    for ref in search_refs:
        ref_type=classify_ref(ref)
        tokens=content_tokens(ref)
        norm_ref = " ".join(ref.split()).lower()
        for domain in domains:
            for hit in keyword_search(ref,domain,n_results=pool_size):
                # Comparer sur la référence NORMALISÉE COMPLÈTE, pas ses 8
                # premiers caractères : pour « article 62 », [:8] ne retient que
                # "article " (le mot générique, sans le numéro) — n'importe quel
                # passage citant N'IMPORTE quel article passait ce filtre.
                norm_text = " ".join(hit["text"].split()).lower()
                if norm_ref in norm_text:
                    all_results.append({**hit,"reference_detected":ref,"reference_type":ref_type,"domain":domain,"score":hit.get("score",0)*exact_ref_boost(hit["text"],ref)*filename_boost(hit.get("metadata"),file_hint)})
        if len(all_results)<2:
            for domain in domains:
                for hit in vector_search(ref,domain,n_results=2):
                    # Repli vectoriel : on n'accepte un voisin que s'il contient
                    # réellement un mot de la référence — sinon c'est du bruit
                    # (référence absente du corpus).
                    if has_lexical_overlap(hit["text"], tokens):
                        all_results.append({**hit,"reference_detected":ref,"reference_type":ref_type,"domain":domain,"score":hit["score"]*0.7})
    seen,final=[],[]
    for r in sorted(all_results,key=lambda x:x.get("score",0),reverse=True):
        key=r["text"][:80]
        if key not in seen:
            seen.append(key)
            meta=r.get("metadata",{})
            full_text=_full_article_text(r["text"],meta,r["domain"])
            final.append({"reference_detected":r["reference_detected"],"reference_type":r["reference_type"],"text":full_text,"domain":r["domain"],"source":meta.get("source","N/A"),"filename":meta.get("filename","N/A"),"url":safe_url(meta.get("url")),"score":float(r.get("score",0))})
        if len(final)>=request.top_k: break
    return {"query":request.reference,"references_found":refs,"results":final,"domains_searched":domains}
