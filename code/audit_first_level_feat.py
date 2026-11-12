#!/usr/bin/env python3
"""Read existing first-level FEAT files and print diagnostics to stdout."""
import argparse
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
parser.add_argument("subjects", nargs="*", default=["10108", "10188", "10203", "10320"])
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


def emit(*values):
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
    except ValueError:
        return math.nan


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


def inspect(feat, cope, mask, bids):
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
        emit("GLOBAL_BASELINE", run("fslstats", str(mean), "-k", str(featmask), "-m", "-V"))
    if check_mask(mean, mask):
        emit("ROI_BASELINE", mask.stem, run("fslmeants", "-i", str(mean), "-m", str(mask)),
             "nonzero_mean_and_count=" + run("fslstats", str(mean), "-k", str(mask), "-M", "-V"),
             "mask_count=" + run("fslstats", str(mask), "-V"))
    if image and image not in input_measured and check_mask(image, featmask):
        input_measured.add(image)
        upstream = image.with_name(re.sub(r"_\d+mm(?=\.nii)", "", image.name))
        for img in dict.fromkeys((image, upstream)):
            if check_mask(img, featmask):
                emit("INPUT_MASKED_MEAN", img, run("fslstats", str(img), "-k", str(featmask), "-m"))

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
    if not saw_scale:
        emit("SCALING_LOG_UNAVAILABLE", feat)

    mat, matrix = vest(feat / "design.mat")
    con, contrasts = vest(feat / "design.con")
    emit("DESIGN", mat.get("NumPoints"), mat.get("NumWaves"), f"rows={len(matrix)}")
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
    for idx in range(1, int(fsf.get("fmri(evs_orig)", "0")) + 1):
        field = lambda k: fsf.get(f"fmri({k}{idx})", "")
        column += 1
        custom = field("custom")
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


emit("PROJECT", root)
emit("GIT_HEAD", run("git", "-C", str(root), "rev-parse", "HEAD") if (root / ".git").exists() else "NA")
emit("FIGURE_TABLES", *sorted((root / "derivatives/plots").glob("*act_beta*base*.csv")))
for sub in args.subjects:
    sub = re.sub("^sub-", "", sub)
    for acq in acquisitions:
        emit("RUN", f"sub-{sub}", coil.get(sub, "unknown"), acq)
        def extract(roi):
            return root / ("derivatives/extractions/"
                           f"ts_sub-{sub}_acq_{acq}_type-act_img-beta_mask-{roi}_denoise_base.txt")
        bilateral = extract("bilateralMotor")
        left = number(read(extract("leftMotor")).strip())
        right = number(read(extract("rightMotor")).strip())
        emit("BILATERAL_SAVED", bilateral, read(bilateral).strip(), f"hemisphere_average={(left+right)/2:.9g}")
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
            saved = extract(roi)
            beta = number(read(saved).strip())
            emit("EXTRACTION", saved, beta)
            mask = root / f"masks/mask_{roi}.nii.gz"
            stem = f"L1_task-sharedreward_model-{model}_type-act_acq-{acq}"
            dirs = sorted((root / f"derivatives/fsl/sub-{sub}").glob(f"{stem}_*_denoising-base*.feat"))
            matches = []
            for feat in dirs:
                for index in (cope, 4) if roi == "leftMotor" else (cope,):
                    image = feat / f"stats/cope{index}.nii.gz"
                    if check_mask(image, mask):
                        observed = number(run("fslmeants", "-i", str(image), "-m", str(mask)))
                        match = math.isclose(beta, observed, rel_tol=1e-7, abs_tol=1e-6)
                        emit("COPE_CANDIDATE", image, observed, "MATCH" if match else "")
                        if match:
                            matches.append((feat, index))
            if len(matches) == 1:
                feat, index = matches[0]
                inspect(feat, index, mask, bids)
            else:
                emit("PROVENANCE_UNRESOLVED", roi, len(matches), *dirs)
                canonical = root / f"derivatives/fsl/sub-{sub}/{stem}_sm-0_denoising-base.feat"
                if canonical in dirs:
                    emit("CANONICAL_CANDIDATE_ONLY", canonical)
                    inspect(canonical, cope, mask, bids)
