from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

@dataclass
class LegalCaseState:
    session_id: str
    case_type: str = "pqrs"  # pqrs, derecho, tutela, impugnacion
    raw_input: str = ""
    
    # Extracción
    facts: List[str] = field(default_factory=list)
    petitioner_name: Optional[str] = None
    petitioner_id: Optional[str] = None
    deadline: Optional[datetime] = None
    
    # Investigación
    legal_basis: List[Dict[str, str]] = field(default_factory=list)  # {ley, articulo, texto, vigencia}
    jurisprudence: List[Dict[str, str]] = field(default_factory=list)
    
    # Generación
    draft_document: Optional[str] = None
    citations_block: Optional[str] = None
    document_package: Dict[str, str] = field(default_factory=dict) # V62.0
    
    # Revisión
    review_status: str = "pending"  # pending, draft, approved, rejected
    review_score: float = 0.5
    review_notes: List[str] = field(default_factory=list)
    
    # Metadatos
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_step(self, agent: str, output: Dict):
        self.history.append({
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "output_summary": str(output)[:200]
        })
        self.updated_at = datetime.utcnow()
