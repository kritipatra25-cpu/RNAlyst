import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import agent_query, analyses, qc, ingestion

app = FastAPI(
    title="AI-Assisted RNA-seq Research API",
    description="Deterministic bioinformatics engine with evidence-grounded AI interpretation.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router, prefix="/api/v1/projects", tags=["Dataset Ingestion"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Dataset Ingestion"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["Dataset Ingestion"])
app.include_router(agent_query.router, prefix="/api/v1/query", tags=["Agent Query"])
app.include_router(analyses.router, prefix="/api/v1/analyses", tags=["Analyses"])
app.include_router(qc.qc_router, prefix="/api/v1/qc", tags=["QC"])
app.include_router(qc.qc_router, prefix="/qc", tags=["QC"])

# Mount static web app if directory exists
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="static")
else:
    @app.get("/")
    def read_root():
        return {
            "status": "online",
            "service": "AI-Assisted RNA-seq Research API",
            "version": "0.1.0",
            "supported_organisms": ["Arabidopsis thaliana", "Homo sapiens", "Mus musculus"]
        }
