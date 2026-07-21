#!/usr/bin/env python3
"""
ACADEMIC BATTLE CARDS - Card Image Exporter  (v2, print templates)
==================================================================
Renders your REAL in-game cards into the approved print layouts (2.5x3.5),
ready to drop into the 'cards/' folder for make_card_sheet.py.

Card types are auto-detected and rendered into the right template:
  - Character / Commander -> Variant 3b (windowed art, bracket, passive, footer)
  - Ultra-rare (full-art)  -> 3b full-art (art edge-to-edge, boxes float)
  - ABC (Attack/Block)     -> trivia card (question + A/B/C/D options)
  - Item / Status / Support-> header + name + effect + thematic icon + rarity badge
  - Crit / Lens            -> header + art + name + Passive/Thesis/Reward

ONE-TIME SETUP  (macOS Terminal)
    pip3 install playwright pillow          (add --break-system-packages if needed)
    python3 -m playwright install chromium

HOW TO USE
    1) python3 build.py            (build the game so real art is embedded)
    2) edit MANIFEST below
    3) python3 export_cards.py     (writes PNGs into cards/)
    4) python3 make_card_sheet.py  (lays them out into card_sheet.pdf)
"""
import os, sys

# ---------------- CONFIG ----------------
GAME_FILE = "dist/academic_battle_cards.html"
OUT_DIR   = "cards"

# MANIFEST - cards to export, in print order.
# To include something, put it on its own line inside the MANIFEST = [ ... ] list below.
# To turn a line off, put a # at the start of it.  (Do NOT add words after a line - only the tuple.)
#
# Individual: ("fe","<id>")  ("char","<deck>","<id>")  ("abc","<deck>",<index>)  ("bm",<index>)  ("crit",<index>)
# Bulk:       ("ALL_FE",)  ("ALL_CHARS","<deck>")  ("ALL_ABCS","<deck>")  ("ALL_BMS",)  ("ALL_CRITS",)
# Expansions: ("ALL_EXP_CHARS","<exp>")  ("ALL_EXP_ABCS","<exp>")  ("ALL_EXP_CMDRS","<exp>")  ("ALL_EXP_BMS","<exp>")
#             where <exp> is one of: sengekokujo, modern_hamlet, frankenstein_2077
MANIFEST = [
  # ("fe", "otdesi_1e"),
   # ("ALL_CRITS",),
    # ("ALL_BMS",),

    # --- base decks (remove the # to use) ---
    # ("ALL_CHARS", "othello"),
    # ("ALL_ABCS",  "othello"),

    # --- expansions (remove the # to use) ---
     ("ALL_EXP_CHARS", "sengekokujo"),
    # ("ALL_EXP_ABCS",  "sengekokujo"),
     ("ALL_EXP_CMDRS", "sengekokujo"),
    # ("ALL_EXP_BMS",   "sengekokujo"),
]
# ----------------------------------------

try:
    from playwright.sync_api import sync_playwright
    from PIL import Image  # noqa
except ImportError:
    sys.exit("Missing libs. Run:  pip3 install playwright pillow  &&  python3 -m playwright install chromium")
if not os.path.exists(GAME_FILE):
    sys.exit(f"Can't find '{GAME_FILE}'. Build it first (python3 build.py) or edit GAME_FILE.")
os.makedirs(OUT_DIR, exist_ok=True)

ICONS = [
    (("heal","restore","aid","full hp","medic"), "\U0001FA79"),
    (("glue","stick","stuck","trap"),            "\U0001F578\uFE0F"),
    (("burn","fire","ignite","scorch"),          "\U0001F525"),
    (("rip","tear","shred"),                     "\U0001F4C4"),
    (("smudge","ink","pen","blot"),              "\U0001F58A\uFE0F"),
    (("draw","discard","card","hand"),           "\U0001F0CF"),
    (("double","supercharge","boost","power"),   "\U0001F4A5"),
    (("shield","block","guard","curtain","wall"),"\U0001F6E1\uFE0F"),
    (("weaken","drain","sap"),                   "\U0001FAAB"),
    (("shuffle","swap","switch"),                "\U0001F501"),
    (("spill","liquid","coffee"),                "\u2615"),
    (("time","turn","delay","stall"),            "\u23F3"),
    (("study","book","read","note"),             "\U0001F4D6"),
]
DEFAULT_ICON = "\U0001F516"
def pick_icon(*texts):
    blob=" ".join(t for t in texts if t).lower()
    for keys,ic in ICONS:
        if any(k in blob for k in keys): return ic
    return DEFAULT_ICON

RAR={"C":("#b8b8b8","COMMON"),"U":("#4a9a54","UNCOMMON"),"R":("#3a6ea5","RARE"),
     "E":("#7d3c98","EPIC"),"L":("#d99a2b","LEGENDARY")}
def esc(s): return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
STAR = "\u2605"

FONTS='<link href="https://fonts.googleapis.com/css2?family=Alfa+Slab+One&family=Anton&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">'
CSS = r'''
:root{--paper:#f3ecd8;--ink:#241f1b;--gold:#E3A92B;--cond:'Anton',sans-serif;--disp:'Alfa Slab One',serif;--body:'Spectral',serif}
*{box-sizing:border-box}body{margin:0;background:#2b2620;font-family:var(--body)}
.card{width:750px;height:1050px;background:var(--paper);border:6px solid var(--ink);border-radius:30px;position:relative;overflow:hidden;display:flex;flex-direction:column}
img.art{width:100%;height:100%;object-fit:cover}
.foot{position:absolute;left:0;right:0;bottom:0;height:42px;display:flex;align-items:center;justify-content:center;font-family:var(--cond);letter-spacing:1px;font-size:12px;color:#9a8a6a}
.rar{position:absolute;left:18px;bottom:8px;display:flex;align-items:center;gap:6px;font-family:var(--cond);font-size:13px;letter-spacing:1px;z-index:5}
.rdot{width:14px;height:14px;border-radius:50%;border:2px solid #241f1b}
.hp{background:linear-gradient(#c0392b,#8a1a1a);border:3px solid #000;border-radius:11px;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;width:96px;height:70px}
.hp b{font-family:var(--disp);font-size:28px;line-height:.9}.hp span{font-family:var(--cond);font-size:12px;letter-spacing:2px}
.plate{background:#241f1b;border:3px solid #000;padding:9px 15px;display:flex;align-items:center;justify-content:space-between}
.plate .name{font-family:var(--disp);color:var(--gold);font-size:24px;line-height:1}
.plate .sub{font-family:var(--cond);letter-spacing:1.5px;font-size:13px;color:#c9b58a;margin-top:3px}
.plate .stars{color:var(--gold);letter-spacing:4px;font-size:24px}
.fetab{background:var(--gold);color:#241f1b;font-family:var(--cond);font-size:11px;letter-spacing:1px;writing-mode:vertical-rl;transform:rotate(180deg);display:flex;align-items:center;justify-content:center;padding:2px;border:2px solid #000;border-radius:8px 0 0 8px}
.box{border:2px solid #241f1b;border-radius:11px;color:#fff;padding:11px 16px}
.box.ult{background:linear-gradient(#b33c9a,#7d2870)}.box.atk{background:linear-gradient(#b5402a,#7d2718)}.box.blk{background:linear-gradient(#2a5a96,#1c3f6c)}
.box .tt{display:flex;justify-content:space-between;align-items:center;font-family:var(--disp);font-size:22px}
.box .cost{font-family:var(--cond);font-size:20px;background:rgba(0,0,0,.3);padding:1px 11px;border-radius:8px}
.box .tx{font-size:16px;line-height:1.34;margin-top:6px}
.pass{background:rgba(20,15,12,.94);border:2px solid var(--gold);border-radius:12px;color:#f0e6d2;padding:12px 16px}
.pass .ph{font-family:var(--cond);color:var(--gold);font-size:18px;letter-spacing:1px;margin-bottom:4px}
.pass .pt{font-size:15.5px;line-height:1.32}
.brk{position:absolute;background:#241f1b}
.abchead{padding:20px 28px;color:#fff;font-family:var(--cond);font-size:30px;letter-spacing:1px}
.abc.atk .abchead{background:#a5382a}.abc.blk .abchead{background:#2a6a63}
.abcbody{padding:26px 30px;flex:1;display:flex;flex-direction:column}
.abccharge{font-family:var(--cond);font-size:16px;letter-spacing:1px;color:#8a5a1a}
.abcq{font-size:28px;line-height:1.3;color:#241f1b;margin:16px 0 20px;font-weight:600}
.opt{display:flex;align-items:center;gap:14px;border:3px solid #241f1b;border-radius:12px;padding:13px 18px;margin-bottom:13px;background:#fbf6e8;font-size:22px}
.opt .k{font-family:var(--disp);color:#a5382a;font-size:22px;width:26px}.abc.blk .opt .k{color:#2a6a63}
.ih{padding:20px 28px;background:#241f1b;color:var(--gold);font-family:var(--cond);font-size:28px;letter-spacing:2px}
.ibody{padding:30px 34px;flex:1;display:flex;flex-direction:column;align-items:center;text-align:center}
.iname{font-family:var(--disp);font-size:48px;color:#241f1b;margin-top:6px}
.itxt{font-size:26px;line-height:1.45;color:#3a322b;margin-top:24px}
.iicon{font-size:150px;margin-top:auto;margin-bottom:30px}
.ch{padding:16px 24px;background:var(--gold);color:#241f1b;font-family:var(--cond);font-size:26px;letter-spacing:1px}
.cart{height:330px;margin:16px;border:3px solid #241f1b;border-radius:12px;overflow:hidden;display:flex;align-items:center;justify-content:center;background:#3a2f28;color:#8a7d5e;font-family:var(--cond);font-size:40px}
.cart img{width:100%;height:100%;object-fit:cover}
.cname{text-align:center;font-family:var(--disp);font-size:38px;color:#241f1b;margin:2px 0 12px}
.csec{margin:0 20px 12px;border:2px solid #241f1b;border-radius:10px;overflow:hidden}
.csec .sh{font-family:var(--cond);font-size:15px;padding:7px 14px;color:#fff}
.csec.pass2 .sh{background:#4a3f6a}.csec.thesis .sh{background:#8a5a1a}.csec.reward .sh{background:#2f6a45}
.csec .st{padding:10px 14px;font-size:19px;line-height:1.35;color:#3a322b;background:#fbf6e8}
'''

def footer(rar=None):
    r=""
    if rar and rar in RAR:
        c,n=RAR[rar]; r=f'<div class="rar"><span class="rdot" style="background:{c}"></span>{n}</div>'
    return f'{r}<div class="foot">ACADEMIC BATTLE CARDS\u00ae \u00b7 LAKEFRONT U</div>'

def box(kind,m):
    if not m: return ""
    ic={'ult':'\u2726','atk':'\u2694','blk':'\u26e8'}[kind]
    cost=f'<span class="cost">{esc(m.get("label"))}</span>' if m.get("label") else ""
    return f'<div class="box {kind}"><div class="tt"><span>{ic} {esc(m["n"])}</span>{cost}</div><div class="tx">{esc(m["t"])}</div></div>'

def plate_row(d, stars=0, fe=False):
    fetab='<div class="fetab">1ST ED</div>' if fe else ''
    st=f'<span class="stars">{STAR*stars}</span>' if stars else '<span></span>'
    sub=f'{esc(d.get("deck","")).upper()} \u00b7 {"COMMANDER" if fe else "CHARACTER"}'
    return (f'<div style="display:flex;align-items:stretch;gap:0">{fetab}'
            f'<div class="plate" style="flex:1;border-radius:{"0" if fe else "8px 0 0 8px"}">'
            f'<div><div class="name">{esc(d["name"])}</div><div class="sub">{sub}</div></div>{st}</div>'
            f'<div class="hp" style="border-radius:0 8px 8px 0"><b>{d["hp"]}</b><span>HP</span></div></div>')

def ability_stack(d):
    items=[]
    if d.get("atk2"): items.append(box("ult",d["atk2"]))
    items.append(box("atk",d.get("atk"))); items.append(box("blk",d.get("blk")))
    items=[x for x in items if x]; n=len(items)
    lines='<div class="brk" style="left:16px;top:-14px;bottom:14px;width:3px"></div>'
    lines+=''.join(f'<div class="brk" style="left:16px;top:{18+i*88}px;width:24px;height:3px"></div>' for i in range(n))
    return f'<div style="position:relative;padding-left:40px">{lines}<div style="display:flex;flex-direction:column;gap:9px">{"".join(items)}</div></div>'

def tpl_char(d, stars=0, fe=False):
    art_h = 600 if (d.get("atk2") or d.get("passive")) else 660
    img=(f'<img class="art" src="{d["img"]}" style="height:100%;object-position:{d.get("imgpos","50% 16%")}">'
         if d.get("img") else '<div style="height:100%;display:grid;place-items:center;background:#3a2f28;color:#8a7d5e;font-family:var(--cond);font-size:26px">ART</div>')
    passive=(f'<div class="pass"><div class="ph">PASSIVE \u2014 {esc(d["passive"]["name"])}</div><div class="pt">{esc(d["passive"]["text"])}</div></div>'
             if d.get("passive") else '')
    return (f'<div class="card" style="padding:0"><div style="position:relative;height:{art_h}px">{img}'
            f'<div style="position:absolute;left:16px;right:16px;bottom:12px">{plate_row(d,stars,fe)}</div></div>'
            f'<div style="padding:14px 20px 46px;display:flex;flex-direction:column;gap:11px">{ability_stack(d)}{passive}</div>'
            f'{footer()}</div>')

def tpl_fullart(d, stars=4):
    passive=(f'<div class="pass"><div class="ph">PASSIVE \u2014 {esc(d["passive"]["name"])}</div><div class="pt">{esc(d["passive"]["text"])}</div></div>'
             if d.get("passive") else '')
    return (f'<div class="card" style="padding:0;box-shadow:0 0 0 5px var(--gold) inset">'
            f'<img class="art" src="{d["fullart"]}" style="position:absolute;inset:0;height:100%;object-position:50% 8%">'
            f'<div style="position:absolute;left:20px;right:20px;bottom:16px;display:flex;flex-direction:column;gap:11px">'
            f'{plate_row(d,stars,True)}{ability_stack(d)}{passive}</div></div>')

def tpl_abc(d):
    cls='atk' if d["type"]=='ATTACK' else 'blk'
    ic='\u2694' if d["type"]=='ATTACK' else '\U0001F6E1'
    opts=''.join(f'<div class="opt"><span class="k">{chr(65+i)}</span><span>{esc(o)}</span></div>' for i,o in enumerate(d["opts"]))
    return (f'<div class="card abc {cls}"><div class="abchead">{ic} {d["type"]} CARD \u00b7 POWER {d["power"]}</div>'
            f'<div class="abcbody"><div class="abccharge">ANSWER CORRECTLY TO CHARGE YOUR CHARACTER.</div>'
            f'<div class="abcq">{esc(d["q"])}</div>{opts}</div>{footer()}</div>')

def tpl_item(d):
    icon=pick_icon(d.get("name"), d.get("text"), d.get("effect"))
    return (f'<div class="card"><div class="ih">\u2726 {esc(d["bkind"])}</div>'
            f'<div class="ibody"><div class="iname">{esc(d["name"])}</div><div class="itxt">{esc(d["text"])}</div>'
            f'<div class="iicon">{icon}</div></div>{footer(d.get("rarity"))}</div>')

def tpl_crit(d):
    art=f'<img src="{d["img"]}">' if d.get("img") else 'LENS ART'
    return (f'<div class="card"><div class="ch">\u2726 CRIT LENS</div>'
            f'<div class="cart">{art}</div><div class="cname">{esc(d["name"])}</div>'
            f'<div class="csec pass2"><div class="sh">PASSIVE \u2014 ACTIVE WHILE EQUIPPED</div><div class="st">{esc(d.get("passive"))}</div></div>'
            f'<div class="csec thesis"><div class="sh">THESIS \u2014 COMPLETE TO EARN THE REWARD</div><div class="st">{esc(d.get("thesis"))}</div></div>'
            f'<div class="csec reward"><div class="sh">REWARD</div><div class="st">{esc(d.get("reward"))}</div></div>'
            f'{footer(d.get("rarity"))}</div>')

def render_html(d):
    k=d["kind"]
    if k=="fe":   return tpl_fullart(d) if (d.get("fullart") and d.get("tier")=="ultra") else tpl_char(d, stars=4, fe=True)
    if k=="char": return tpl_char(d)
    if k=="abc":  return tpl_abc(d)
    if k=="bm":   return tpl_item(d)
    if k=="crit": return tpl_crit(d)
    return ""

def expand(manifest, page):
    out=[]
    for e in manifest:
        if isinstance(e, str): e=(e,)   # tolerate ("ALL_FE") / "ALL_FE" without the trailing comma
        k=e[0]
        if k=="ALL_FE":      out+=[("fe",x["id"]) for x in page.evaluate("window.ABC_EXPORT.feList()")]
        elif k=="ALL_CHARS": out+=[("char",e[1],x["id"]) for x in page.evaluate(f"window.ABC_EXPORT.chars('{e[1]}')")]
        elif k=="ALL_ABCS":  out+=[("abc",e[1],x["i"]) for x in page.evaluate(f"window.ABC_EXPORT.abcList('{e[1]}')")]
        elif k=="ALL_BMS":   out+=[("bm",x["i"]) for x in page.evaluate("window.ABC_EXPORT.bmList()")]
        elif k=="ALL_CRITS": out+=[("crit",x["i"]) for x in page.evaluate("window.ABC_EXPORT.critList()")]
        elif k=="ALL_EXP_CHARS": out+=[("expchar",e[1],x["id"]) for x in page.evaluate(f"window.ABC_EXPORT.expCharList('{e[1]}')")]
        elif k=="ALL_EXP_ABCS":  out+=[("expabc",e[1],x["i"]) for x in page.evaluate(f"window.ABC_EXPORT.expAbcList('{e[1]}')")]
        elif k=="ALL_EXP_CMDRS": out+=[("expcmdr",e[1],x["i"]) for x in page.evaluate(f"window.ABC_EXPORT.expCmdrList('{e[1]}')")]
        elif k=="ALL_EXP_BMS":   out+=[("expbm",e[1],x["i"]) for x in page.evaluate(f"window.ABC_EXPORT.expBmList('{e[1]}')")]
        else: out.append(e)
    return out

def get_data(page, e):
    k=e[0]
    if k=="fe":   return page.evaluate(f"window.ABC_EXPORT.feData('{e[1]}')"), e[1]
    if k=="char": return page.evaluate(f"window.ABC_EXPORT.charData('{e[1]}','{e[2]}')"), f"{e[1]}_{e[2]}"
    if k=="abc":  return page.evaluate(f"window.ABC_EXPORT.abcData('{e[1]}',{e[2]})"), f"abc_{e[1]}_{e[2]}"
    if k=="bm":   return page.evaluate(f"window.ABC_EXPORT.bmData({e[1]})"), f"bm_{e[1]}"
    if k=="crit": return page.evaluate(f"window.ABC_EXPORT.critData({e[1]})"), f"crit_{e[1]}"
    if k=="expchar": return page.evaluate(f"window.ABC_EXPORT.expCharData('{e[1]}','{e[2]}')"), f"exp_{e[1]}_{e[2]}"
    if k=="expabc":  return page.evaluate(f"window.ABC_EXPORT.expAbcData('{e[1]}',{e[2]})"), f"exp_{e[1]}_abc_{e[2]}"
    if k=="expcmdr": return page.evaluate(f"window.ABC_EXPORT.expCmdrData('{e[1]}',{e[2]})"), f"exp_{e[1]}_cmdr_{e[2]}"
    if k=="expbm":   return page.evaluate(f"window.ABC_EXPORT.expBmData('{e[1]}',{e[2]})"), f"exp_{e[1]}_bm_{e[2]}"
    return None,"?"

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); page=b.new_page(viewport={"width":820,"height":1130}, device_scale_factor=2)
        page.goto("file://"+os.path.abspath(GAME_FILE)); page.wait_for_timeout(1500)
        if not page.evaluate("!!(window.ABC_EXPORT && window.ABC_EXPORT.charData)"):
            sys.exit("This game build lacks the v2 export hook. Rebuild from the latest game.src.html.")
        page.add_style_tag(content=CSS)
        page.evaluate("(f)=>{ const l=document.createElement('div'); l.innerHTML=f; document.head.appendChild(l); }", FONTS)
        entries=expand(MANIFEST, page); n=0
        for e in entries:
            d,label=get_data(page, e)
            if not d: print("  skip (no data):", e); continue
            html=render_html(d)
            if not html: print("  skip (unknown kind):", e); continue
            page.evaluate("""(html)=>{ let f=document.getElementById('__pc'); if(f)f.remove();
                f=document.createElement('div'); f.id='__pc'; f.style.cssText='position:fixed;left:0;top:0;z-index:99999';
                f.innerHTML=html; document.body.appendChild(f); }""", html)
            page.wait_for_timeout(160)
            el=page.query_selector("#__pc .card")
            n+=1; path=os.path.join(OUT_DIR, f"{n:02d}_{label}.png")
            el.screenshot(path=path); print("  wrote", path)
        page.evaluate("()=>{const f=document.getElementById('__pc'); if(f)f.remove();}")
        b.close()
        print(f"\nDone. {n} card image(s) in '{OUT_DIR}/'. Next:  python3 make_card_sheet.py")

if __name__ == "__main__":
    main()
