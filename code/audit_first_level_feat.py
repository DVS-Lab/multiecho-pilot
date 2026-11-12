#!/usr/bin/env python3
"""Read existing first-level FEAT files and print diagnostics to stdout."""
import argparse
from collections import Counter, defaultdict
import csv
import functools
import html
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", type=Path, default=Path("/ZPOOL/data/projects/multiecho-pilot"))
parser.add_argument("--local-details", action="store_true",
                    help="Print participant-level diagnostics for local use only. Do not commit this output.")
parser.add_argument("subjects", nargs="*",
                    help="Local subject codes. Default: two complete extraction sets per coil.")
args = parser.parse_args()
root = args.root.resolve()
if not (root / "derivatives/fsl").is_dir():
    parser.error(f"FEAT directory unavailable under {root}")
for tool in ("fslmeants", "fslstats", "fslhd"):
    if not shutil.which(tool):
        parser.error(f"{tool} is unavailable. Load the existing FSL environment first.")

acquisitions = ("mb1me1", "mb1me4", "mb3me1", "mb3me4", "mb6me1", "mb6me4")
sources = (("VSconstrained", 1, 13), ("rFFA", 3, 3), ("rightMotor", 2, 3), ("leftMotor", 4, 3))
input_measured = set()
coil = {}
for channels in (20, 64):
    path = root / f"code/sublist-{channels}ch.txt"
    if path.is_file():
        coil.update({re.sub("^sub-", "", s): channels for s in path.read_text().split()})


def extraction(sub, acq, roi):
    return root / ("derivatives/extractions/"
                   f"ts_sub-{sub}_acq_{acq}_type-act_img-beta_mask-{roi}_denoise_base.txt")


def emit(*values):
    if args.local_details:
        print(*values, sep="\t", flush=True)


def read(path):
    return path.read_text(errors="replace") if path.is_file() else ""


@functools.lru_cache(maxsize=None)
def run(*command):
    process = subprocess.run(command, capture_output=True, text=True)
    if process.returncode:
        emit("FSL_ERROR", *command, " ".join(process.stderr.split())[:250])
        return "NA"
    return " ".join(process.stdout.split())


@functools.lru_cache(maxsize=None)
def image_header(image):
    # Preserve fslhd's line breaks when parsing its keyed output.
    process = subprocess.run(("fslhd", str(image)), capture_output=True, text=True)
    return dict(line.split(maxsplit=1) for line in process.stdout.splitlines()
                if len(line.split(maxsplit=1)) == 2)


def grid(image):
    h = image_header(image)
    transform = "sto" if h.get("sform_code", "0") != "0" else "qto"
    fields = [f"dim{i}" for i in range(1, 4)] + [f"{transform}_xyz:{i}" for i in range(1, 4)]
    return tuple(h.get(field) for field in fields)


def check_mask(image, mask):
    if not image.is_file() or not mask.is_file():
        return False
    g1, g2 = grid(image), grid(mask)
    if None in g1 or None in g2 or g1[:3] != g2[:3]:
        emit("GRID_CHECK", image, mask, g1, g2)
        return False
    if any(abs(float(a) - float(b)) > 0.001 for x, y in zip(g1[3:], g2[3:])
           for a, b in zip(x.split(), y.split())):
        emit("GRID_CHECK", image, mask, g1, g2)
        return False
    return True


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return math.nan


def compare(a, b, abs_tol=1e-6):
    return math.isclose(a, b, rel_tol=1e-7, abs_tol=abs_tol)


def resolve_input(value, feat):
    path = Path(value)
    if path.is_absolute() and path.is_file():
        return path
    if "/multiecho-pilot/" in value:
        path = root / value.split("/multiecho-pilot/", 1)[1]
        if path.is_file():
            return path
    for path in (feat / value, feat.parent / value):
        if path.is_file():
            return path
    return None


def vest(path):
    before, _, after = read(path).partition("/Matrix")
    metadata = dict(line[1:].split(maxsplit=1) for line in before.splitlines()
                    if line.startswith("/") and len(line.split(maxsplit=1)) == 2)
    return metadata, [list(map(float, line.split())) for line in after.splitlines() if line.strip()]


def inspect(feat, cope, mask, bids, record=None):
    fsf = {}
    for key, value in re.findall(r"^set (\S+)\s+(.+)$", read(feat / "design.fsf"), re.M):
        fsf[key] = value.strip().strip('"')
    settings = ("version", "level", "analysis", "tr", "npts", "ndelete", "norm_yn",
                "smooth", "temphp_yn", "filtering_yn", "paradigm_hp", "evs_orig", "evs_real")
    emit("FSF", feat, *(f"{k}={fsf.get(f'fmri({k})', 'NA')}" for k in settings))
    value = fsf.get("feat_files(1)", "")
    image = resolve_input(value, feat) if value else None
    mean = feat / "mean_func.nii.gz"
    featmask = feat / "mask.nii.gz"
    if record is not None:
        for key in ("tr", "norm_yn", "smooth", "temphp_yn"):
            record[key] = number(fsf.get(f"fmri({key})"))
        if image:
            if re.search(r"_5mm\.nii(?:\.gz)?$", image.name):
                record["input_kind"] = "5mm_input"
            elif re.search(r"_\d+mm\.nii(?:\.gz)?$", image.name):
                record["input_kind"] = "other_smoothed_input"
            elif "tedana" in image.name or "optcom" in image.name:
                record["input_kind"] = "tedana_or_optcom_named_input"
            else:
                record["input_kind"] = "other_input"
            header = image_header(image)
            record["input_tr"] = number(header.get("pixdim4"))
            if header.get("time_units") == "ms":
                record["input_tr"] /= 1000
            record["tr_matches_input"] = compare(record["tr"], record["input_tr"], 1e-5)
    for kind, img in (("FEAT_INPUT", image), ("FEAT_INPUT_LINK", feat / "prefiltered_func_data.nii.gz"),
                      ("FEAT_MEAN", mean)):
        if img and img.is_file():
            h = image_header(img)
            emit(kind, value if kind == "FEAT_INPUT" else img, img.resolve(),
                 *(f"{k}={h.get(k, 'NA')}" for k in ("dim4", "pixdim4", "time_units",
                                                     "datatype", "scl_slope", "scl_inter")))
        elif kind == "FEAT_INPUT":
            emit("MISSING_INPUT", value)
    if check_mask(mean, featmask):
        global_stats = run("fslstats", str(mean), "-k", str(featmask), "-m", "-V")
        emit("GLOBAL_BASELINE", global_stats)
        if record is not None:
            record["global_mean"] = number(global_stats.split()[0]) if global_stats else math.nan
    if check_mask(mean, mask):
        roi_mean = run("fslmeants", "-i", str(mean), "-m", str(mask))
        nonzero = run("fslstats", str(mean), "-k", str(mask), "-M", "-V")
        count = run("fslstats", str(mask), "-V")
        emit("ROI_BASELINE", mask.stem, roi_mean, "nonzero_mean_and_count=" + nonzero, "mask_count=" + count)
        if record is not None:
            record["roi_mean"] = number(roi_mean)
            if len(nonzero.split()) >= 2 and len(count.split()) >= 2 and number(count.split()[0]) > 0:
                record["coverage"] = number(nonzero.split()[1]) / number(count.split()[0])
    if image and image not in input_measured and check_mask(image, featmask):
        input_measured.add(image)
        upstream = image.with_name(re.sub(r"_\d+mm(?=\.nii)", "", image.name))
        for img in dict.fromkeys((image, upstream)):
            if check_mask(img, featmask):
                input_mean = run("fslstats", str(img), "-k", str(featmask), "-m")
                emit("INPUT_MASKED_MEAN", img, input_mean)
                if record is not None:
                    record["input_mean" if img == image else "upstream_mean"] = number(input_mean)

    log_paths = [feat / "report_log.html", *sorted((feat / "logs").glob("*"))]
    saw_scale = False
    for path in log_paths:
        if not path.is_file():
            continue
        for line in read(path).splitlines():
            line = html.unescape(re.sub(r"<[^>]+>", " ", line)).strip()
            if re.search(r"(?:^|\s)-(?:ing|inm)\s|grand.?mean|intensity norm|prefiltered_func_data_intnorm",
                         line, re.I):
                emit("SCALING_LOG", path, line[:500])
                saw_scale = True
                if record is not None and "prefiltered_func_data_intnorm" in line:
                    if re.search(r"\s-inm\s", line):
                        record["volume_scaling_logged"] = True
                    if re.search(r"\s-(mul|ing)\s", line):
                        record["run_scaling_logged"] = True
    if not saw_scale:
        emit("SCALING_LOG_UNAVAILABLE", feat)

    mat, matrix = vest(feat / "design.mat")
    con, contrasts = vest(feat / "design.con")
    emit("DESIGN", mat.get("NumPoints"), mat.get("NumWaves"), f"rows={len(matrix)}")
    if record is not None:
        record["design_rows_match"] = len(matrix) == number(fsf.get("fmri(npts)")) - number(fsf.get("fmri(ndelete)", 0))
    if len(contrasts) < cope or not matrix:
        emit("MISSING_DESIGN_OR_CONTRAST", feat, cope)
        return
    pp = mat.get("PPheights", "").split()
    contrast_pp = con.get("PPheights", "").split()
    for idx in (3, 4) if mask.name == "mask_leftMotor.nii.gz" else (cope,):
        if idx <= len(contrasts):
            emit("CONTRAST", idx, con.get(f"ContrastName{idx}", "NA"),
                 " ".join(map(str, contrasts[idx - 1])),
                 contrast_pp[idx - 1] if idx <= len(contrast_pp) else "NA")
    with bids.open() if bids else open("/dev/null") as stream:
        events = list(csv.DictReader(stream, delimiter="\t"))
    aliases = {
        "guess_allLeftButton": {"guess_leftButton_computer", "guess_leftButton_face"},
        "guess_allRightButton": {"guess_rightButton_computer", "guess_rightButton_face"},
        "guess_allFace": {"guess_leftButton_face", "guess_rightButton_face"},
        "guess_allComputer": {"guess_leftButton_computer", "guess_rightButton_computer"},
    }
    # The generated FSF supplies the original EV mapping. Derivatives, if present,
    # alter the real-column order. The saved contrast vector above remains authoritative.
    column = 0
    weights = contrasts[cope - 1]
    actual_weights = {}
    target_ev_heights = []
    target_ev_timing = []
    target_ev_pp = []
    target_ev_hrf = []
    for idx in range(1, int(fsf.get("fmri(evs_orig)", "0")) + 1):
        field = lambda k: fsf.get(f"fmri({k}{idx})", "")
        column += 1
        custom = field("custom")
        weight = weights[column - 1] if column <= len(weights) else 0
        if weight:
            actual_weights[Path(custom).stem.lstrip("_")] = weight
            target_ev_hrf.append(field("shape") == "3" and field("convolve") == "3" and
                                 field("convolve_phase") == "0")
        if field("shape") == "3" and custom and column <= len(matrix[0]):
            evfile = resolve_input(custom, feat)
            rows = [tuple(map(float, line.split())) for line in read(evfile).splitlines()
                    if line.strip()] if evfile else []
            valid_rows = [row for row in rows if len(row) == 3]
            durations = [r[1] for r in valid_rows]
            heights = sorted({r[2] for r in valid_rows})
            samples = [row[column - 1] for row in matrix]
            label = Path(custom).stem.lstrip("_")
            trials = aliases.get(label, {label})
            expected = sorted((float(e["onset"]), float(e["duration"])) for e in events
                              if e["trial_type"] in trials)
            actual = sorted(r[:2] for r in valid_rows)
            match = len(expected) == len(actual) and all(
                abs(x - y) <= 1e-5 for a, b in zip(expected, actual) for x, y in zip(a, b))
            if weight:
                target_ev_heights.append(heights == [1.0])
                target_ev_timing.append(match if bids and evfile else None)
                if column <= len(pp):
                    target_ev_pp.append(number(pp[column - 1]))
            orth = [j for j in range(int(fsf.get("fmri(evs_orig)", "0")) + 1)
                    if fsf.get(f"fmri(ortho{idx}.{j})") == "1"]
            emit("EV", idx, field("evtitle"), evfile or custom, f"rows={len(valid_rows)}/{len(rows)}",
                 f"duration_s={min(durations, default=math.nan):.5g}..{max(durations, default=math.nan):.5g}",
                 f"height={heights}", f"hrf={field('convolve')}/{field('convolve_phase')}",
                 f"derivative={field('deriv_yn')}", f"orth={orth}",
                 f"PPheight={pp[column-1] if column <= len(pp) else 'NA'}",
                 f"matrix_range={max(samples)-min(samples):.6g}",
                 f"bids_onset_duration_match={match if bids and evfile else 'NA'}")
        column += field("deriv_yn") == "1"
    if record is not None:
        if mask.name == "mask_VSconstrained.nii.gz":
            expected_weights = {f"outcome_{partner}_{trial}": weight
                                for partner in ("computer", "stranger")
                                for trial, weight in (("reward", 1), ("punish", -1))}
        elif mask.name == "mask_rFFA.nii.gz":
            expected_weights = {"guess_allFace": 1, "guess_allComputer": -1}
        else:
            sign = -1 if mask.name == "mask_leftMotor.nii.gz" else 1
            expected_weights = {"guess_allLeftButton": sign, "guess_allRightButton": -sign}
        record["contrast_expected"] = (actual_weights == expected_weights and
                                       sum(w != 0 for w in weights) == len(actual_weights))
        if mask.name == "mask_leftMotor.nii.gz":
            record["left_motor_uses_left_gt_right"] = actual_weights == {
                "guess_allLeftButton": 1, "guess_allRightButton": -1}
        record["target_evs_unit_height"] = bool(target_ev_heights) and all(target_ev_heights)
        record["target_evs_match_bids"] = (all(target_ev_timing) if target_ev_timing and
                                           None not in target_ev_timing else None)
        record["target_evs_double_gamma_zero_phase"] = bool(target_ev_hrf) and all(target_ev_hrf)
        record["mean_target_ev_pp"] = sum(target_ev_pp) / len(target_ev_pp) if target_ev_pp else math.nan
        if cope <= len(contrast_pp):
            record["contrast_pp"] = number(contrast_pp[cope - 1])


emit("PROJECT", root)
emit("GIT_HEAD", run("git", "-C", str(root), "rev-parse", "HEAD") if (root / ".git").exists() else "NA")
figure_tables = sorted((root / "derivatives/plots").glob("*act_beta*base*.csv"))
emit("FIGURE_TABLES", *figure_tables)
subjects = list(dict.fromkeys(re.sub("^sub-", "", sub) for sub in args.subjects))
if not subjects:
    included = set(read(root / "code/sublist-included.txt").split())
    for channels in (20, 64):
        eligible = sorted(s for s, c in coil.items() if c == channels and s in included and
                          all(extraction(s, acq, roi).is_file() for acq in acquisitions
                              for roi in ("VSconstrained", "rFFA", "leftMotor", "rightMotor", "bilateralMotor")))
        start = max(0, (len(eligible) - 2) // 2)
        subjects.extend(eligible[start:start + 2])
    if not subjects:
        parser.error("No complete extraction sets found. Supply local subject codes as arguments.")
records = defaultdict(list)
bilateral_checks = defaultdict(Counter)
for sub in subjects:
    for acq in acquisitions:
        emit("RUN", f"sub-{sub}", coil.get(sub, "unknown"), acq)
        bilateral = extraction(sub, acq, "bilateralMotor")
        left = number(read(extraction(sub, acq, "leftMotor")).strip())
        right = number(read(extraction(sub, acq, "rightMotor")).strip())
        bilateral_saved = number(read(bilateral).strip())
        emit("BILATERAL_SAVED", bilateral, bilateral_saved, f"hemisphere_average={(left+right)/2:.9g}")
        if all(math.isfinite(value) for value in (bilateral_saved, left, right)):
            bilateral_checks[acq]["comparable"] += 1
            if compare(bilateral_saved, (left + right) / 2, abs_tol=0.001):
                bilateral_checks[acq]["matches_signed_average"] += 1
        func = root / f"bids/sub-{sub}/func"
        bids_files = sorted(func.glob(f"*task-sharedreward*_acq-{acq}_events.tsv"))
        bids = bids_files[0] if len(bids_files) == 1 else None
        emit("BIDS_EVENTS", *bids_files)
        for path in sorted(func.glob(f"*task-sharedreward*_acq-{acq}*_bold.json")):
            if "part-phase" in path.name or re.search(r"_echo-[2-9](?:_|\.)", path.name):
                continue
            try:
                sidecar = json.loads(read(path))
            except ValueError:
                emit("UNREADABLE_BIDS_JSON", path)
                continue
            emit("BIDS_ACQUISITION", path, sidecar.get("RepetitionTime"), sidecar.get("ReceiveCoilName"))
        for roi, model, cope in sources:
            saved = extraction(sub, acq, roi)
            beta = number(read(saved).strip())
            emit("EXTRACTION", saved, beta)
            mask = root / f"masks/mask_{roi}.nii.gz"
            stem = f"L1_task-sharedreward_model-{model}_type-act_acq-{acq}"
            canonical = root / f"derivatives/fsl/sub-{sub}/{stem}_sm-0_denoising-base.feat"
            dirs = sorted((root / f"derivatives/fsl/sub-{sub}").glob(f"{stem}_*_denoising-base*.feat"))
            matches = []
            for feat in dirs:
                for index in (cope, 4) if roi == "leftMotor" else (cope,):
                    image = feat / f"stats/cope{index}.nii.gz"
                    if check_mask(image, mask):
                        observed = number(run("fslmeants", "-i", str(image), "-m", str(mask)))
                        match = compare(beta, observed)
                        emit("COPE_CANDIDATE", image, observed, "MATCH" if match else "")
                        if match:
                            matches.append((feat, index))
            record = {"sub": sub, "extraction_present": math.isfinite(beta), "match_count": len(matches)}
            records[acq, roi].append(record)
            if len(matches) == 1:
                feat, index = matches[0]
                record["source"] = "canonical" if feat == canonical else (
                    "update" if feat.name.endswith("_update.feat") else "other_base")
                record["cope"] = index
                inspect(feat, index, mask, bids, record)
            else:
                emit("PROVENANCE_UNRESOLVED", roi, len(matches), *dirs)
                if args.local_details and canonical in dirs:
                    emit("CANONICAL_CANDIDATE_ONLY", canonical)
                    inspect(canonical, cope, mask, bids)


def finite(rows, key):
    return [row[key] for row in rows if key in row and math.isfinite(row[key])]


def rounded_mean(values, increment, minimum=3):
    return round(sum(values) / len(values) / increment) * increment if len(values) >= minimum else None


if not args.local_details:
    output = {
        "sample_counts_by_coil": {str(c): sum(coil.get(s, "unknown") == c for s in subjects)
                                  for c in (20, 64, "unknown")},
        "candidate_figure_csv_count": len(figure_tables),
        "bilateral_signed_average_checks": dict(bilateral_checks),
        "by_protocol_and_roi": {},
        "within_participant_roi_baseline_spread": {},
    }
    for (acq, roi), rows in records.items():
        checks = ("tr_matches_input", "design_rows_match", "contrast_expected",
                  "left_motor_uses_left_gt_right", "target_evs_unit_height", "target_evs_match_bids",
                  "target_evs_double_gamma_zero_phase", "run_scaling_logged", "volume_scaling_logged")
        entry = {
            "saved_extractions": sum(row["extraction_present"] for row in rows),
            "matched_runs": dict(Counter(f'{row["source"]}_cope{row["cope"]}' for row in rows
                                         if row["match_count"] == 1)),
            "multiple_matches": sum(row["match_count"] > 1 for row in rows),
            "input_kind_counts": dict(Counter(row["input_kind"] for row in rows if "input_kind" in row)),
            "settings_counts": {key: dict(Counter(round(v, 5) for v in finite(rows, key)))
                                for key in ("tr", "input_tr", "norm_yn", "smooth", "temphp_yn")},
            "checks": {key: {label: sum(row.get(key) is value for row in rows)
                             for label, value in (("yes", True), ("no", False))}
                       for key in checks},
        }
        for key, increment in (("global_mean", 100), ("roi_mean", 100), ("coverage", 0.05),
                               ("input_mean", 10), ("upstream_mean", 10),
                               ("mean_target_ev_pp", 0.05), ("contrast_pp", 0.05)):
            values = finite(rows, key)
            mean = rounded_mean(values, increment)
            entry[key] = {"count": len(values), "rounded_mean": round(mean, 4) if mean is not None else None}
        output["by_protocol_and_roi"].setdefault(acq, {})[roi] = entry
    for roi, _, _ in sources:
        for channels in (20, 64):
            spreads = []
            for sub in subjects:
                if coil.get(sub) != channels:
                    continue
                values = [v for acq in acquisitions for v in
                          finite([row for row in records[acq, roi] if row["sub"] == sub], "roi_mean")]
                if len(values) == len(acquisitions) and min(values) > 0:
                    spreads.append(100 * (max(values) - min(values)) / (sum(values) / len(values)))
            output["within_participant_roi_baseline_spread"].setdefault(roi, {})[str(channels)] = {
                "complete_series": len(spreads),
                "mean_percent_range_rounded_to_5_points": rounded_mean(spreads, 5, minimum=2),
            }
    print(json.dumps(output, indent=2, allow_nan=False))
