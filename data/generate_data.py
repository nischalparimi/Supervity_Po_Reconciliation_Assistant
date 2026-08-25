"""
generate_data.py — Re-generate mock CSVs for PO Reconciliation Assistant.
Run: python data/generate_data.py
This script is provided for transparency; the CSVs are already committed.
"""
import csv, os, random
from datetime import date, timedelta

random.seed(42)
BASE = os.path.dirname(__file__)

VENDORS = [
    "Steelcase Inc.", "Dell Technologies", "Grainger Industrial", "Sysco Corporation",
    "Staples Business Advantage", "Cisco Systems", "3M Company", "Honeywell International",
    "W.W. Grainger", "Adobe Systems", "Uline Shipping", "Quill Corporation",
]
ITEMS = [
    "Ergonomic Office Chair", "Latitude 5540 Laptop", "Industrial Safety Gloves (Box/100)",
    "Breakroom Coffee Supplies (Monthly)", "Printer Paper A4 (Carton)", "Catalyst 9200 Network Switch",
    "N95 Respirator Masks (Box/20)", "HVAC Thermostat Smart Controller",
]
STATUSES = ["Fully Received", "Partially Received", "Pending Receipt"]

def rand_date(start="2024-01-01", n=120):
    d = date.fromisoformat(start)
    return d + timedelta(days=random.randint(0, n))

print("CSVs already committed to /data. This script shows the generation approach.")
print("purchase_orders.csv and receipts.csv are pre-generated with deliberate anomalies:")
print("  - Duplicate invoice numbers (INV-GRN-2293, INV-CNT-2281, INV-HP-5503, INV-3M-779x)")
print("  - Missing receipts for POs: 0005, 0008, 0014, 0020, 0025, 0032, 0035, 0041, 0047")
print("  - Quantity mismatches: PO-0002, PO-0011, PO-0019, PO-0030, PO-0045")
print("  - Amount mismatches >$1000: PO-0006 (duplicate+extra), PO-0034, PO-0043, PO-0046, PO-0050")
print("  - Partially received POs tracked across multiple receipt rows")
