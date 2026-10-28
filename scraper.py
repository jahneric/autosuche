"""Durchsucht AutoScout24 und Kleinanzeigen nach allen aktiven Suchen aus config.json.

Aufruf:  python scraper.py          (wird vom Zeitplan 2x taeglich gestartet)
"""
import json
import random
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup

from klassen import MODELLE

BASIS = Path(__file__).resolve().parent
CONFIG = BASIS / "config.json"
DB = BASIS / "angebote.db"
LOG = BASIS / "suche.log"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9",
}
SEITEN_AS24 = 5  # 20 Anzeigen pro Seite, neueste zuerst
SEITEN_KA = 4    # ~25 Anzeigen pro Seite, neueste zuerst
MUELL = re.compile(r"ankauf|kaufe|suche|motorschaden|getriebeschaden|export|bastler|defekt|unfall", re.I)
KRAFTSTOFF_TEXT = {"B": r"benzin", "D": r"diesel", "E": r"elektro", "L": r"autogas|lpg", "C": r"erdgas|cng", "2": r"hybrid"}

STANDARD_CONFIG = {
    "suchen": [
        {
            "id": "familienkiste",
            "name": "Hochdachkombi bis 12.000 €",
            "aktiv": True,
            "modelle": ["roomster", "caddy", "kangoo", "berlingo"],
            "preis_min": 2000, "preis_max": 12000,
            "km_max": 180000, "ez_min": 2010, "ps_min": 0,
            "kraftstoff": "", "getriebe": "",
            "plz": "", "umkreis": 0, "nur_privat": False,
            "schrott_ausblenden": True,
        }
    ],
    "benachrichtigung": {"windows": True, "email_an": "", "smtp_user": "", "smtp_passwort": "", "smtp_server": "smtp.gmail.com"},
    "zeiten": ["08:00", "18:00"],
}


def log(msg):
    zeile = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(zeile)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(zeile + "\n")


def lade_config():
    if not CONFIG.exists():
        speichere_config(STANDARD_CONFIG)
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def speichere_config(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS angebote (
        id TEXT PRIMARY KEY, quelle TEXT, suche TEXT, modell TEXT, titel TEXT,
        preis INTEGER, preis_vorher INTEGER, km INTEGER, ez TEXT, ez_jahr INTEGER,
        kraftstoff TEXT, getriebe TEXT, ps INTEGER, ort TEXT, anbieter TEXT,
        url TEXT, bild TEXT, bewertung TEXT,
        erstmals TEXT, zuletzt TEXT, status TEXT DEFAULT 'neu')""")
    con.execute("CREATE TABLE IF NOT EXISTS laeufe (zeit TEXT, neu INTEGER, gesamt INTEGER, fehler TEXT)")
    return con


def zahl(text):
    ziffern = re.sub(r"[^\d]", "", text or "")
    return int(ziffern) if ziffern else None


def hole(session, url):
    time.sleep(random.uniform(1.5, 3.5))  # hoeflich bleiben
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.text


# ---------------------------------------------------------------- AutoScout24

def as24_url(modell, s, seite):
    q = {"atype": "C", "cy": "D", "sort": "age", "desc": 1, "page": seite, "ustate": "N,U"}
    if s.get("preis_min"): q["pricefrom"] = s["preis_min"]
    if s.get("preis_max"): q["priceto"] = s["preis_max"]
    if s.get("km_max"): q["kmto"] = s["km_max"]
    if s.get("ez_min"): q["fregfrom"] = s["ez_min"]
    if s.get("kraftstoff"): q["fuel"] = s["kraftstoff"]
    if s.get("getriebe"): q["gear"] = s["getriebe"]
    if s.get("ps_min"): q.update(powerfrom=round(s["ps_min"] * 0.7355), powertype="kw")
    if s.get("nur_privat"): q["custtype"] = "P"
    if s.get("plz") and s.get("umkreis"): q.update(zip=s["plz"], zipr=s["umkreis"])
    return f"https://www.autoscout24.de/lst/{modell['as24']}?{urlencode(q)}"


def as24_suche(session, modell, s):
    for seite in range(1, SEITEN_AS24 + 1):
        html = hole(session, as24_url(modell, s, seite))
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            raise RuntimeError("AutoScout24: Seitenformat unbekannt")
        pp = json.loads(m.group(1))["props"]["pageProps"]
        listings = pp.get("listings") or []
        for l in listings:
            v, tr = l.get("vehicle", {}), l.get("tracking", {})
            details = {d.get("ariaLabel"): d.get("data") for d in l.get("vehicleDetails", [])}
            ez = tr.get("firstRegistration") or ""  # "11-2009"
            ps = re.search(r"\((\d+)\s*PS\)", details.get("Leistung") or "")
            loc = l.get("location", {})
            titel = " ".join(x for x in [v.get("make"), v.get("model"), v.get("modelVersionInput")] if x)
            yield dict(
                id="as24:" + l["id"], quelle="AutoScout24", titel=titel,
                preis=l.get("price", {}).get("priceRaw"), km=zahl(tr.get("mileage")),
                ez=ez.replace("-", "/"), ez_jahr=zahl(ez[-4:]),
                kraftstoff=details.get("Kraftstoff") or "", getriebe=details.get("Getriebe") or "",
                ps=int(ps.group(1)) if ps else None,
                ort=f"{loc.get('zip', '')} {loc.get('city', '')}".strip(),
                anbieter="Händler" if l.get("seller", {}).get("type") == "Dealer" else "Privat",
                url="https://www.autoscout24.de" + l.get("url", ""),
                bild=(l.get("images") or [""])[0],
                bewertung={"top-price": "Top-Preis", "good-price": "Guter Preis", "fair-price": "Fairer Preis",
                           "increased-price": "Erhöht", "high-price": "Hoch"}.get(tr.get("priceLabel"), ""),
            )
        if seite >= (pp.get("numberOfPages") or 1) or not listings:
            break


# ---------------------------------------------------------------- Kleinanzeigen

_ka_orte = {}


def ka_ort(session, plz):
    if plz not in _ka_orte:
        r = session.get("https://www.kleinanzeigen.de/s-ort-empfehlungen.json", params={"query": plz}, timeout=30)
        ids = [k.lstrip("_") for k in r.json() if k != "_0"]
        _ka_orte[plz] = ids[0] if ids else None
    return _ka_orte[plz]


def ka_url(session, modell, s, seite):
    teile = ["s-autos"]
    if s.get("nur_privat"): teile.append("anbieter:privat")
    teile += ["anzeige:angebote", "sortierung:neueste"]
    if seite > 1: teile.append(f"seite:{seite}")
    if s.get("preis_min") or s.get("preis_max"):
        teile.append(f"preis:{s.get('preis_min') or ''}:{s.get('preis_max') or ''}")
    ort = ka_ort(session, s["plz"]) if s.get("plz") and s.get("umkreis") else None
    if ort:
        teile.append(s["plz"])
    teile.append(quote(modell["ka"].replace(" ", "-")))
    teile.append("k0c216" + (f"l{ort}r{s['umkreis']}" if ort else ""))
    return "https://www.kleinanzeigen.de/" + "/".join(teile)


def ka_suche(session, modell, s):
    for seite in range(1, SEITEN_KA + 1):
        soup = BeautifulSoup(hole(session, ka_url(session, modell, s, seite)), "html.parser")
        artikel = soup.select("article[data-adid]")
        for a in artikel:
            texte = list(a.stripped_strings)
            titel_el = a.select_one("h2, h3") or a.select_one("a[href*='/s-anzeige/']")
            titel = titel_el.get_text(" ", strip=True) if titel_el and titel_el.get_text(strip=True) else ""
            if not titel:
                info = a.select_one("script[type='application/ld+json']")
                titel = json.loads(info.string).get("title", "") if info else ""
            preis = next((t for t in texte if "€" in t), "")
            km = next((t for t in texte if re.fullmatch(r"[\d.]+ km", t)), "")
            ez = next((t for t in texte if t.startswith("EZ ")), "")
            ort = next((t for t in texte if re.match(r"^\d{5} ", t)), "")
            beschreibung = " ".join(texte)
            fuel = re.search(r"\b(Benzin|Diesel|Elektro|Hybrid|Autogas|LPG|Erdgas|CNG)\b", beschreibung, re.I)
            gear = re.search(r"\b(Automatik|Schaltgetriebe|Manuell|DSG)\b", beschreibung, re.I)
            img = a.select_one("img")
            yield dict(
                id="ka:" + a["data-adid"], quelle="Kleinanzeigen", titel=titel,
                preis=zahl(preis.split("€")[0]), km=zahl(km), ez=ez[3:], ez_jahr=zahl(ez[-4:]) if ez else None,
                kraftstoff=fuel.group(1).capitalize() if fuel else "",
                getriebe=("Automatik" if gear and gear.group(1).lower() in ("automatik", "dsg") else "Schaltgetriebe") if gear else "",
                ps=None, ort=ort, anbieter="Privat" if s.get("nur_privat") else "",
                url="https://www.kleinanzeigen.de" + a.get("data-href", ""),
                bild=img.get("src", "") if img else "", bewertung="",
                _text=beschreibung,
            )
        if len(artikel) < 20:
            break


# ---------------------------------------------------------------- Filter & Speichern

def passt(a, modell, s):
    """Lokaler Filter - Kleinanzeigen kann serverseitig nur den Preis filtern."""
    if a["preis"] is None:
        return False
    if s.get("preis_min") and a["preis"] < s["preis_min"]: return False
    if s.get("preis_max") and a["preis"] > s["preis_max"]: return False
    if s.get("km_max") and a["km"] and a["km"] > s["km_max"]: return False
    if s.get("ez_min") and a["ez_jahr"] and a["ez_jahr"] < s["ez_min"]: return False
    if s.get("ps_min") and a["ps"] and a["ps"] < s["ps_min"]: return False
    if s.get("kraftstoff") and a["kraftstoff"] and not re.search(KRAFTSTOFF_TEXT[s["kraftstoff"]], a["kraftstoff"], re.I): return False
    if s.get("getriebe") and a["getriebe"] and (s["getriebe"] == "A") != (a["getriebe"] == "Automatik"): return False
    if s.get("kasten_ausblenden") and re.search(r"kasten|\bnfz\b|\blkw\b|pritsche|koffer", a["titel"], re.I): return False
    if a["quelle"] == "Kleinanzeigen":
        if not re.search(modell["muster"], a["titel"], re.I): return False
        if s.get("schrott_ausblenden", True) and MUELL.search(a["titel"]): return False
    return True


def speichere(con, a, suche, modell, jetzt):
    a.pop("_text", None)
    alt = con.execute("SELECT preis, status FROM angebote WHERE id=?", (a["id"],)).fetchone()
    if alt is None:
        con.execute(
            """INSERT INTO angebote (id, quelle, suche, modell, titel, preis, km, ez, ez_jahr, kraftstoff, getriebe,
               ps, ort, anbieter, url, bild, bewertung, erstmals, zuletzt, status)
               VALUES (:id,:quelle,:suche,:modell,:titel,:preis,:km,:ez,:ez_jahr,:kraftstoff,:getriebe,
               :ps,:ort,:anbieter,:url,:bild,:bewertung,:jetzt,:jetzt,'neu')""",
            dict(a, suche=suche, modell=modell, jetzt=jetzt))
        return True
    vorher = alt["preis"] if a["preis"] != alt["preis"] else None
    con.execute(
        """UPDATE angebote SET preis=?, preis_vorher=COALESCE(?, preis_vorher), km=?, zuletzt=?, bild=?, bewertung=?
           WHERE id=?""", (a["preis"], vorher, a["km"], jetzt, a["bild"], a["bewertung"], a["id"]))
    return False


def benachrichtigen(cfg, neue):
    if not neue:
        return
    b = cfg.get("benachrichtigung", {})
    text = f"{len(neue)} neue Angebote: " + ", ".join(f"{a['titel'][:30]} {a['preis']}€" for a in neue[:3])
    if b.get("windows", True):
        try:
            import subprocess
            ps = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$x = $t.GetElementsByTagName('text'); $x.Item(0).AppendChild($t.CreateTextNode('Autosuche')) | Out-Null
$x.Item(1).AppendChild($t.CreateTextNode({json.dumps(text)})) | Out-Null
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Autosuche').Show([Windows.UI.Notifications.ToastNotification]::new($t))
"""
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as e:
            log(f"Windows-Benachrichtigung fehlgeschlagen: {e}")
    if b.get("email_an") and b.get("smtp_user") and b.get("smtp_passwort"):
        try:
            import smtplib
            from email.mime.text import MIMEText
            zeilen = "".join(
                f"<p><a href='{a['url']}'><b>{a['titel']}</b></a><br>{a['preis']:,} € · {a['km'] or '?'} km · EZ {a['ez']} · {a['ort']} · {a['quelle']}</p>".replace(",", ".")
                for a in neue)
            msg = MIMEText(f"<h2>{len(neue)} neue Angebote</h2>{zeilen}", "html", "utf-8")
            msg["Subject"], msg["From"], msg["To"] = f"Autosuche: {len(neue)} neue Angebote", b["smtp_user"], b["email_an"]
            with smtplib.SMTP_SSL(b.get("smtp_server", "smtp.gmail.com"), 465, timeout=30) as smtp:
                smtp.login(b["smtp_user"], b["smtp_passwort"])
                smtp.send_message(msg)
        except Exception as e:
            log(f"E-Mail fehlgeschlagen: {e}")


def lauf(nur_suche=None):
    cfg = lade_config()
    con = db()
    session = requests.Session()
    session.headers.update(HEADERS)
    jetzt = datetime.now().strftime("%Y-%m-%d %H:%M")
    neue, gesamt, fehler = [], 0, []
    for s in cfg["suchen"]:
        if not s.get("aktiv", True) or (nur_suche and s["id"] != nur_suche):
            continue
        for mid in s["modelle"]:
            modell = MODELLE.get(mid)
            if not modell:
                continue
            for quelle, funktion in (("AutoScout24", as24_suche), ("Kleinanzeigen", ka_suche)):
                n = 0
                try:
                    for a in funktion(session, modell, s):
                        if passt(a, modell, s):
                            gesamt += 1; n += 1
                            if speichere(con, a, s["id"], modell["name"], jetzt):
                                neue.append(a)
                except Exception as e:
                    fehler.append(f"{quelle}/{modell['name']}: {e}")
                    log(f"FEHLER {quelle} {modell['name']}: {e}")
                log(f"{s['name']} | {modell['name']} | {quelle}: {n} passende")
                con.commit()
    con.execute("INSERT INTO laeufe VALUES (?,?,?,?)", (jetzt, len(neue), gesamt, "; ".join(fehler)))
    con.commit()
    log(f"Fertig: {len(neue)} neu, {gesamt} passende insgesamt, {len(fehler)} Fehler")
    benachrichtigen(cfg, neue)
    return len(neue), gesamt, fehler


if __name__ == "__main__":
    lauf(sys.argv[1] if len(sys.argv) > 1 else None)
