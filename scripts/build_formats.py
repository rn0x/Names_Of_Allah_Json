#!/usr/bin/env python3
"""Build distributable database formats from the master JSON.

Reads:  asma_allah_alhusna_saeed_alqahtani.json (repo root)
Writes: data/*.db, data/*.sql, data/*.csv
"""
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "asma_allah_alhusna_saeed_alqahtani.json"
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)

BOOK_TITLE = "شرح أسماء الله الحسنى في ضوء الكتاب والسنة"
BOOK_AUTHOR = "د. سعيد بن علي بن وهف القحطاني"
BOOK_URL = "https://shamela.ws/book/96493"


def main() -> None:
    records = json.loads(MASTER.read_text(encoding="utf-8"))
    assert len(records) == 99, f"expected 99 names, got {len(records)}"

    db_path = OUT / "asma_allah_alhusna.db"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=DELETE")
    cur = con.cursor()

    cur.execute(
        """CREATE TABLE names (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_arabic TEXT,
            meaning TEXT,
            explanation TEXT,
            page INTEGER,
            chapter TEXT,
            url TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE quran_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_id INTEGER NOT NULL REFERENCES names(id),
            text TEXT NOT NULL,
            source TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE hadith_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_id INTEGER NOT NULL REFERENCES names(id),
            text TEXT NOT NULL,
            source TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE scholarly_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_id INTEGER NOT NULL REFERENCES names(id),
            statement TEXT NOT NULL
        )"""
    )
    cur.execute(
        """CREATE TABLE sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_id INTEGER NOT NULL REFERENCES names(id),
            source TEXT NOT NULL
        )"""
    )
    cur.execute(
        """CREATE TABLE related_names (
            name_id INTEGER NOT NULL REFERENCES names(id),
            related_name TEXT NOT NULL,
            PRIMARY KEY (name_id, related_name)
        )"""
    )
    cur.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("CREATE INDEX idx_quran_name ON quran_evidence(name_id)")
    cur.execute("CREATE INDEX idx_hadith_name ON hadith_evidence(name_id)")
    cur.execute("CREATE INDEX idx_scholarly_name ON scholarly_statements(name_id)")
    cur.execute("CREATE INDEX idx_sources_name ON sources(name_id)")

    for r in records:
        ref = r.get("book_reference", {}) or {}
        cur.execute(
            "INSERT INTO names (id, name, name_arabic, meaning, explanation, page, chapter, url)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (r["id"], r.get("name"), r.get("name_arabic"), r.get("meaning"),
             r.get("explanation"), ref.get("page"), ref.get("chapter"), ref.get("url")),
        )
        for q in r.get("quran_evidence", []) or []:
            cur.execute(
                "INSERT INTO quran_evidence (name_id, text, source) VALUES (?,?,?)",
                (r["id"], q.get("text"), q.get("source")),
            )
        for h in r.get("hadith_evidence", []) or []:
            cur.execute(
                "INSERT INTO hadith_evidence (name_id, text, source) VALUES (?,?,?)",
                (r["id"], h.get("text"), h.get("source")),
            )
        for s in r.get("scholarly_statements", []) or []:
            cur.execute(
                "INSERT INTO scholarly_statements (name_id, statement) VALUES (?,?)",
                (r["id"], s),
            )
        for s in r.get("sources", []) or []:
            cur.execute(
                "INSERT INTO sources (name_id, source) VALUES (?,?)", (r["id"], s)
            )
        for rel in r.get("related_names", []) or []:
            cur.execute(
                "INSERT OR IGNORE INTO related_names (name_id, related_name) VALUES (?,?)",
                (r["id"], rel),
            )

    counts = {
        "names": len(records),
        "quran_evidence": sum(len(r.get("quran_evidence", []) or []) for r in records),
        "hadith_evidence": sum(len(r.get("hadith_evidence", []) or []) for r in records),
    }
    from datetime import date

    meta = {
        "book_title": BOOK_TITLE,
        "book_author": BOOK_AUTHOR,
        "book_url": BOOK_URL,
        "records": str(counts["names"]),
        "generated": date.today().isoformat(),
        "source_format": "JSON (asma_allah_alhusna_saeed_alqahtani.json)",
    }
    cur.executemany("INSERT INTO meta (key, value) VALUES (?,?)", meta.items())
    con.commit()

    # SQL dump
    sql_path = OUT / "asma_allah_alhusna.sql"
    with open(sql_path, "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(line + "\n")

    # CSVs (UTF-8 with BOM for Excel Arabic support)
    def write_csv(path, header, rows):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    write_csv(
        OUT / "asma_allah_alhusna_names.csv",
        ["id", "name", "name_arabic", "meaning", "explanation", "page", "chapter", "url", "related_names"],
        [(
            r["id"], r.get("name", ""), r.get("name_arabic", ""), r.get("meaning", ""),
            r.get("explanation", ""), (r.get("book_reference", {}) or {}).get("page", ""),
            (r.get("book_reference", {}) or {}).get("chapter", ""),
            (r.get("book_reference", {}) or {}).get("url", ""),
            "|".join(r.get("related_names", []) or []),
        ) for r in records],
    )
    write_csv(
        OUT / "asma_allah_alhusna_quran.csv",
        ["name_id", "name", "text", "source"],
        [(r["id"], r.get("name", ""), q.get("text", ""), q.get("source", "") or "")
         for r in records for q in (r.get("quran_evidence", []) or [])],
    )
    write_csv(
        OUT / "asma_allah_alhusna_hadith.csv",
        ["name_id", "name", "text", "source"],
        [(r["id"], r.get("name", ""), h.get("text", ""), h.get("source", "") or "")
         for r in records for h in (r.get("hadith_evidence", []) or [])],
    )
    write_csv(
        OUT / "asma_allah_alhusna_scholarly.csv",
        ["name_id", "name", "statement"],
        [(r["id"], r.get("name", ""), s)
         for r in records for s in (r.get("scholarly_statements", []) or [])],
    )
    write_csv(
        OUT / "asma_allah_alhusna_sources.csv",
        ["name_id", "name", "source"],
        [(r["id"], r.get("name", ""), s)
         for r in records for s in (r.get("sources", []) or [])],
    )

    # integrity check
    for table, expected in [
        ("names", counts["names"]),
        ("quran_evidence", counts["quran_evidence"]),
        ("hadith_evidence", counts["hadith_evidence"]),
    ]:
        got = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert got == expected, f"{table}: {got} != {expected}"
    con.close()
    print("OK:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
