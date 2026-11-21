"""Lit les tableaux de pages choisies dans des PDF publics, avec pdfplumber.

    python lire.py <plan.json> <part> <nb_parts> [limite]

Chaque part lit un quotidien sur nb_parts. Sortie : sortie_<part>.jsonl
"""
import json, sys, time, urllib.request
from pathlib import Path

import pdfplumber
from tables_util import tables_page

plan_f, part, nb = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
limite = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] not in ('', '0') else None
plan = json.load(open(plan_f, encoding='utf-8'))
titres = [t for i, t in enumerate(plan) if i % nb == part]
if limite:
    titres = titres[:limite]
sortie = Path('sortie_%d.jsonl' % part)
pdf_path = Path('q.pdf')


def telecharger(url):
    err = None
    for essai in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=240).read()
            if data[:5] != b'%PDF-':
                raise ValueError('pas un PDF')
            pdf_path.write_bytes(data)
            return len(data)
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(15 * (essai + 1))
    raise err


t0 = time.time()
for i, titre in enumerate(titres, 1):
    info = plan[titre]
    rec = {'titre': titre, 'url': info['url'], 'pages': {}, 'erreur': None}
    try:
        telecharger(info['url'])
        with pdfplumber.open(pdf_path) as pdf:
            for p, meta in info['pages'].items():
                n = int(p)
                if n > len(pdf.pages):
                    rec['pages'][p] = {'meta': meta, 'erreur': 'page absente du PDF'}
                    continue
                page = pdf.pages[n - 1]
                rec['pages'][p] = {'meta': meta, 'tables': tables_page(page), 'texte': page.extract_text() or '',
                                   'images': len(page.images)}
                page.flush_cache()
    except Exception as e:  # noqa: BLE001
        rec['erreur'] = repr(e)[:300]
    finally:
        if pdf_path.exists():
            pdf_path.unlink()
    with open(sortie, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('%d/%d %s : %d pages%s | %.0f min' % (i, len(titres), titre[:40], len(info['pages']),
                                                ' ERREUR ' + rec['erreur'][:80] if rec['erreur'] else '',
                                                (time.time() - t0) / 60), flush=True)
