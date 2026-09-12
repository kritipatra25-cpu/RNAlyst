import subprocess

rscript = r"C:\Program Files\R\R-4.5.1\bin\Rscript.exe"
r_code = """
options(repos = c(CRAN = "https://cloud.r-project.org"))
if (!requireNamespace("jsonlite", quietly = TRUE)) install.packages("jsonlite")
if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager")
BiocManager::install(c("DESeq2", "apeglm"), ask = FALSE, update = FALSE)
"""

print("Installing required R packages...")
res = subprocess.run([rscript, "-e", r_code], capture_output=True, text=True)
print("Return code:", res.returncode)
print("Stdout:", res.stdout[-1500:] if res.stdout else "")
print("Stderr:", res.stderr[-1500:] if res.stderr else "")
