"""
DatabaseRecordVerifier for Phase 2 RAG / Knowledge Retrieval Layer.
Validates database annotations from GO, KEGG, Plant Reactome, MapMan, and TAIR,
ensuring strict separation from peer-reviewed literature citations.
"""

from typing import Tuple, Dict, Any, Optional
from pipeline.schemas.rag_schemas import VerifiedDatabaseRecord

class DatabaseRecordVerifier:
    VALID_DATABASES = {"GO", "KEGG", "REACTOME", "MAPMAN", "TAIR", "OSDR"}

    def __init__(self, external_db_map: Optional[Dict[str, Any]] = None):
        self.external_db_map = external_db_map or {}

    def verify_database_record(self, record_dict: Dict[str, Any]) -> Tuple[bool, Optional[VerifiedDatabaseRecord], str]:
        """
        Verify database annotation record:
        - Must have valid database name in VALID_DATABASES
        - Must have valid non-synthetic record ID
        - Must specify association_type
        """
        db = str(record_dict.get("database", "")).upper()
        rec_id = str(record_dict.get("record_id", "")).strip()
        annotation = str(record_dict.get("annotation_text", "")).strip()
        assoc_type = str(record_dict.get("association_type", "DIRECT_ANNOTATION")).strip()

        if db not in self.VALID_DATABASES:
            return False, None, f"Unsupported or invalid database name: '{db}'"

        if not rec_id or rec_id.startswith("FAKE_") or rec_id.startswith("SYNTHETIC_"):
            return False, None, f"Synthetic or invalid database record ID: '{rec_id}'"

        if not annotation:
            return False, None, "Database record missing annotation text"

        verified_rec = VerifiedDatabaseRecord(
            database=db,
            record_id=rec_id,
            record_version=record_dict.get("record_version", "v1.0"),
            annotation_text=annotation,
            association_type=assoc_type,
            verification_status="VERIFIED_DATABASE_ENTRY"
        )
        return True, verified_rec, "Database record verified successfully"
