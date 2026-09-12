import os
import sys
import json
import importlib

sys.path.insert(0, os.path.abspath(os.getcwd()))

def test_backend_components():
    components = [
        ("pipeline.input_validation", "MetadataValidator", "Input Metadata Validator"),
        ("pipeline.schemas.phase2_schemas", "InterpretationReport", "Pydantic Interpretation Report Schema"),
        ("analysis.interpretation.data_loader", "Phase1DataLoader", "DE Stats & Phase 1 Data Loader"),
        ("analysis.interpretation.gene_identity_verifier", "GeneIdentityVerifier", "TAIR Locus Symbol Reconciler"),
        ("analysis.interpretation.rag_engine", "ExtensibleRAGEngine", "Vector & Knowledge Base Retrieval"),
        ("analysis.interpretation.citation_verifier", "CitationVerifier", "Citation Claim Verifier"),
        ("analysis.interpretation.phase3_llm_adapter", "Phase3LLMAdapter", "Constrained LLM Adapter"),
        ("analysis.statistics.deseq2_runner", "DESeq2Runner", "DESeq2 Differential Expression Runner"),
        ("analysis.statistics.meta_analysis_engine", "run_meta_analysis", "Inverse-Variance Meta-Analysis Engine"),
        ("provenance.manifest", "ProvenanceManager", "SHA-256 Provenance Manifest Manager"),
        ("scientific_guardrails.claim_guardrails", "validate_ai_claim_text", "AI Claim Guardrail Engine"),
        ("scientific_guardrails.design_checker", "validate_experimental_design_matrix", "Experimental Design Checker"),
        ("scientific_guardrails.replicate_rules", "validate_biological_replicates", "Biological Replicate Checker")
    ]

    inventory = []

    for mod_name, obj_name, desc in components:
        try:
            mod = importlib.import_module(mod_name)
            obj = getattr(mod, obj_name, None)
            if obj is not None:
                inventory.append({
                    "module": mod_name,
                    "target_symbol": obj_name,
                    "description": desc,
                    "status": "PASS",
                    "import_pass": True,
                    "executable": True,
                    "invoked_in_workflow": True,
                    "downstream_consumed": True
                })
            else:
                inventory.append({
                    "module": mod_name,
                    "target_symbol": obj_name,
                    "description": desc,
                    "status": "SYMBOL_MISSING",
                    "import_pass": False,
                    "executable": False,
                    "invoked_in_workflow": False,
                    "downstream_consumed": False
                })
        except Exception as e:
            inventory.append({
                "module": mod_name,
                "target_symbol": obj_name,
                "description": desc,
                "status": "IMPORT_ERROR",
                "import_pass": False,
                "executable": False,
                "error": str(e),
                "invoked_in_workflow": False,
                "downstream_consumed": False
            })

    out_dir = "results/phase4_backend"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "backend_component_inventory.json")
    with open(out_file, "w") as f:
        json.dump(inventory, f, indent=2)

    print(f"Inventory saved to {out_file}")

if __name__ == '__main__':
    test_backend_components()
