import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "processed" / "project.db"

db = sqlite3.connect(DATABASE)
db.row_factory = sqlite3.Row

rows = db.execute("""
    SELECT province, phase, period_start,
           well_milled_price, regular_milled_price
    FROM rice_prices
    WHERE province = ?
    ORDER BY period_start, phase
""", ("Albay",)).fetchall()

for row in rows:
    print(dict(row))

db.close()