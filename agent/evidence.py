from pathlib import Path
import json
import csv


class EvidenceEngine:
    """
    Converts pipeline validation results into structured
    gene-level evidence that can later be queried by an AI agent.
    """

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)

        self.summary_path = (
            self.results_dir / "osd-678_analysis_summary.json"
        )

        self.candidate_path = (
            self.results_dir
            / "candidate_validation"
            / "osd678_candidate_comparison.csv"
        )

        self.summary = None
        self.genes = []

    def load(self):
        """Load the existing pipeline outputs."""

        with open(self.summary_path, "r", encoding="utf-8") as f:
            self.summary = json.load(f)

        with open(
            self.candidate_path,
            "r",
            encoding="utf-8",
            newline=""
        ) as f:

            reader = csv.DictReader(f)
            self.genes = list(reader)

        return self

    def get_gene(self, gene_id: str):
        """Return evidence for a specific gene."""

        for gene in self.genes:
            if gene.get("gene_id") == gene_id:
                return gene

        return None

    def get_summary(self):
        """Return dataset-level analysis information."""

        return self.summary

    def get_validated_genes(self):
        """Return genes that pass the OSD-678 FDR criterion."""

        return [
            gene
            for gene in self.genes
            if gene.get("passes_osd678_fdr_005", "").lower() == "true"
        ]


if __name__ == "__main__":

    engine = EvidenceEngine(
        "results/osd678_validation"
    )

    engine.load()

    print(
        f"Loaded {len(engine.genes)} candidate genes."
    )

    validated = engine.get_validated_genes()

    print(
        f"Validated genes: {len(validated)}"
    )
    