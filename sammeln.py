"""Sammelt die neuesten Angebote aller Modelle (ganz Deutschland, ohne Filter) in daten.json.

Gefiltert wird erst im Browser - so kann jeder seine eigene Suche einstellen.
Laeuft per GitHub Actions 2x taeglich (.github/workflows/suche.yml), geht aber auch lokal: python sammeln.py
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

import scraper
from klassen import KLASSEN, MODELLE

BASIS = Path(__file__).resolve().parent
DATEN = BASIS / "daten.json"
MODELL_DATEI = BASIS / "modelle.json"
AUFBEWAHREN_TAGE = 21  # nicht mehr gesehene Anzeigen fliegen danach raus
scraper.SEITEN_AS24 = 10
scraper.SEITEN_KA = 5
FELDER = ("quelle", "titel", "preis", "preis_vorher", "km", "ez", "ez_jahr", "kraftstoff", "getriebe", "ps",
          "ort", "anbieter", "url", "bild", "bewertung", "modell", "erstmals", "zuletzt")


def main(nur=None):
    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    alt = json.loads(DATEN.read_text(encoding="utf-8")) if DATEN.exists() else {"angebote": {}}
    angebote = alt["angebote"]
    session = requests.Session()
    session.headers.update(scraper.HEADERS)
    neu, fehler = 0, []
    for mid, modell in MODELLE.items():
        if nur and mid not in nur:
            continue
        for quelle, funktion in (("AutoScout24", scraper.as24_suche), ("Kleinanzeigen", scraper.ka_suche)):
            n = 0
            try:
                for a in funktion(session, modell, {}):
                    if not scraper.passt(a, modell, {}):
                        continue
                    a.pop("_text", None)
                    n += 1
                    vorher = angebote.get(a["id"])
                    if vorher is None:
                        neu += 1
                        a.update(modell=mid, erstmals=jetzt, preis_vorher=None)
                    else:
                        a.update(modell=vorher["modell"], erstmals=vorher["erstmals"],
                                 preis_vorher=vorher["preis"] if vorher["preis"] != a["preis"] else vorher.get("preis_vorher"))
                    a["zuletzt"] = jetzt
                    angebote[a["id"]] = {k: a.get(k) for k in FELDER}
            except Exception as e:
                fehler.append(f"{quelle}/{modell['name']}: {e}")
            scraper.log(f"{modell['name']} | {quelle}: {n}")
    grenze = (datetime.now(timezone.utc) - timedelta(days=AUFBEWAHREN_TAGE)).strftime("%Y-%m-%dT%H:%MZ")
    angebote = {k: v for k, v in angebote.items() if v["zuletzt"] >= grenze}
    DATEN.write_text(json.dumps({"stand": jetzt, "neu": neu, "fehler": fehler, "angebote": angebote},
                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    MODELL_DATEI.write_text(json.dumps(
        {k: {mid: {"name": m["name"], "mobile": m["mobile"]} for mid, m in ms.items()} for k, ms in KLASSEN.items()},
        ensure_ascii=False, indent=1), encoding="utf-8")
    scraper.log(f"Fertig: {neu} neu, {len(angebote)} gesamt, {len(fehler)} Fehler")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
