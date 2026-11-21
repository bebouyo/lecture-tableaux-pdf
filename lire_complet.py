"""Lit des PDF ENTIERS : repère les pages « base de fournisseurs » (avis, listes, suites) puis lit leurs tableaux.

    python lire_complet.py <plan.json {titre: url}> <part> <nb_parts>

Sortie : sortie_<part>.jsonl (même format que lire.py, avec 'type' dans 'meta').
"""
import json, re, sys, time, urllib.request
from pathlib import Path

import fitz
import pdfplumber
from tables_util import tables_page

BASE = re.compile(
    r"(?i)\b(?:bases?(?:\s+\w+){0,2}?\s+de\s+donn[ée]es|bases?\s+de\s+candidats|r[ée]pertoire|fichier)\b"
    r".{0,120}?\b(?:fournisseurs?|prestataires?|consultants?|cotations?)\b"
    r"|\b(?:fournisseurs?|prestataires?)\b.{0,80}?\bbases?\s+de\s+donn[ée]es\b"
    r"|\b(?:compl[ée]ment|constitution|r[ée]vision|actualisation|mise\s+[àa]\s+jour)\b.{0,25}?\bbases?\s+de\s+donn[ée]es\b",
    re.S)
TETE = re.compile(r'(?m)^[ \t]*(?:REGION|MINISTERE|COMMUNE|DIRECTION|AGENCE|CENTRE|SOCIETE|UNIVERSITE|OFFICE|CAISSE|FONDS|INSTITUT|ECOLE|LYCEE|HOPITAL|PRESIDENCE|PREMIER MINISTERE|ASSEMBLEE|CONSEIL|AUTORITE|LABORATOIRE|PROJET|PROGRAMME|LOTERIE|CHAMBRE|MAISON|BUREAU|RADIODIFFUSION|COUR|HAUTE)\b[^\n]{8,}$')
LIGNE = re.compile(r'(?m)^[ \t]*\d{1,4}[ \t]+[A-Z][A-Z]')


def corps(t):
    m = re.search(r'www\.finances\.gov\.bf', (t or '')[:400])
    return t[m.end():] if m else (t or '')


def est_liste(t):
    c = corps(t)
    return len(re.findall(r'RCCM|IFU', c)) >= 3 or len(LIGNE.findall(c)) >= 8


def suite_de_liste(t):
    return not TETE.search(corps(t)[:700]) and est_liste(t)


plan = json.load(open(sys.argv[1], encoding='utf-8'))
part, nb = int(sys.argv[2]), int(sys.argv[3])
titres = [t for i, t in enumerate(plan) if i % nb == part]
sortie = Path('sortie_%d.jsonl' % part)
pdf_path = Path('q.pdf')
t0 = time.time()
for i, titre in enumerate(titres, 1):
    rec = {'titre': titre, 'url': plan[titre], 'pages': {}, 'erreur': None}
    try:
        for essai in range(4):
            try:
                data = urllib.request.urlopen(urllib.request.Request(plan[titre], headers={'User-Agent': 'Mozilla/5.0'}),
                                              timeout=240).read()
                if data[:5] != b'%PDF-':
                    raise ValueError('pas un PDF')
                pdf_path.write_bytes(data); break
            except Exception:  # noqa: BLE001
                if essai == 3:
                    raise
                time.sleep(15 * (essai + 1))
        doc = fitz.open(pdf_path); txt = [pg.get_text() for pg in doc]; doc.close()
        garder = {}
        for n, t in enumerate(txt, 1):
            if BASE.search(' '.join(t.split())):
                garder[n] = 'liste' if est_liste(t) else 'avis'
        for n in sorted(list(garder)):
            q = n + 1
            while q <= len(txt) and q not in garder and suite_de_liste(txt[q - 1]):
                garder[q] = 'suite'; q += 1
        with pdfplumber.open(pdf_path) as pdf:
            for n in sorted(garder):
                page = pdf.pages[n - 1]
                rec['pages'][str(n)] = {'meta': {'type': garder[n]}, 'texte': page.extract_text() or '',
                                        'tables': tables_page(page), 'images': len(page.images)}
                page.flush_cache()
    except Exception as e:  # noqa: BLE001
        rec['erreur'] = repr(e)[:300]
    finally:
        if pdf_path.exists():
            pdf_path.unlink()
    with open(sortie, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('%d/%d %s : %d pages gardées%s | %.0f min' % (i, len(titres), titre, len(rec['pages']),
                                                        ' ERREUR ' + rec['erreur'][:80] if rec['erreur'] else '',
                                                        (time.time() - t0) / 60), flush=True)
