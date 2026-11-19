#!/usr/bin/env python3
"""
Figure 1 -- Reward-processing (shared-reward card-guessing) task design.

Redraws the task schematic at publication resolution. The original figure
existed only as a low-resolution screenshot embedded in the manuscript; this
script rebuilds the same layout as vector shapes and text, using the task's
own partner images from stimuli/Images/.

Timing labels follow the task code (stimuli/SharedReward_5button.py) and the
Methods: decision phase up to 2.5 s, outcome 1.0 s, ITI drawn from 1, 2, 3 or
4 s (mean 2.46 s across the run logs).

Usage:  python code/make_figure1_task_design.py
Writes: figures/Fig1_task_design.{png,tiff}
        (and a copy in derivatives/publication_figures/ when that folder exists)
"""
from pathlib import Path
import shutil

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, PathPatch
from matplotlib.path import Path as MplPath
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = PROJECT_ROOT / 'stimuli' / 'Images'
OUT_DIR = PROJECT_ROOT / 'figures'
PUB_DIR = PROJECT_ROOT / 'derivatives' / 'publication_figures'
BASENAME = 'Fig1_task_design'

# Timing labels (seconds)
DECISION_LABEL = '2.5 sec'
OUTCOME_LABEL = '1.0 sec'
ITI_LABEL = '1–4 sec'

# Layout is specified in "canvas units" matching the original 1404 x 782
# schematic, so element positions can be checked against it directly.
CANVAS_W, CANVAS_H = 1404, 782
FIG_WIDTH_IN = 7.0                       # J Neurosci two-column width
DPI = 600
PT_PER_UNIT = FIG_WIDTH_IN * 72 / CANVAS_W   # converts canvas units to points

CARD_GRAY = '#808080'
SIL_BG = (197, 202, 221)
LINE_GRAY = '#8c8c8c'
TEXT = '#1a1a1a'
GREEN = '#6cc04a'
DARK_RED = '#7a2622'
FONT = 'Arial'


def lw(units):
    """Line width in points for a stroke `units` canvas pixels wide."""
    return units * PT_PER_UNIT


def fs(units):
    """Font size in points for an em height of `units` canvas pixels."""
    return units * PT_PER_UNIT


def silhouette_image(size_px=900):
    """Partner silhouette, re-rendered with crisp edges at high resolution."""
    img = Image.open(IMAGE_DIR / 'olderadult.png').convert('RGB')
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    img = img.resize((size_px, size_px), Image.BICUBIC)
    a = np.asarray(img).astype(float)
    bg = np.array(SIL_BG, float)
    # Fraction of the way from background to white, sharpened to a clean edge
    frac = ((a.mean(2) - bg.mean()) / (255 - bg.mean())).clip(0, 1)
    alpha = 1 / (1 + np.exp(-(frac - 0.5) * 18))
    out = bg[None, None, :] * (1 - alpha[..., None]) + 255 * alpha[..., None]
    return out.astype(np.uint8)


def computer_image(scale=6):
    img = Image.open(IMAGE_DIR / 'computer.png').convert('RGBA')
    img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    return np.asarray(img)


def place_image(ax, arr, x0, y0, x1, y1, z=3):
    ax.imshow(arr, extent=(x0, x1, y1, y0), interpolation='lanczos', zorder=z)


def card(ax, x0, y0, x1, y1, inset=11, z=2):
    """Gray card with an inset white border, as presented in the task."""
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=CARD_GRAY, edgecolor='none', zorder=z))
    ax.add_patch(Rectangle((x0 + inset, y0 + inset), x1 - x0 - 2 * inset, y1 - y0 - 2 * inset,
                           facecolor='none', edgecolor='white', linewidth=lw(3.2), zorder=z + 0.1))


def text(ax, x, y, s, size, color=TEXT, weight='normal', z=5):
    ax.text(x, y, s, ha='center', va='center', fontsize=fs(size), color=color,
            fontfamily=FONT, fontweight=weight, zorder=z)


def check_icon(ax, cx, cy, s=30, z=5):
    ax.add_patch(Rectangle((cx - s / 2, cy - s / 2), s, s, facecolor='none', edgecolor=GREEN,
                           linewidth=lw(3.5), zorder=z))
    ax.plot([cx - s * 0.30, cx - s * 0.05, cx + s * 0.42], [cy + s * 0.02, cy + s * 0.28, cy - s * 0.42],
            color=GREEN, linewidth=lw(4.5), solid_capstyle='round', solid_joinstyle='round', zorder=z + 0.1)


def x_icon(ax, cx, cy, s=30, z=5):
    ax.add_patch(Rectangle((cx - s / 2, cy - s / 2), s, s, facecolor='none', edgecolor=DARK_RED,
                           linewidth=lw(3.0), zorder=z))
    d = s * 0.26
    for sx in (1, -1):
        ax.plot([cx - d, cx + d], [cy - sx * d, cy + sx * d], color=DARK_RED, linewidth=lw(2.6),
                solid_capstyle='round', zorder=z + 0.1)


def double_arrow_icon(ax, cx, cy, w=38, h=24, z=5):
    """Hollow left-right arrow (neutral outcome)."""
    hw, hh, sh = w / 2, h / 2, h * 0.2   # half width, half height, half shaft height
    head = w * 0.30
    pts = [(-hw, 0), (-hw + head, -hh), (-hw + head, -sh), (hw - head, -sh), (hw - head, -hh),
           (hw, 0), (hw - head, hh), (hw - head, sh), (-hw + head, sh), (-hw + head, hh)]
    ax.add_patch(Polygon([(cx + x, cy + y) for x, y in pts], closed=True, facecolor='none',
                         edgecolor='white', linewidth=lw(2.6), joinstyle='miter', zorder=z))


def brace(ax, x0=190, xm=216, xtip=245, y_top=112, y_tip=182, y_bot=380, r=12, z=2):
    """Right-facing curly brace grouping the two partner types."""
    P = MplPath
    verts = [(x0, y_top), (xm - r, y_top), (xm, y_top), (xm, y_top + r),
             (xm, y_tip - r), (xm, y_tip), (xm + r, y_tip), (xtip, y_tip),
             (xm + r, y_tip), (xm, y_tip), (xm, y_tip + r),
             (xm, y_bot - r), (xm, y_bot), (xm - r, y_bot), (x0, y_bot)]
    codes = [P.MOVETO, P.LINETO, P.CURVE3, P.CURVE3,
             P.LINETO, P.CURVE3, P.CURVE3, P.LINETO,
             P.MOVETO, P.CURVE3, P.CURVE3,
             P.LINETO, P.CURVE3, P.CURVE3, P.LINETO]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor='none', edgecolor=LINE_GRAY,
                           linewidth=lw(2.2), capstyle='round', zorder=z))


def phase_bracket(ax, x0, x1, label, duration, y_end=660, y_line=676, y_tick=692):
    xc = (x0 + x1) / 2
    ax.plot([x0, x0, x1, x1], [y_end, y_line, y_line, y_end], color=LINE_GRAY, linewidth=lw(2.0),
            solid_joinstyle='round', zorder=2)
    ax.plot([xc, xc], [y_line, y_tick], color=LINE_GRAY, linewidth=lw(2.0), zorder=2)
    text(ax, xc, 714, label, 25)
    text(ax, xc, 743, duration, 25)


def make_figure():
    fig = plt.figure(figsize=(FIG_WIDTH_IN, FIG_WIDTH_IN * CANVAS_H / CANVAS_W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CANVAS_W)
    ax.set_ylim(CANVAS_H, 0)
    ax.axis('off')

    sil = silhouette_image()

    # --- Partner types: confederate and computer ---
    place_image(ax, sil, 24, 20, 184, 180)
    ax.add_patch(Rectangle((24, 180), 160, 85, facecolor=CARD_GRAY, edgecolor='none', zorder=2))
    text(ax, 104, 223, 'Confederate', 25, color='white')

    ax.add_patch(Rectangle((26, 290), 158, 182, facecolor=CARD_GRAY, edgecolor='none', zorder=2))
    place_image(ax, computer_image(), 30, 300, 180, 300 + 150 * 180 / 220)
    text(ax, 105, 456, 'computer', 23, color='white', weight='bold')

    brace(ax)

    # --- Decision phase: partner above a face-down card ---
    ax.add_patch(Rectangle((255, 84), 178, 410, facecolor=CARD_GRAY, edgecolor='none', zorder=2))
    place_image(ax, sil, 270, 92, 420, 242)
    text(ax, 345, 262, 'Confederate', 25, color='white')
    ax.add_patch(Rectangle((266, 281), 159, 205, facecolor='none', edgecolor='white',
                           linewidth=lw(3.2), zorder=3))
    text(ax, 345, 383, '?', 22, color='white')

    # --- Outcome phase: reward, loss, neutral, missed response ---
    for i, (x0, y0) in enumerate([(528, 128), (649, 213), (773, 313), (898, 410)]):
        card(ax, x0, y0, x0 + 176, y0 + 213, z=2 + i)
    check_icon(ax, 618, 190, z=7)
    text(ax, 617, 238, '9', 52, color='white', z=7)
    x_icon(ax, 737, 280, z=8)
    text(ax, 737, 328, '4', 52, color='white', z=8)
    double_arrow_icon(ax, 861, 381, z=9)
    text(ax, 861, 429, '5', 52, color='white', z=9)
    text(ax, 988, 524, '#', 44, color='white', z=10)

    # --- Inter-trial interval: fixation ---
    card(ax, 1172, 268, 1352, 494)
    text(ax, 1263, 382, '+', 34, color='white', weight='bold')

    # --- Phase labels ---
    phase_bracket(ax, 255, 433, 'Decision Phase', DECISION_LABEL)
    phase_bracket(ax, 529, 1077, 'Outcome Phase', OUTCOME_LABEL)
    phase_bracket(ax, 1172, 1352, 'ITI', ITI_LABEL)
    return fig


def main():
    OUT_DIR.mkdir(exist_ok=True)
    fig = make_figure()
    png, tiff = OUT_DIR / f'{BASENAME}.png', OUT_DIR / f'{BASENAME}.tiff'
    fig.savefig(png, dpi=DPI, facecolor='white')
    fig.savefig(tiff, dpi=DPI, facecolor='white', pil_kwargs={'compression': 'tiff_lzw'})
    plt.close(fig)
    print(f'Saved {png.relative_to(PROJECT_ROOT)} and {tiff.relative_to(PROJECT_ROOT)}')
    if PUB_DIR.is_dir():
        for f in (png, tiff):
            shutil.copy2(f, PUB_DIR / f.name)
        print(f'Copied to {PUB_DIR.relative_to(PROJECT_ROOT)}/')


if __name__ == '__main__':
    main()
