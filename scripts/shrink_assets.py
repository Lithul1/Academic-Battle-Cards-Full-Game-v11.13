import base64,io,json,os,re,sys
from PIL import Image
MB=1048576; APPLY='--apply' in sys.argv; Q=82; KEEP_FROM=1034
AJ='assets/assets.json'; SR='src/game.src.html'
if not(os.path.isfile(AJ) and os.path.isfile(SR)): sys.exit('run from the repo root')
src=open(SR,encoding='utf-8').read(); assets=json.load(open(AJ))
used=set(re.findall(r'__ABCASSET_(\d+)__',src))
CAPS=[('--deckbg',512),('--arena',1200),('ABC_FULLART',900),('"box"',700),('CRIT_IMG',600),('PACK_ART',480)]
def cap_for(aid):
    i=src.find('__ABCASSET_%s__'%aid)
    if i<0: return 600,'card art'
    best,bc,bk=-1,600,'card art'
    for k,c in CAPS:
        j=src.rfind(k,max(0,i-400),i)
        if j>best: best,bc,bk=j,c,k
    return bc,bk
rows={};out={};skip={}
def note(w): skip[w]=skip.get(w,0)+1
for k,v in assets.items():
    aid=re.sub(r'^a','',k); b=v.split(',',1)[1] if v.startswith('data:') else v
    if aid.isdigit() and int(aid)>=KEEP_FROM:
        out[k]=v; note('new art, already optimal'); continue
    try: raw=base64.b64decode(b+'='*(-len(b)%4))
    except Exception: out[k]=v; note('undecodable'); continue
    if aid not in used: rows[k]=('ORPHAN',len(v),0,''); continue
    if raw[:3]==b'ID3' or raw[:2] in (b'\xff\xfb',b'\xff\xf3',b'\xff\xf2'):
        out[k]=v; note('audio'); continue
    try:
        im=Image.open(io.BytesIO(raw)); im.load()
    except Exception: out[k]=v; note('not an image'); continue
    w0,h0=im.size; cap,role=cap_for(aid)
    im2=im.convert('RGBA' if im.mode in('RGBA','LA') else 'RGB')
    if max(w0,h0)>cap: im2.thumbnail((cap,cap),Image.LANCZOS)
    bb=io.BytesIO(); im2.save(bb,'WEBP',quality=Q,method=6)
    nb=base64.b64encode(bb.getvalue()).decode()
    if len(nb)>=len(v): out[k]=v; note('already small'); continue
    out[k]=nb
    rows[k]=(role,len(v),len(nb),'%dx%d'%(w0,h0)+('' if im2.size==(w0,h0) else ' -> %dx%d'%im2.size))
bef=sum(len(v) for v in assets.values()); aft=sum(len(v) for v in out.values())
ch=sorted(rows.items(),key=lambda r:r[1][2]-r[1][1])
print('='*72); print('ABC SHRINK  '+('APPLY' if APPLY else 'DRY RUN, nothing written')); print('='*72)
print('assets %d  kept %d  orphans dropped %d'%(len(assets),len(out),len(assets)-len(out)))
print('base64 %6.2f MB -> %6.2f MB   (%.0f%% off)'%(bef/MB,aft/MB,100*(1-aft/bef)))
print('build  %6.2f MB -> %6.2f MB'%((bef+len(src))/MB,(aft+len(src))/MB))
print(); print('%-8s %-11s %-22s %9s %9s'%('id','role','pixels','KB before','KB after'))
for k,(r,b1,b2,n) in ch[:20]: print('%-8s %-11s %-22s %9.1f %9.1f'%(k,r[:11],n,b1/1024,b2/1024))
print(); print('left alone: '+', '.join('%d %s'%(n,w) for w,n in skip.items()))
if not APPLY: sys.exit('\nNothing written. Re-run with --apply when this looks right.')
json.dump(out,open('assets/assets.shrunk.json','w'))
chg={re.sub(r'^a','',k) for k in out if out[k]!=assets.get(k)}
ns=re.sub(r'data:image/(png|jpeg|jpg|gif);base64,(__ABCASSET_(\d+)__)',
          lambda m:('data:image/webp;base64,'+m.group(2)) if m.group(3) in chg else m.group(0),src)
open('src/game.src.shrunk.html','w',encoding='utf-8').write(ns)
print('\nWROTE assets/assets.shrunk.json and src/game.src.shrunk.html')
