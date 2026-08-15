import base64,io,json,os,re,sys
from PIL import Image
MB=1048576; APPLY='--apply' in sys.argv; Q=82
AJ='assets/assets.json'; SR='src/game.src.html'
if not(os.path.isfile(AJ) and os.path.isfile(SR)): sys.exit('run this from the repo root')
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
for k,v in assets.items():
    aid=re.sub(r'^a','',k); b=v.split(',',1)[1] if v.startswith('data:') else v
    try: raw=base64.b64decode(b+'='*(-len(b)%4))
    except Exception: out[k]=v; skip['undecodable']=skip.get('undecodable',0)+1; continue
    if aid not in used: rows[k]=('ORPHAN',len(v),0,''); continue
    if raw[:3]==b'ID3' or raw[:2] in (b'\xff\xfb',b'\xff\xf3',b'\xff\xf2'):
        out[k]=v; skip['audio']=skip.get('audio',0)+1; continue
    try:
        im=Image.open(io.BytesIO(raw)); im.load()
    except Exception: out[k]=v; skip['not an image']=skip.get('not an image',0)+1; continue
    w0,h0=im.size; cap,role=cap_for(aid)
    im2=im.convert('RGBA' if im.mode in('RGBA','LA') else 'RGB')
    if max(w0,h0)>cap: im2.thumbnail((cap,cap),Image.LANCZOS)
    bb=io.BytesIO(); im2.save(bb,'WEBP',quality=Q,method=6)
    nb=base64.b64encode(bb.getvalue()).decode()
    if len(nb)>=len(v): out[k]=v; skip['already small']=skip.get('already small',0)+1; continue
    out[k]=nb
    rows[k]=(role,len(v),len(nb),'%dx%d'%(w0,h0)+('' if im2.size==(w0,h0) else ' -> %dx%d'%im2.size))
bef=sum(len(v) for v in assets.values()); aft=sum(len(v) for v in out.values())
ch=sorted(rows.items(),key=lambda r:r[1][2]-r[1][1])
print('='*72); print('ABC SHRINK — '+('APPLY' if APPLY else 'DRY RUN, nothing written')); print('='*72)
print('assets %d  kept %d  orphans dropped %d  left alone %d'%(len(assets),len(out),len(assets)-len(out),sum(skip.values())))
print('base64 %6.2f MB -> %6.2f MB   (%.0f%% off)'%(bef/MB,aft/MB,100*(1-aft/bef)))
print('build  %6.2f MB -> %6.2f MB'%((bef+len(src))/MB,(aft+len(src))/MB))
print(); print('%-8s %-11s %-22s %9s %9s'%('id','role','pixels','KB before','KB after'))
for k,(r,b1,b2,n) in ch[:30]: print('%-8s %-11s %-22s %9.1f %9.1f'%(k,r[:11],n,b1/1024,b2/1024))
print(); print('left alone: '+', '.join('%d %s'%(n,w) for w,n in skip.items()))
if not APPLY: sys.exit('\nNothing written. Re-run with --apply when the roster looks right.')
json.dump(out,open('assets/assets.shrunk.json','w'))
chg={re.sub(r'^a','',k) for k in out if out[k]!=assets.get(k)}
ns=re.sub(r'data:image/(png|jpeg|jpg|gif);base64,(__ABCASSET_(\d+)__)',
          lambda m:('data:image/webp;base64,'+m.group(2)) if m.group(3) in chg else m.group(0),src)
open('src/game.src.shrunk.html','w',encoding='utf-8').write(ns)
cards=[]
for k,(r,b1,b2,n) in ch:
    if b2==0: continue
    ov=assets[k]; mo=ov.split(';')[0].replace('data:','') if ov.startswith('data:') else 'image/jpeg'
    cards.append('<div class=c><h3>%s <small>%s &middot; %s &middot; %.0f KB &rarr; %.0f KB</small></h3><div class=p>'
      '<figure><img src="data:%s;base64,%s"><figcaption>before</figcaption></figure>'
      '<figure><img src="data:image/webp;base64,%s"><figcaption>after</figcaption></figure></div></div>'
      %(k,r,n,b1/1024,b2/1024,mo,ov.split(',',1)[-1],out[k]))
open('shrink_preview.html','w',encoding='utf-8').write(
 '<!doctype html><meta charset=utf-8><title>ABC shrink</title><style>body{background:#143b3d;color:#FBF3DD;'
 'font:14px system-ui;padding:20px}h1{color:#E3A92B}.c{margin:24px 0;border-top:1px solid #2b5c5e;padding-top:10px}'
 'h3{margin:0 0 8px}small{color:#9fc4bd;font-weight:400}.p{display:flex;gap:18px;flex-wrap:wrap}figure{margin:0}'
 'img{max-width:420px;max-height:320px;background:#fff;display:block;border:1px solid #2b5c5e}'
 'figcaption{color:#9fc4bd;font-size:12px;padding-top:4px}</style><h1>Shrink — before / after</h1>'
 '<p>%d images changed. Look for anything that lost detail you care about.</p>%s'%(len(cards),''.join(cards)))
print('\nWROTE (originals untouched):\n  assets/assets.shrunk.json\n  src/game.src.shrunk.html\n  shrink_preview.html')
print('\n  open shrink_preview.html')
