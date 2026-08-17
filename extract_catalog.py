#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull deck data out of Academic_Battle_Cards_Catalog.xlsx into TSVs for sync_decks.py.

    python3 extract_catalog.py Academic_Battle_Cards_Catalog.xlsx romeojuliet odyssey

Reads the workbook with the standard library only (no openpyxl needed) and writes
sync/characters.tsv, sync/firsteds.tsv, sync/trivia.tsv.

Two things Excel does to this data that have to be undone on the way out:
  * integers come back as floats  -> "1.0" becomes "1"
  * a label like 10/2 is silently stored as a DATE -> restored to "10/2"
Both are reported, so a silent corruption never passes through unnoticed.
"""
import sys, os, re, io, zipfile, datetime
import xml.etree.ElementTree as ET

NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
EPOCH=datetime.datetime(1899,12,30)

def col(ref):
    m=re.match(r'([A-Z]+)',ref or '');  n=0
    for ch in (m.group(1) if m else ''): n=n*26+(ord(ch)-64)
    return n-1

def sheets(z):
    wb=ET.fromstring(z.read('xl/workbook.xml'))
    rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    tgt={r.get('Id'):r.get('Target') for r in rels}
    out={}
    for sh in wb.iter(NS+'sheet'):
        t=tgt.get(sh.get(REL+'id'),'')
        t=t[1:] if t.startswith('/xl/') else (t if t.startswith('xl/') else 'xl/'+t.lstrip('/'))
        out[sh.get('name')]=t
    return out

def date_styles(z):
    """style indices whose number format is a date"""
    try: st=ET.fromstring(z.read('xl/styles.xml'))
    except KeyError: return set()
    custom={f.get('numFmtId'):(f.get('formatCode') or '') for f in st.iter(NS+'numFmt')}
    builtin=set(str(i) for i in list(range(14,23))+list(range(45,48)))
    out=set()
    xfs=st.find(NS+'cellXfs')
    if xfs is None: return out
    for i,xf in enumerate(xfs.findall(NS+'xf')):
        nid=xf.get('numFmtId')
        code=custom.get(nid,'')
        if nid in builtin or re.search(r'[dmy]', code, re.I) and not re.search(r'[#0]', code):
            out.add(str(i))
    return out

def grid(z, path, shared, dstyles, warn):
    rows=[]
    for row in ET.fromstring(z.read(path)).iter(NS+'row'):
        cells={}
        for c in row.iter(NS+'c'):
            i=col(c.get('r')); t=c.get('t'); s=c.get('s')
            if t=='inlineStr': v=''.join(x.text or '' for x in c.iter(NS+'t'))
            else:
                ve=c.find(NS+'v'); v=ve.text if ve is not None and ve.text is not None else ''
                if t=='s' and v.isdigit(): v=shared[int(v)]
                elif v and s in dstyles:
                    try: v=('DATE:'+ (EPOCH+datetime.timedelta(days=float(v))).strftime('%Y-%m-%d'))
                    except Exception: pass
                elif v and re.fullmatch(r'-?\d+\.0+', v): v=v.split('.')[0]
            cells[i]=(v or '').strip()
        rows.append([cells.get(i,'') for i in range(max(cells)+1)] if cells else [])
    return rows

def table(rows, warn, sheet):
    hdr=[c.strip() for c in rows[0]]
    while hdr and not hdr[-1]: hdr.pop()      # trailing blank header columns
    n=len(hdr); out=[]
    for r in rows[1:]:
        if not any(x.strip() for x in r): continue
        r=list(r)+['']*(n-len(r))
        d={hdr[i]:r[i] for i in range(n) if hdr[i]}
        rid=d.get('id') or d.get('question','')[:30]
        for k,v in list(d.items()):
            if v.startswith('DATE:'):
                iso=v[5:]
                if k.endswith('_label'):
                    y,m,dd=iso.split('-'); fixed='%d/%d'%(int(m),int(dd))
                    warn.append('%s: %s %s was stored as a date by Excel -> restored "%s"'%(sheet,rid,k,fixed))
                    d[k]=fixed
                else:
                    warn.append('%s: %s %s is a date and probably should not be (%s)'%(sheet,rid,k,iso))
                    d[k]=iso
        out.append(d)
    return hdr,out

def main():
    if len(sys.argv)<3: sys.exit(__doc__)
    xlsx=sys.argv[1]; decks=set(sys.argv[2:])
    if not os.path.exists(xlsx): sys.exit("no such workbook: "+xlsx)
    warn=[]
    with zipfile.ZipFile(xlsx) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(NS+'si'):
                shared.append(''.join(t.text or '' for t in si.iter(NS+'t')))
        sh=sheets(z); ds=date_styles(z)
        want={'Characters':'characters','1st Editions':'firsteds','Trivia_ABC':'trivia'}
        os.makedirs('sync',exist_ok=True)
        for name,out in want.items():
            if name not in sh: sys.exit("workbook has no sheet %r (has: %s)"%(name,', '.join(sh)))
            hdr,rows=table(grid(z,sh[name],shared,ds,warn),warn,name)
            rows=[r for r in rows if r.get('deck') in decks]
            with io.open('sync/%s.tsv'%out,'w',encoding='utf-8') as f:
                f.write('\t'.join(hdr)+'\n')
                for d in rows:
                    f.write('\t'.join(d.get(k,'').replace('\t',' ').replace('\n',' ') for k in hdr)+'\n')
            print("  sync/%-14s %4d rows" % (out+'.tsv', len(rows)))
    if warn:
        print("\nExcel damage found and repaired:")
        for x in warn: print("   "+x)
        print("   ^ fix the cell format in the workbook so this stops recurring")
    else:
        print("\nno Excel coercion detected")

if __name__=='__main__': main()
