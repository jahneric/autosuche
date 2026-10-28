"""Fahrzeugklassen und Modelle.

Jedes Modell hat:
  as24      Pfad auf AutoScout24 (/lst/<as24>)
  ka        Suchbegriff fuer Kleinanzeigen (Kategorie Autos)
  muster    Regex, die im Anzeigentitel vorkommen muss (filtert Kleinanzeigen-Muell)
  mobile    (Marken-ID, Suchtext) fuer den mobile.de-Link, None = kein Link
Neue Modelle einfach hier ergaenzen.
"""

KLASSEN = {
    "Hochdachkombi": {
        "roomster":        dict(name="Skoda Roomster",        as24="skoda/roomster",          ka="roomster",           muster=r"roomster",                 mobile=(22900, "roomster")),
        "caddy":           dict(name="VW Caddy",              as24="volkswagen/caddy",        ka="caddy",              muster=r"caddy",                    mobile=(25200, "caddy")),
        "kangoo":          dict(name="Renault Kangoo",        as24="renault/kangoo",          ka="kangoo",             muster=r"kangoo",                   mobile=(20700, "kangoo")),
        "berlingo":        dict(name="Citroën Berlingo",      as24="citroen/berlingo",        ka="berlingo",           muster=r"berlingo",                 mobile=(5900, "berlingo")),
        "partner":         dict(name="Peugeot Partner",       as24="peugeot/partner",         ka="peugeot partner",    muster=r"partner",                  mobile=(19300, "partner")),
        "rifter":          dict(name="Peugeot Rifter",        as24="peugeot/rifter",          ka="rifter",             muster=r"rifter",                   mobile=(19300, "rifter")),
        "combo":           dict(name="Opel Combo",            as24="opel/combo",              ka="opel combo",         muster=r"combo",                    mobile=(19000, "combo")),
        "tourneo_connect": dict(name="Ford Tourneo Connect",  as24="ford/tourneo-connect",    ka="tourneo connect",    muster=r"tourneo\s*connect|grand tourneo", mobile=(9000, "tourneo connect")),
        "doblo":           dict(name="Fiat Doblò",            as24="fiat/doblo",              ka="doblo",              muster=r"dobl[oò]",                 mobile=(8800, "doblo")),
        "citan":           dict(name="Mercedes Citan",        as24="mercedes-benz/citan",     ka="citan",              muster=r"citan",                    mobile=(17200, "citan")),
        "proace_city":     dict(name="Toyota Proace City",    as24="toyota/proace-city",      ka="proace city",        muster=r"proace\s*city",            mobile=(24100, "proace city")),
        "dokker":          dict(name="Dacia Dokker",          as24="dacia/dokker",            ka="dokker",             muster=r"dokker",                   mobile=None),
    },
    "VW Bus T5 / T6": {
        "t5_transporter":  dict(name="VW T5 Transporter",     as24="volkswagen/t5-transporter",  ka="t5 transporter",  muster=r"t5",                       mobile=(25200, "t5 transporter")),
        "t5_multivan":     dict(name="VW T5 Multivan",        as24="volkswagen/t5-multivan",     ka="t5 multivan",     muster=r"t5|multivan",              mobile=(25200, "t5 multivan")),
        "t6_transporter":  dict(name="VW T6 Transporter",     as24="volkswagen/t6-transporter",  ka="t6 transporter",  muster=r"t6",                       mobile=(25200, "t6 transporter")),
        "t6_multivan":     dict(name="VW T6 Multivan",        as24="volkswagen/t6-multivan",     ka="t6 multivan",     muster=r"t6|multivan",              mobile=(25200, "t6 multivan")),
        "t6_caravelle":    dict(name="VW T6 Caravelle",       as24="volkswagen/t6-caravelle",    ka="t6 caravelle",    muster=r"caravelle",                mobile=(25200, "t6 caravelle")),
        "t6_california":   dict(name="VW T6 California",      as24="volkswagen/t6-california",   ka="t6 california",   muster=r"california",               mobile=(25200, "t6 california")),
        "t61_transporter": dict(name="VW T6.1 Transporter",   as24="volkswagen/t6.1-transporter", ka="t6.1 transporter", muster=r"t6[.,]1",                mobile=(25200, "t6.1 transporter")),
        "t61_multivan":    dict(name="VW T6.1 Multivan",      as24="volkswagen/t6-1-multivan",   ka="t6.1 multivan",   muster=r"t6[.,]1|multivan",         mobile=(25200, "t6.1 multivan")),
    },
    "Transporter / Kleinbus (Alternativen zum T6)": {
        "transit_custom":  dict(name="Ford Transit Custom",   as24="ford/transit-custom",     ka="transit custom",     muster=r"transit\s*custom",         mobile=(9000, "transit custom")),
        "tourneo_custom":  dict(name="Ford Tourneo Custom",   as24="ford/tourneo-custom",     ka="tourneo custom",     muster=r"tourneo\s*custom",         mobile=(9000, "tourneo custom")),
        "vito":            dict(name="Mercedes Vito",         as24="mercedes-benz/vito",      ka="vito",               muster=r"vito",                     mobile=(17200, "vito")),
        "v_klasse":        dict(name="Mercedes V-Klasse",     as24="mercedes-benz/v-klasse",  ka="mercedes v klasse",  muster=r"v[\s-]?klasse|\bv\s?\d{3}\b|marco polo", mobile=(17200, "v-klasse")),
        "trafic":          dict(name="Renault Trafic",        as24="renault/trafic",          ka="renault trafic",     muster=r"trafic",                   mobile=(20700, "trafic")),
        "vivaro":          dict(name="Opel Vivaro",           as24="opel/vivaro",             ka="vivaro",             muster=r"vivaro",                   mobile=(19000, "vivaro")),
    },
    "Kompaktvan": {
        "touran":          dict(name="VW Touran",             as24="volkswagen/touran",       ka="touran",             muster=r"touran",                   mobile=(25200, "touran")),
    },
}

# flacher Zugriff: id -> Modell (inkl. Klasse)
MODELLE = {mid: dict(m, id=mid, klasse=k) for k, ms in KLASSEN.items() for mid, m in ms.items()}

KRAFTSTOFFE = {"": "egal", "B": "Benzin", "D": "Diesel", "E": "Elektro", "L": "Autogas (LPG)", "C": "Erdgas (CNG)", "2": "Hybrid"}
GETRIEBE = {"": "egal", "M": "Schaltgetriebe", "A": "Automatik"}
