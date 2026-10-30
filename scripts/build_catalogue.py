import json
from pathlib import Path

ROWS = [
    ("T01", "Kapadokya", "İstanbul", 5200, 2, True, True, False, 600, 350),
    ("T02", "Kapadokya", "İstanbul", 6900, 2, False, True, True, 0, 1200),
    ("T03", "Kapadokya", "İstanbul", 4500, 1, True, None, False, None, None),
    ("T04", "Kapadokya", "İstanbul", 7600, 3, False, False, None, 400, 0),
    ("T05", "Karadeniz", "Ankara", 8400, 3, True, True, False, 700, 500),
    ("T06", "Karadeniz", "Ankara", 10500, 4, False, True, True, 0, 650),
    ("T07", "Karadeniz", "Ankara", 7200, 2, None, True, False, 300, None),
    ("T08", "Karadeniz", "Ankara", 9600, 3, False, None, True, None, 800),
    ("T09", "Pamukkale", "İstanbul", 3900, 1, True, True, False, 500, 0),
    ("T10", "Pamukkale", "İstanbul", 5100, 2, False, True, True, 0, 0),
    ("T11", "Pamukkale", "İstanbul", 4700, 2, False, False, None, 200, 400),
    ("T12", "Pamukkale", "İstanbul", 3600, 1, None, None, False, None, None),
    ("T13", "Ege", "İzmir", 5800, 2, False, True, False, 350, 700),
    ("T14", "Ege", "İzmir", 6900, 3, False, True, True, 0, 900),
    ("T15", "Ege", "İzmir", 4300, 1, True, False, False, None, 500),
    ("T16", "Ege", "İzmir", 7500, 3, None, True, None, 250, 0),
    ("T17", "Safranbolu", "Ankara", 2400, 1, False, True, False, 100, 0),
    ("T18", "Safranbolu", "Ankara", 3200, 2, False, True, True, 0, 300),
    ("T19", "Safranbolu", "Ankara", 2100, 1, True, None, False, 250, None),
    ("T20", "Safranbolu", "Ankara", 2900, 2, None, False, None, None, 150),
]


def build():
    tours = []
    for row in ROWS:
        code, destination, departure, price, nights, bus, breakfast, museums, mandatory, optional = row
        fact_rows = [
            ("price", price, f"Kişi başı taban ücret {price} TL'dir."),
            ("nights", nights, f"Programda otelde {nights} gece konaklama vardır."),
            ("overnight_bus", bus, "Program gece otobüs yolculuğu içerir." if bus else "Program gece otobüs yolculuğu içermez."),
            ("breakfast", breakfast, "Kahvaltı taban ücrete dahildir." if breakfast else "Kahvaltı taban ücrete dahil değildir."),
            ("museums", museums, "Müze girişleri taban ücrete dahildir." if museums else "Müze girişleri taban ücrete dahil değildir."),
            ("mandatory_fee", mandatory, f"Taban ücrete ek zorunlu ücret kişi başı {mandatory} TL'dir." if mandatory else "Taban ücrete ek zorunlu ücret yoktur."),
            ("optional_fee", optional, f"İsteğe bağlı gezi paketi kişi başı {optional} TL'dir." if optional else "Programda ücretli isteğe bağlı gezi paketi yoktur."),
        ]
        facts = {key: {"value": value, "evidence": text if value is not None else ""} for key, value, text in fact_rows}
        sentences = [f"{departure} çıkışlı {destination} örnek turu."]
        sentences += [f["evidence"] for f in facts.values() if f["evidence"]]
        sentences.append("Tarih, müsaitlik, otel adı ve kişisel harcamalar bu örnekte tanımlanmamıştır.")
        tours.append({"id": code, "name": f"{destination} Örnek Tur {code}", "destination": destination,
                      "departure": departure, "description": " ".join(sentences), "facts": facts})
    return {"kind": "synthetic", "version": "1.0", "created": "2026-10-21",
            "licence": "CC0-1.0",
            "currency": "TRY", "price_basis": "per_person", "tours": tours}


if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / "data" / "tours.json"
    destination.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote 20 fictional tour records to", destination)
