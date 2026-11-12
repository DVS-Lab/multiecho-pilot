#!/usr/bin/env python3
"""Rerun the publication notebook's motor and cerebellar analyses from model 2."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import NamedTemporaryFile

NOTEBOOK_REVISION = "93a0f07391ce5f3e1e2b2eb931f3ad5a2456b420"
NOTEBOOK_PATH = "code/print-statistics_pub.ipynb"
REEXTRACTION_SUMMARY = "first_level_feat_model2_reextraction_summary.json"
EXTRACTION_DIRECTORY = "derivatives/extractions_model2_motor"
ROIS = ("bilateralMotor", "bilateralCerebellum")
STATS = ("beta", "zstat", "weighted_beta")
ANOVA_NUMERIC = ("Sum Sq", "Mean Sq", "Num df", "Den df", "F", "Partial eta_sq")
EMM_NUMERIC = ("emmean", "SE", "df", "lower.CL", "upper.CL", "asymp.LCL", "asymp.UCL")
EFFECT_TERM = r"Head Coil|Multiband|Multi-echo|Smoothness|ROI|headcoil|mb|me|roi|smoothness|HC|MB|ME"
EFFECT = re.compile(rf"(?:{EFFECT_TERM})(?:(?: × |:)(?:{EFFECT_TERM}))*")
EXPECTED_EMM_CELLS = {
    (mb, me, hc) for mb in ("mb1", "mb3", "mb6") for me in ("me1", "me4") for hc in ("20", "64")
}


def source_cells(root):
    result = subprocess.run(
        ["git", "show", f"{NOTEBOOK_REVISION}:{NOTEBOOK_PATH}"],
        cwd=root, text=True, capture_output=True, check=True,
    )
    notebook = json.loads(result.stdout)
    return {index: "".join(notebook["cells"][index]["source"]) for index in (2, 3, 5, 7, 15, 17)}


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f"Expected one notebook code match for {before!r}")
    return source.replace(before, after, 1)


def prepare_cells(cells):
    setup = replace_once(cells[2], "%matplotlib inline", "")
    for assignment, replacement in (
        ('project_root = Path(os.path.expanduser("~/Documents/GitHub/multiecho-pilot"))',
         "project_root = rerun_project_root"),
        ("extractions_dir = project_root / 'derivatives' / 'extractions'",
         "extractions_dir = rerun_extractions"),
        ("output_dir = project_root / 'derivatives' / 'plots'", "output_dir = rerun_activation_dir"),
    ):
        setup = replace_once(setup, assignment, replacement)
    # Keep the notebook's cohort filters and skip its standalone demographics figure.
    cohort, marker, _ = cells[5].partition("# --- 3. Nature-Quality Visualization ---")
    if not marker:
        raise ValueError("Could not locate the publication notebook's cohort filters.")
    motor_activation = replace_once(cells[15], "panel_labels = 'abcdefghi'", "panel_labels = 'ef'")
    selected = ((2, setup), (3, cells[3]), (5, cohort), (7, cells[7]),
                (15, motor_activation), (17, cells[17]))
    return tuple((index, source.replace("pandas2ri.rpy2py(", "as_pandas_frame("))
                 for index, source in selected)


def as_pandas_frame(table):
    from pandas import DataFrame
    from rpy2.robjects import pandas2ri

    # The notebook enables automatic conversion, so an R call may already
    # have returned a pandas DataFrame.
    return table if isinstance(table, DataFrame) else pandas2ri.rpy2py(table)


def coverage_summary(root):
    report = json.loads((root / REEXTRACTION_SUMMARY).read_text())
    subjects = report["manuscript_subjects_selected"]
    runs = report["manuscript_runs_expected"]
    if (report["extraction_status"] not in {"ready", "already_ready"}
            or subjects <= 0 or runs != 6 * subjects or report["runs_ready"] != runs
            or report["repaired_files_staged"] != 12 * runs
            or report["extraction_directory"] != EXTRACTION_DIRECTORY
            or not (root / EXTRACTION_DIRECTORY).is_dir()):
        raise ValueError("A complete, staged model-2 re-extraction is required.")
    return {"subjects": subjects, "runs": runs}


def finite(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def anova_rows(path, expected_rows):
    import pandas as pd

    table = pd.read_csv(path, dtype={"p": str}, keep_default_na=False)
    rows = []
    for record in table.to_dict("records"):
        effect = record["Effect"]
        p_value = record["p"]
        if not EFFECT.fullmatch(effect) or not (
            p_value == "N/A" or re.fullmatch(r"(?:<\s*)?(?:\d+(?:\.\d+)?|\.\d+)", p_value)
        ):
            raise ValueError(f"Unexpected aggregate ANOVA fields in {path.name}")
        row = {"Effect": effect, "p": None if p_value == "N/A" else p_value}
        row.update({field: finite(record[field]) for field in ANOVA_NUMERIC if field in record})
        rows.append(row)
    if len(rows) != expected_rows or len({row["Effect"] for row in rows}) != expected_rows:
        raise ValueError(f"Unexpected number of ANOVA effects in {path.name}")
    return rows


def emmeans_rows(table):
    rows = []
    seen = set()
    for record in table.to_dict("records"):
        cell = tuple(str(record[key]) for key in ("MB", "ME", "HC"))
        if cell not in EXPECTED_EMM_CELLS or cell in seen:
            raise ValueError("Unexpected estimated marginal means condition.")
        seen.add(cell)
        row = dict(zip(("MB", "ME", "HC"), cell))
        row.update({field: finite(record[field]) for field in EMM_NUMERIC if field in record})
        if row.get("emmean") is None or row.get("SE") is None:
            raise ValueError("An estimated marginal mean or standard error is unavailable.")
        rows.append(row)
    if seen != EXPECTED_EMM_CELLS:
        raise ValueError("Some conditions are missing estimated marginal means.")
    return rows


def roi_results(namespace, data_name, emms_name, roi):
    data = namespace[data_name][roi]
    return {
        "subjects": int(data["n_subjects"]),
        "observations": len(data["data"]),
        "subjects_by_coil": {"20": int(data["n_20ch"]), "64": int(data["n_64ch"])},
        "emmeans": emmeans_rows(namespace[emms_name][roi]),
    }


def activation_results(namespace, output):
    result = {}
    for stat in STATS:
        if stat == "weighted_beta":
            data_name, emms_name = "weighted_roi_results", "weighted_emm_results"
            filename = "bilateralMotor_weighted_beta_lme_anova.csv"
        else:
            data_name, emms_name = f"{stat}_roi_results", f"{stat}_emm_results"
            filename = f"bilateralMotor_{stat}_lme_anova_with_smoothness.csv"
        result[stat] = roi_results(namespace, data_name, emms_name, "bilateralMotor")
        result[stat]["anova"] = anova_rows(output / filename, 8)
    return result


def comparison_results(namespace, output):
    result = {}
    for stat in ("beta", "zstat"):
        filename = f"motor_cerebellum_roi_{stat}_lme_anova_with_smoothness.csv"
        result[stat] = {
            "joint_anova": anova_rows(output / filename, 16),
            "by_roi": {roi: roi_results(namespace, f"mc_{stat}_results", f"mc_{stat}_emms", roi)
                       for roi in ROIS},
        }

    weighted = {}
    for roi in ROIS:
        weighted[roi] = roi_results(namespace, "mc_weighted_results", "mc_weighted_emms", roi)
        weighted[roi]["anova"] = anova_rows(output / f"{roi}_weighted_beta_lme_anova.csv", 8)
    result["weighted_beta_by_roi"] = weighted
    return result


def verify_figures(output, prefix):
    for stat in STATS:
        for suffix in ("png", "tiff"):
            path = output / f"{prefix}_{stat}_emm_plot_publication.{suffix}"
            if not path.is_file() or not path.stat().st_size:
                raise ValueError(f"Missing notebook output {path.name}")


def run_notebook(root, prepared_cells, output, expected):
    activation_dir = output / "motor_activation"
    comparison_dir = output / "motor_cerebellum"
    comparison_dir.mkdir()
    namespace = {
        "as_pandas_frame": as_pandas_frame,
        "rerun_project_root": root,
        "rerun_extractions": root / EXTRACTION_DIRECTORY,
        "rerun_activation_dir": activation_dir,
    }
    for index, source in prepared_cells:
        if index == 15:
            if len(set(namespace["valid_subjects"])) != expected["subjects"]:
                raise ValueError("Notebook cohort size differs from the staged re-extraction.")
            configs = namespace["ROI_CONFIGS"]
            configs["3roi"]["rois"] = ["bilateralMotor"]
            for config in configs.values():
                for roi in ROIS:
                    if roi in config["ylabels"]:
                        config["ylabels"][roi] = "Hand response contrast"
        elif index == 17:
            namespace["output_dir"] = comparison_dir
        exec(compile(source, f"{NOTEBOOK_PATH}:cell-{index}", "exec"), namespace)

    verify_figures(activation_dir, "multi_roi")
    verify_figures(comparison_dir, "motor_cerebellum")
    brain_images = root / "derivatives/figures/brain_images"
    return {
        "status": "complete",
        "notebook_revision": NOTEBOOK_REVISION,
        "staged_coverage": expected,
        "local_output_directory": str(output.relative_to(root)),
        "brain_insets_available": {
            "bilateralMotor": (brain_images / "mask_bilateralMotor.png").is_file(),
            "bilateralCerebellum": (brain_images / "mask_bilateralCerebellum_red.png").is_file(),
        },
        "motor_activation": activation_results(namespace, activation_dir),
        "motor_cerebellum_comparison": comparison_results(namespace, comparison_dir),
        "joint_weighted_motor_cerebellum": "source_not_in_publication_notebook",
    }


def save_summary(path, summary):
    with NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(summary, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/ZPOOL/data/projects/multiecho-pilot"))
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    expected = coverage_summary(root)
    prepared = prepare_cells(source_cells(root))
    os.environ["MPLBACKEND"] = "Agg"
    parent = root / "derivatives/plots_model2_motor"
    parent.mkdir(exist_ok=True)
    output = parent / datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S%fZ")
    output.mkdir()
    try:
        summary = run_notebook(root, prepared, output, expected)
        save_summary(args.summary.resolve(), summary)
    except BaseException:
        shutil.rmtree(output)
        raise
    print(f"Motor analyses and plots saved to {output}")


if __name__ == "__main__":
    main()
