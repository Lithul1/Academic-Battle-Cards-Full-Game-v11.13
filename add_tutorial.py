#!/usr/bin/env python3
"""
add_tutorial.py — adds the Tutorial menu entry + screen to src/game.src.html.

Usage:   python3 add_tutorial.py src/game.src.html

Additive only: 38 lines inserted, nothing removed or rewritten. Writes a .bak
first, verifies every anchor is present exactly once BEFORE touching anything,
and refuses to run twice. If any anchor is missing or ambiguous it aborts and
leaves your file untouched.

Stdlib only. Python 3.8+.
"""
import sys, os, re, shutil, difflib

VIDEO_ID = '1RsrczPZdgmrLCPOOdt4wsD75VPEvF3nG'

CSS_ANCHOR = ".sub-actions{ display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-top:18px; }\n"
CSS_ADD = """/* ---- tutorial screen (hosted video) ---- */
.tut-frame{ position:relative; aspect-ratio:16/9; width:100%; border:3px solid var(--ink); border-radius:12px; overflow:hidden; background:var(--felt); box-shadow:0 6px 0 #0c2426; }
.tut-frame iframe{ position:absolute; inset:0; width:100%; height:100%; border:0; }
.tut-fall{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px; padding:20px; text-align:center; color:var(--cream-hi); background:var(--felt); }
.tut-fall b{ font-family:var(--disp); font-size:18px; }
.tut-fall small{ font-size:12.5px; opacity:.8; max-width:38ch; line-height:1.5; }
.tut-note{ font-size:12.5px; color:#6b5c42; text-align:center; margin:10px 0 0; line-height:1.55; }
.tut-note a{ color:var(--red-dk); }
"""

BTN_ANCHOR = '<button class="menu-btn" data-do="go-guide">'
BTN_ADD = ('<button class="menu-btn" data-do="go-tutorial">'
           '<span class="menu-ic">\U0001F3AC</span>'
           '<span class="menu-tx"><b>Watch the Tutorial</b>'
           '<small>Two minutes \u2014 how a turn works, start to finish</small></span>'
           '<span class="menu-go">\u203a</span></button>\n      ')

ROUTE_ANCHOR = "    else if(d==='go-guide'){ APP.screen='guide'; render(); }\n"
ROUTE_ADD = "    else if(d==='go-tutorial'){ APP.screen='tutorial'; render(); }\n"

DISP_ANCHOR = "  if(APP.screen==='guide'){ root.innerHTML=guideScreen()+_ov(); return; }\n"
DISP_ADD = "  if(APP.screen==='tutorial'){ root.innerHTML=tutorialScreen()+_ov(); return; }\n"

FN_ANCHOR = "function guideScreen(){\n"
FN_ADD = """/* ---------- tutorial (hosted video) ---------- */
const ABC_TUTORIAL_ID='%s';
function tutorialScreen(){
  const emb='https://drive.google.com/file/d/'+ABC_TUTORIAL_ID+'/preview';
  const url='https://drive.google.com/file/d/'+ABC_TUTORIAL_ID+'/view';
  return `<div class="title-screen sub-screen">
    <img class="title-logo sm" src="${window.ABC_LOGO||''}" alt="Academic Battle Cards">
    <h2 class="sub-h">Tutorial</h2>
    <div class="gd-tag">Two minutes, start to finish</div>
    <div class="rules">
      <div class="tut-frame">
        <div class="tut-fall">
          <b>Video needs a connection</b>
          <small>The tutorial streams from Google Drive. If you are offline it will not load \\u2014 the Quickstart Guide covers the same ground in text.</small>
        </div>
        <iframe src="${emb}" title="Academic Battle Cards \\u2014 how to play" loading="lazy"
          allow="autoplay; fullscreen" allowfullscreen referrerpolicy="no-referrer"></iframe>
      </div>
      <p class="tut-note">Trouble playing it here? <a href="${url}" target="_blank" rel="noopener noreferrer">Open the video in a new tab</a>.</p>
      <div class="gd-box"><b class="lbl">What it covers</b>The goal, the table, reading a card, all three phases, charging with trivia, statuses, and Bookmarks &amp; Critical Lenses.</div>
    </div>
    <div class="sub-actions">
      <button class="toolbtn" data-do="menu">\\u2039 Back to menu</button>
      <button class="bigbtn" data-do="go-guide">Read the Quickstart Guide \\u203a</button>
    </div>
  </div>`;
}
""" % VIDEO_ID

# (anchor, replacement, label) — replacement is built from the anchor so nothing is lost
EDITS = [
    (CSS_ANCHOR,   CSS_ANCHOR + CSS_ADD,   "CSS rules"),
    (BTN_ANCHOR,   BTN_ADD + BTN_ANCHOR,   "menu entry"),
    (ROUTE_ANCHOR, ROUTE_ADD + ROUTE_ANCHOR, "click router case"),
    (DISP_ANCHOR,  DISP_ANCHOR + DISP_ADD, "screen dispatcher"),
    (FN_ANCHOR,    FN_ADD + FN_ANCHOR,     "tutorialScreen()"),
]


def die(msg):
    print("\n  ABORTED — your file was not modified.\n  " + msg + "\n")
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        die("Usage: python3 add_tutorial.py src/game.src.html")
    path = sys.argv[1]
    if not os.path.isfile(path):
        die("No such file: %s" % path)

    src = open(path, encoding='utf-8').read()

    if 'go-tutorial' in src or 'tutorialScreen' in src:
        die("This file already has the tutorial wiring. Nothing to do.")

    # verify EVERY anchor before changing anything
    problems = []
    for anchor, _, label in EDITS:
        n = src.count(anchor)
        if n != 1:
            problems.append("  %-22s anchor found %d times (expected 1)" % (label + ":", n))
    if problems:
        die("Anchor check failed — your source differs from what this patch expects:\n"
            + "\n".join(problems)
            + "\n\n  Send me your current src/game.src.html and I'll rebuild the patch against it.")

    # guard: the CSS block must not land inside an @media rule
    ci = src.index(CSS_ANCHOR)
    mi = src.rfind('@media', 0, ci)
    if mi != -1 and sum(1 if c == '{' else -1 if c == '}' else 0 for c in src[mi:ci]) != 0:
        die("The CSS anchor sits inside an @media block; the rules would be unreachable.")

    out = src
    for anchor, replacement, _ in EDITS:
        out = out.replace(anchor, replacement, 1)

    # additive-only proof
    ol, nl = src.splitlines(True), out.splitlines(True)
    added = removed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ol, nl, autojunk=False).get_opcodes():
        if tag == 'insert':
            added += j2 - j1
        elif tag in ('delete', 'replace'):
            removed += i2 - i1
    if removed:
        die("Internal check failed: the patch would remove %d line(s)." % removed)

    before = len(re.findall(r'__ABCASSET_\d+__', src))
    after = len(re.findall(r'__ABCASSET_\d+__', out))
    if before != after:
        die("Internal check failed: asset placeholder count changed (%d -> %d)." % (before, after))

    bak = path + '.bak'
    shutil.copyfile(path, bak)
    open(path, 'w', encoding='utf-8').write(out)

    print("\n  Patched %s" % path)
    print("  Backup  %s" % bak)
    print("  %d lines inserted, 0 removed. Asset placeholders unchanged (%d)." % (added, before))
    print("  %s -> %s bytes\n" % (format(len(src), ','), format(len(out), ',')))
    print("  Next:  python3 build.py\n")


if __name__ == '__main__':
    main()
