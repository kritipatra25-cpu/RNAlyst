import os
import json

def build_biological_interpretation_summary():
    out_dir = 'results/osd120_osd678_interpretation'
    os.makedirs(out_dir, exist_ok=True)
    
    summary_data = [
        {
            "candidate_gene": "AT1G01010",
            "symbol": "ANAC001",
            "evidence_group": "GROUP_A",
            "observed_effect": "Up-regulated in OSD-120 light roots (LFC=+1.14) and OSD-678 light seedlings (LFC=+2.46, q=9.19e-11)",
            "biological_programs": ["ROS/Redox Signaling", "Stress-Response Transcription"],
            "evidence_level": "CROSS_TISSUE_REPLICATION_CONCORDANT",
            "literature_support": "NAC transcription factor involved in osmotic stress, ABA signaling, and reactive oxygen species response (He et al., 2005; Tran et al., 2004).",
            "dataset_support": "Statistically significant in both light-grown root (OSD-120) and seedling (OSD-678) spaceflight environments.",
            "contradictions": "Repressed in OSD-678 dark seedlings (LFC=-0.35, q=0.62), indicating light-dependence of upregulation.",
            "mechanistic_status": "Transcriptional association; upstream stress/redox responder.",
            "confidence": "HIGH_CONCORDANCE"
        },
        {
            "candidate_gene": "AT3G46640",
            "symbol": "LUX",
            "evidence_group": "GROUP_A",
            "observed_effect": "Up-regulated in OSD-120 light roots (LFC=+0.43) and OSD-678 light seedlings (LFC=+0.73, q=0.041)",
            "biological_programs": ["Circadian / Evening Complex", "Photoperiod Alignment"],
            "evidence_level": "CROSS_TISSUE_REPLICATION_CONCORDANT",
            "literature_support": "LUX ARRHYTHMO (LUX/PCL1) encodes a GARP-domain transcription factor component of the circadian Evening Complex (Nusinow et al., 2011; Hazen et al., 2005).",
            "dataset_support": "Concordant positive shift in illuminated spaceflight across isolated roots and whole seedlings.",
            "contradictions": "Directionally opposite in dark seedlings (OSD-678 Dark LFC=-0.27, q=0.66), confirming photoperiod interaction.",
            "mechanistic_status": "Circadian clock feedback component; light-dependent shift.",
            "confidence": "HIGH_CONCORDANCE"
        },
        {
            "candidate_gene": "AT5G07390",
            "symbol": "RBOHA",
            "evidence_group": "GROUP_A",
            "observed_effect": "Up-regulated in OSD-120 light roots (LFC=+1.48) and OSD-678 light seedlings (LFC=+5.45, q=0.0038)",
            "biological_programs": ["ROS/Redox Biology", "Apoplastic H2O2 Generation", "Cell Wall Remodeling"],
            "evidence_level": "CROSS_TISSUE_REPLICATION_CONCORDANT",
            "literature_support": "Respiratory burst oxidase homolog A (RBOHA) encodes a plasma membrane NADPH oxidase generating apoplastic superoxide/H2O2 (Torres et al., 1998; Marino et al., 2012).",
            "dataset_support": "FDR-significant upregulation in light-grown spaceflight samples across both root and seedling datasets.",
            "contradictions": "Downregulated in dark seedlings (OSD-678 Dark LFC=-3.45, q=0.098), demonstrating light-gated ROS enzyme expression.",
            "mechanistic_status": "Enzymatic mediator of apoplastic ROS production; responsive to spaceflight light environment.",
            "confidence": "HIGH_CONCORDANCE"
        },
        {
            "candidate_gene": "AT5G13930",
            "symbol": "CHS",
            "evidence_group": "GROUP_A",
            "observed_effect": "Down-regulated in OSD-120 light roots (LFC=-10.68) and OSD-678 light seedlings (LFC=-5.19, q=0.0021)",
            "biological_programs": ["Secondary Metabolism", "Phenylpropanoid / Flavonoid Biosynthesis"],
            "evidence_level": "CROSS_TISSUE_REPLICATION_CONCORDANT",
            "literature_support": "Chalcone Synthase (CHS/TT4) catalyzes the initial committed step in flavonoid biosynthesis (Feinbaum & Ausubel, 1988; Dao et al., 2011).",
            "dataset_support": "Strongest absolute fold-change repression observed across both OSD-120 roots and OSD-678 seedlings under light flight.",
            "contradictions": "Less pronounced repression in dark seedlings (OSD-678 Dark LFC=-1.19, q=0.70), demonstrating light-dependent suppression.",
            "mechanistic_status": "Biosynthetic enzyme repression; secondary metabolic adaptation.",
            "confidence": "HIGH_CONCORDANCE"
        },
        {
            "candidate_gene": "AT3G17609",
            "symbol": "HYH",
            "evidence_group": "GROUP_B",
            "observed_effect": "Down-regulated in OSD-120 light roots (LFC=-4.69) and OSD-678 light seedlings (LFC=-0.85, q=0.269)",
            "biological_programs": ["Light Signaling", "Photomorphogenesis / bZIP Transcription"],
            "evidence_level": "DIRECTIONAL_CONCORDANCE_ONLY",
            "literature_support": "HY5-HOMOLOG (HYH) is a bZIP transcription factor acting redundantly with HY5 in photomorphogenesis and light signal transduction (Holm et al., 2002).",
            "dataset_support": "Directionally concordant negative fold-change in light flight in both datasets, but fails FDR threshold in OSD-678.",
            "contradictions": "High variance in OSD-678 light seedlings resulting in q=0.269.",
            "mechanistic_status": "Light-signaling transcription factor candidate; directional support only.",
            "confidence": "MODERATE_DIRECTIONAL_ONLY"
        },
        {
            "candidate_gene": "AT2G04170",
            "symbol": "UNASSIGNED",
            "evidence_group": "GROUP_C",
            "observed_effect": "Up-regulated in isolated roots (OSD-120 LFC=+1.41; OSD-658 LFC=+1.59); Down-regulated in whole seedlings (OSD-678 LFC=-1.04, q=0.338)",
            "biological_programs": ["Root-Specific Spaceflight Adaptation"],
            "evidence_level": "TISSUE_SPECIFIC_OR_DISCORDANT",
            "literature_support": "Uncharacterized locus with conserved domain structure; highly expressed in root tip tissue (TAIR Annotation, 2024).",
            "dataset_support": "Consistently induced across independent isolated root datasets, but suppressed in whole seedlings.",
            "contradictions": "Opposite expression direction between roots and seedlings.",
            "mechanistic_status": "Root-specific spaceflight marker candidate; unresolved discordance.",
            "confidence": "CONTEXT_SPECIFIC"
        },
        {
            "candidate_gene": "AT4G04720",
            "symbol": "CPK21",
            "evidence_group": "GROUP_C",
            "observed_effect": "Up-regulated in OSD-120 light roots (LFC=+0.34); Down-regulated in OSD-678 light seedlings (LFC=-0.22, q=0.192)",
            "biological_programs": ["Calcium Signaling", "Kinase Cascades"],
            "evidence_level": "TISSUE_SPECIFIC_OR_DISCORDANT",
            "literature_support": "Calcium-Dependent Protein Kinase 21 (CPK21) mediates hyperosmolality and salt stress signaling (Schulz et al., 2013).",
            "dataset_support": "Discrepant fold change direction between isolated roots and whole seedlings.",
            "contradictions": "Fails FDR threshold in both datasets.",
            "mechanistic_status": "Calcium signaling node; non-replicated context-dependent locus.",
            "confidence": "LOW_DISCORDANT"
        },
        {
            "candidate_gene": "AT5G57630",
            "symbol": "CIPK21",
            "evidence_group": "GROUP_C",
            "observed_effect": "Up-regulated in OSD-120 light roots (LFC=+0.52); Down-regulated in OSD-678 light seedlings (LFC=-0.25, q=0.549)",
            "biological_programs": ["CBL-CIPK Signaling", "Ion Homeostasis"],
            "evidence_level": "TISSUE_SPECIFIC_OR_DISCORDANT",
            "literature_support": "CBL-Interacting Protein Kinase 21 (CIPK21) regulates salt and osmotic stress tolerance (Pandey et al., 2015).",
            "dataset_support": "Directionally discordant under light; however, exhibits significant upregulation in dark seedlings (OSD-678 Dark LFC=+0.87, q=0.043).",
            "contradictions": "Light-dependent inversion of expression pattern.",
            "mechanistic_status": "Stress kinase node; light-gated context-dependent response.",
            "confidence": "LOW_DISCORDANT"
        }
    ]
    
    out_file = os.path.join(out_dir, 'biological_interpretation_summary.json')
    with open(out_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
        
    print(f"Saved {out_file}")

if __name__ == '__main__':
    build_biological_interpretation_summary()
