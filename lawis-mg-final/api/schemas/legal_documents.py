from typing import Dict, Any
from pydantic import BaseModel, Field


class DocumentGenerationRequest(BaseModel):
    """Données saisies pour un modèle de document. Les clés attendues dépendent
    du type de document (voir GET /legal-documents/types)."""
    data: Dict[str, Any] = Field(default_factory=dict)
