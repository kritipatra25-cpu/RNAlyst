# R Script: DESeq2 Differential Expression Runner
# Locked random seed = 42 for scientific reproducibility.

suppressPackageStartupMessages({
  library(DESeq2)
  library(jsonlite)
})

# Native command-line argument parser for base R
args <- commandArgs(trailingOnly = TRUE)

parse_args_dict <- function(args_list) {
  params <- list(
    counts_file = NULL,
    sample_table = NULL,
    design_formula = "~ condition",
    contrast_var = "condition",
    numerator = NULL,
    reference = NULL,
    output_dir = "./results",
    seed = 42
  )
  
  i <- 1
  while (i <= length(args_list)) {
    arg <- args_list[i]
    if (arg == "--counts_file" && i < length(args_list)) {
      params$counts_file <- args_list[i + 1]
      i <- i + 1
    } else if (arg == "--sample_table" && i < length(args_list)) {
      params$sample_table <- args_list[i + 1]
      i <- i + 1
    } else if (arg == "--design_formula" && i < length(args_list)) {
      params$design_formula <- args_list[i + 1]
      i <- i + 1
    } else if (arg == "--contrast_var" && i < length(args_list)) {
      params$contrast_var <- args_list[i + 1]
      i <- i + 1
    } else if (arg == "--numerator" && i < length(args_list)) {
      params$numerator <- args_list[i + 1]
      i <- i + 1
    } else if (arg == "--reference" && i < length(args_list)) {
      params$reference <- args_list[i + 1]
      i <- i + 1
    } else if (arg == "--output_dir" && i < length(args_list)) {
      params$output_dir <- args_list[i + 1]
      i <- i + 1
    } else if (arg == "--seed" && i < length(args_list)) {
      params$seed <- as.integer(args_list[i + 1])
      i <- i + 1
    }
    i <- i + 1
  }
  return(params)
}

opt <- parse_args_dict(args)

if (is.null(opt$counts_file) || is.null(opt$sample_table)) {
  stop("Both --counts_file and --sample_table are required arguments.")
}

# Set random seed
set.seed(opt$seed)

# Create output directory
dir.create(opt$output_dir, showWarnings = FALSE, recursive = TRUE)

# Read metadata and counts
sample_data <- read.csv(opt$sample_table, row.names = 1, check.names = FALSE, stringsAsFactors = TRUE)
counts_matrix <- read.csv(opt$counts_file, row.names = 1, check.names = FALSE)

# Convert counts to matrix of integers
counts_matrix <- as.matrix(counts_matrix)
mode(counts_matrix) <- "integer"

# Align sample names
common_samples <- intersect(rownames(sample_data), colnames(counts_matrix))
if (length(common_samples) == 0) {
  stop("No matching sample names found between metadata row names and counts matrix column names!")
}

sample_data <- sample_data[common_samples, , drop = FALSE]
counts_matrix <- counts_matrix[, common_samples, drop = FALSE]

# Ensure reference level is set properly
contrast_var <- opt$contrast_var
if (contrast_var %in% colnames(sample_data)) {
  if (!is.null(opt$reference) && opt$reference %in% levels(sample_data[[contrast_var]])) {
    sample_data[[contrast_var]] <- relevel(sample_data[[contrast_var]], ref = opt$reference)
  }
}

# Build DESeqDataSet
design_fmt <- as.formula(opt$design_formula)
dds <- DESeqDataSetFromMatrix(
  countData = counts_matrix,
  colData = sample_data,
  design = design_fmt
)

# Filter low count genes (at least 10 reads total across samples)
keep <- rowSums(counts(dds)) >= 10
dds <- dds[keep, ]

# Run DESeq2 pipeline
dds <- DESeq(dds, quiet = TRUE)

# Extract contrast results
if (!is.null(opt$numerator) && !is.null(opt$reference)) {
  res <- results(dds, contrast = c(contrast_var, opt$numerator, opt$reference), pAdjustMethod = "BH")
} else {
  res <- results(dds, pAdjustMethod = "BH")
}

# LFC shrinkage (apeglm or normal)
shrunk_res <- tryCatch({
  lfcShrink(dds, coef = length(resultsNames(dds)), type = "apeglm", quiet = TRUE)
}, error = function(e) {
  # Fallback to normal shrinkage if apeglm is not applicable
  lfcShrink(dds, res = res, type = "normal", quiet = TRUE)
})

# Combine results into DataFrame
res_df <- data.frame(
  gene_id = rownames(res),
  baseMean = res$baseMean,
  log2FoldChange = res$log2FoldChange,
  lfcSE = res$lfcSE,
  stat = res$stat,
  pvalue = res$pvalue,
  padj = res$padj,
  shrunk_log2FoldChange = shrunk_res$log2FoldChange
)

# Export Normalized Counts & VST
norm_counts <- counts(dds, normalized = TRUE)
vst_data <- assay(vst(dds, blind = FALSE))

# Write Output CSVs
write.csv(res_df, file.path(opt$output_dir, "differential_expression.csv"), row.names = FALSE)
write.csv(norm_counts, file.path(opt$output_dir, "normalized_counts.csv"), row.names = TRUE)
write.csv(vst_data, file.path(opt$output_dir, "vst_counts.csv"), row.names = TRUE)

# Summary JSON
summary_info <- list(
  total_input_genes = nrow(counts_matrix),
  filtered_genes = sum(!keep),
  analyzed_genes = nrow(dds),
  significant_deg_fdr05 = sum(res$padj < 0.05, na.rm = TRUE),
  significant_deg_fdr05_lfc1 = sum(res$padj < 0.05 & abs(res$log2FoldChange) >= 1, na.rm = TRUE),
  random_seed = opt$seed,
  r_version = R.version.string,
  deseq2_version = as.character(packageVersion("DESeq2"))
)

write_json(summary_info, file.path(opt$output_dir, "deseq2_summary.json"), auto_unbox = TRUE, pretty = TRUE)
cat("DESeq2 execution completed successfully. Results saved to:", opt$output_dir, "\n")
