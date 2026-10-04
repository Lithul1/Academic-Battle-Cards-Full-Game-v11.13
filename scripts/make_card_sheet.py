#!/usr/bin/env python3
"""
ACADEMIC BATTLE CARDS - Print Sheet Generator
=============================================
Turns a folder of card images into a print-ready, DOUBLE-SIDED PDF for
hand-cutting or a Cricut. Cards print at exactly 2.5 x 3.5 in (poker size).

------------------------------------------------------------------
HOW TO USE  (macOS - copy/paste into Terminal, one time setup first)
------------------------------------------------------------------
1) Install the one library this needs (only needed once):
       pip3 install reportlab pillow

2) Put this script in a folder. Next to it, make a folder called  cards
   and drop your card FRONT images inside (PNG or JPG).
   They print in alphabetical order, so name them 01.png, 02.png, ...

3) (Optional) Put a back-of-card image next to the script named  back.png
   If you don't, a plain "Academic Battle Cards" back is drawn for you.

4) Run it:
       python3 make_card_sheet.py

5) You get  card_sheet.pdf . Open it and print:
       - Scale: 100%  /  "Actual Size"   (NOT "Fit to Page")
       - Two-Sided:  ON  (Flip on Long Edge)
   Then cut along the card borders. The little corner marks are for lining
   up a Cricut "Print then Cut" or a paper trimmer.

------------------------------------------------------------------
TWEAKABLE SETTINGS  (edit the CONFIG block below if you want)
------------------------------------------------------------------
"""

import os, glob, sys

# ---------------- CONFIG ----------------
CARDS_DIR   = "cards"        # folder holding your front images
BACK_IMG    = "back.png"     # optional uniform back; if missing, one is drawn
OUTPUT_PDF  = "card_sheet.pdf"

CARD_W_IN   = 2.5            # card width  (inches)
CARD_H_IN   = 3.5           # card height (inches)
COLS        = 3             # cards across
ROWS        = 2             # cards down   ->  COLS*ROWS = cards per page
GAP_IN      = 0.0          # gap between cards in inches (0 = edge-to-edge)

CUT_BORDER  = True         # thin line on each card edge (cut on it)
CROP_MARKS  = True         # registration marks at the grid corners
PER_CARD_BACKS = False     # True only if 'backs' folder holds one back per card
BACKS_DIR   = "backs"      # used only when PER_CARD_BACKS = True
# ----------------------------------------

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
except ImportError:
    sys.exit("Missing 'reportlab'. Run:  pip3 install reportlab pillow")

PAGE_W, PAGE_H = letter                 # 8.5 x 11 in, in points
CARD_W, CARD_H = CARD_W_IN*inch, CARD_H_IN*inch
GAP = GAP_IN*inch
PER_PAGE = COLS*ROWS

grid_w = COLS*CARD_W + (COLS-1)*GAP
grid_h = ROWS*CARD_H + (ROWS-1)*GAP
X0 = (PAGE_W - grid_w)/2.0              # left of grid
Y0 = (PAGE_H - grid_h)/2.0             # bottom of grid (reportlab is bottom-up)

def cell_xy(idx, mirror=False):
    """Bottom-left (x,y) in points for slot idx (0..PER_PAGE-1), row-major from top-left."""
    col = idx % COLS
    row = idx // COLS
    if mirror:                          # reverse columns for long-edge duplex + per-card backs
        col = (COLS-1) - col
    x = X0 + col*(CARD_W+GAP)
    y = PAGE_H - Y0 - (row+1)*CARD_H - row*GAP
    return x, y

def draw_cut_border(c, x, y):
    if not CUT_BORDER: return
    c.setLineWidth(0.5); c.setStrokeColorRGB(0.12,0.12,0.12)
    c.rect(x, y, CARD_W, CARD_H)

def draw_crop_marks(c):
    if not CROP_MARKS: return
    c.setLineWidth(0.5); c.setStrokeColorRGB(0,0,0)
    left, right = X0, X0+grid_w
    bottom, top = Y0, Y0+grid_h
    m = 0.16*inch; off = 0.05*inch
    for (px, py) in [(left,bottom),(right,bottom),(left,top),(right,top)]:
        c.line(px-off-m, py, px-off, py)   # horizontal tick
        c.line(px+off, py, px+off+m, py)
        c.line(px, py-off-m, px, py-off)   # vertical tick
        c.line(px, py+off, px, py+off+m)

def draw_default_back(c, x, y):
    """A plain themed back if no back.png supplied."""
    c.saveState()
    c.setFillColorRGB(0.16,0.13,0.10); c.rect(x, y, CARD_W, CARD_H, fill=1, stroke=0)
    pad = 0.28*inch
    c.setStrokeColorRGB(0.89,0.66,0.17); c.setLineWidth(2)
    c.roundRect(x+pad, y+pad, CARD_W-2*pad, CARD_H-2*pad, 6, fill=0, stroke=1)
    c.setFillColorRGB(0.89,0.66,0.17)
    try: c.setFont("Helvetica-Bold", 15)
    except: c.setFont("Helvetica", 15)
    cx = x+CARD_W/2
    for i,line in enumerate(["ACADEMIC","BATTLE","CARDS"]):
        c.drawCentredString(cx, y+CARD_H-pad-0.5*inch-i*0.28*inch, line)
    c.setFillColorRGB(0.94,0.90,0.82); c.setFont("Helvetica", 22)
    c.drawCentredString(cx, y+CARD_H/2-0.35*inch, "\u2694")
    c.setFillColorRGB(0.79,0.64,0.29); c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx, y+pad+0.28*inch, "L A K E F R O N T   U")
    c.restoreState()

def place_image(c, path, x, y):
    """Downscale + JPEG-compress to ~300 DPI so the PDF stays small and opens reliably."""
    from reportlab.lib.utils import ImageReader
    try:
        from PIL import Image
        import io
        target_w = int(CARD_W_IN*300); target_h = int(CARD_H_IN*300)   # 750x1050 @ 300dpi
        im = Image.open(path).convert("RGB").resize((target_w, target_h), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=90); buf.seek(0)
        c.drawImage(ImageReader(buf), x, y, CARD_W, CARD_H, preserveAspectRatio=False)
    except Exception:
        c.drawImage(ImageReader(path), x, y, CARD_W, CARD_H,
                    preserveAspectRatio=False, mask='auto')

def main():
    if not os.path.isdir(CARDS_DIR):
        os.makedirs(CARDS_DIR, exist_ok=True)
        sys.exit(f"Created empty '{CARDS_DIR}/' folder. Put your card front images "
                 f"in it (PNG/JPG), then run this again.")
    fronts = sorted(glob.glob(os.path.join(CARDS_DIR,"*.png")) +
                    glob.glob(os.path.join(CARDS_DIR,"*.jpg")) +
                    glob.glob(os.path.join(CARDS_DIR,"*.jpeg")))
    if not fronts:
        sys.exit(f"No images found in '{CARDS_DIR}/'. Add PNG/JPG card fronts and rerun.")

    per_card_backs = []
    if PER_CARD_BACKS and os.path.isdir(BACKS_DIR):
        per_card_backs = sorted(glob.glob(os.path.join(BACKS_DIR,"*.png")) +
                                glob.glob(os.path.join(BACKS_DIR,"*.jpg")))
    have_back_img = os.path.exists(BACK_IMG)

    c = canvas.Canvas(OUTPUT_PDF, pagesize=letter)
    n_pages = (len(fronts)+PER_PAGE-1)//PER_PAGE

    for pg in range(n_pages):
        batch = fronts[pg*PER_PAGE:(pg+1)*PER_PAGE]
        # ---- FRONT page ----
        for i, path in enumerate(batch):
            x,y = cell_xy(i)
            place_image(c, path, x, y)
            draw_cut_border(c, x, y)
        draw_crop_marks(c)
        c.showPage()
        # ---- BACK page (same slots; mirror columns only if per-card backs) ----
        mirror = PER_CARD_BACKS
        for i in range(len(batch)):
            x,y = cell_xy(i, mirror=mirror)
            if PER_CARD_BACKS and per_card_backs:
                bpath = per_card_backs[(pg*PER_PAGE+i) % len(per_card_backs)]
                place_image(c, bpath, x, y)
            elif have_back_img:
                place_image(c, BACK_IMG, x, y)
            else:
                draw_default_back(c, x, y)
            draw_cut_border(c, x, y)
        draw_crop_marks(c)
        c.showPage()

    c.save()
    print(f"Wrote {OUTPUT_PDF}  ({len(fronts)} cards, {n_pages} sheet(s) = {n_pages*2} PDF pages).")
    print("Print at 100% / Actual Size, two-sided, flip on long edge. Cut on the card borders.")

if __name__ == "__main__":
    main()
