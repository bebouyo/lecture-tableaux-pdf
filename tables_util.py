"""Lecture des tableaux d'une page avec pdfplumber + récupération des lignes « orphelines » : une ligne en haut
(ou en bas) de page dont le trait n'est pas relié au tableau est vue par pdfplumber comme hors tableau.
On la reconstruit en rangeant ses mots dans les colonnes du tableau."""


def _colonnes(t):
    xs = sorted({round(c[0], 1) for c in t.cells} | {round(c[2], 1) for c in t.cells})
    bornes = []
    for x in xs:
        if not bornes or x - bornes[-1] > 3:
            bornes.append(x)
    return bornes


def _ligne_depuis_mots(mots, bornes):
    n = len(bornes) - 1
    cases = [[] for _ in range(n)]
    for w in sorted(mots, key=lambda w: (round(w['top']), w['x0'])):
        cx = (w['x0'] + w['x1']) / 2
        for i in range(n):
            if bornes[i] - 1 <= cx < bornes[i + 1] + 1:
                cases[i].append(w['text']); break
    return [' '.join(c) for c in cases]


def tables_page(page):
    """Liste de tableaux ; chaque tableau = liste de lignes (listes de chaînes). Une ligne récupérée hors tableau
    est précédée du marqueur '§' dans sa première case vide de marqueur (pour le contrôle)."""
    res = []
    try:
        tabs = page.find_tables()
    except Exception:  # noqa: BLE001
        return res
    mots = None
    traits = sorted({round(e['top'], 1) for e in page.edges if e['orientation'] == 'h'})
    for t in tabs:
        lignes = [[(c or '').replace('\n', ' ').strip() for c in r] for r in t.extract()]
        x0, top, x1, bot = t.bbox
        bornes = _colonnes(t)
        if len(bornes) >= 3:
            if mots is None:
                mots = page.extract_words()
            dans_x = [w for w in mots if w['x0'] >= x0 - 2 and w['x1'] <= x1 + 2]
            # au-dessus : entre le trait horizontal le plus proche au-dessus (>= 6 pt) et le haut du tableau
            haut = [y for y in traits if y < top - 6]
            if haut:
                y0 = haut[-1]
                orph = [w for w in dans_x if w['top'] >= y0 - 0.5 and w['bottom'] <= top + 1]
                if orph:
                    l = _ligne_depuis_mots(orph, bornes)
                    if sum(1 for c in l if c) >= 2:
                        lignes.insert(0, ['§' + l[0]] + l[1:])
            # en dessous : entre le bas du tableau et le trait suivant
            bas = [y for y in traits if y > bot + 6]
            if bas:
                y1 = bas[0]
                orph = [w for w in dans_x if w['top'] >= bot - 1 and w['bottom'] <= y1 + 0.5]
                if orph:
                    l = _ligne_depuis_mots(orph, bornes)
                    if sum(1 for c in l if c) >= 2:
                        lignes.append(['§' + l[0]] + l[1:])
        res.append(lignes)
    return res
