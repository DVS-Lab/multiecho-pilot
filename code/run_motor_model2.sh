#!/usr/bin/env bash
# Run the notebook with the R installation inside the motor analysis environment.
set -euo pipefail

: "${CONDA_PREFIX:?Run this script with conda run -n seqpilot-motor-notebook.}"
analysis_python="$CONDA_PREFIX/bin/python"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export R_HOME="$CONDA_PREFIX/lib/R"
export LD_LIBRARY_PATH="$R_HOME/lib:$CONDA_PREFIX/lib"
unset R_LIBS R_DEFAULT_PACKAGES
export R_LIBS_USER=/dev/null R_LIBS_SITE=/dev/null
export R_PROFILE=/dev/null R_PROFILE_USER=/dev/null
export R_ENVIRON=/dev/null R_ENVIRON_USER=/dev/null

scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT

check_r_fit() {
    "$analysis_python" -I -B - <<'PY'
from rpy2.robjects import r

r("""
cat(R.version.string, "\\n")
for (pkg in c("lme4", "lmerTest", "emmeans")) {
    info <- utils::packageDescription(pkg)
    cat(pkg, info$Version, "built with", info$Built, "\\n")
}
fit <- lmerTest::lmer(Reaction ~ Days + (1 | Subject), data = lme4::sleepstudy)
tests <- stats::anova(fit, type = 3, ddf = "Satterthwaite")
means <- as.data.frame(emmeans::emmeans(fit, ~ Days, at = list(Days = c(0, 9))))
stopifnot(is.finite(tests["Days", "Pr(>F)"]), nrow(means) == 2L,
          all(is.finite(means$emmean)))
cat("R model and estimated marginal means check passed.\\n")
""")
PY
}

if ! check_r_fit >"$scratch/r_check.log" 2>&1; then
    cat "$scratch/r_check.log" >&2
    if ! grep -Fq '"tcrossprod" is not a BUILTIN function' "$scratch/r_check.log"; then
        exit 1
    fi

    # Rebuild the same lmerTest version with this R runtime in a temporary library.
    mkdir "$scratch/r_library"
    export R_LIBS="$scratch/r_library"
    "$analysis_python" -I -B - <<'PY'
from rpy2.robjects import r

r("""
lib <- Sys.getenv("R_LIBS")
version <- utils::packageDescription("lmerTest", fields = "Version")
filename <- paste0("lmerTest_", version, ".tar.gz")
archive <- file.path(tempdir(), filename)
cran <- "https://cloud.r-project.org/src/contrib"
download <- function(url) {
    tryCatch(suppressWarnings(utils::download.file(url, archive, quiet = TRUE, mode = "wb")) == 0L,
             error = function(e) FALSE)
}
if (!download(paste(cran, filename, sep = "/")) &&
    !download(paste(cran, "Archive/lmerTest", filename, sep = "/"))) {
    stop("Could not download the installed lmerTest version from CRAN.")
}
utils::install.packages(archive, repos = NULL, type = "source", lib = lib, quiet = TRUE)
stopifnot(utils::packageDescription("lmerTest", lib.loc = lib, fields = "Version") == version)
""")
PY
    check_r_fit
else
    cat "$scratch/r_check.log"
fi

"$analysis_python" -I -B "$script_dir/rerun_motor_model2.py" "$@"
