from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator


class DocumentGenerationRequest(BaseModel):
    """Données saisies pour un modèle de document. Les clés attendues dépendent
    du type de document (voir GET /legal-documents/types)."""
    data: Dict[str, Any] = Field(default_factory=dict)
    lang: str = "fr"  # langue du document généré : "fr" | "en" | "ar"

    @field_validator("lang")
    @classmethod
    def _validate_lang(cls, v):
        return v if v in ("fr", "en", "ar") else "fr"
