"""Generates the bundled demo files:  python data/sample/generate_sample_data.py"""
import csv
from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).parent

HANDBOOK = """Northwind Travel Handbook

Remote work policy. Employees may work remotely up to three days per week. Core collaboration hours are 10:00 to 15:00 local time. Fully remote arrangements require written approval from a department head.

Expense policy. Meals while travelling are reimbursed up to 60 USD per day. Flights over 6 hours may be booked in premium economy. All receipts must be submitted within 30 days of the trip.

Vacation. Full-time employees receive 24 days of paid vacation per year. Unused days, up to 5, carry over into the following year."""

SECURITY = """Security Guidelines (v2)

Passwords must be at least 14 characters and rotated every 180 days. Multi-factor authentication is mandatory for all production systems. Lost devices must be reported to the security desk within 2 hours."""

ROWS = [
    ("sku", "product", "category", "price_usd", "stock"),
    ("A100", "Trailblazer Backpack", "bags", 89.0, 42),
    ("A200", "Summit Water Bottle", "accessories", 24.5, 310),
    ("B300", "Nimbus Rain Jacket", "apparel", 129.0, 18),
    ("B310", "Drift Fleece", "apparel", 74.0, 0),
    ("C400", "Compass Pro", "gear", 39.0, 120),
]


def main():
    (OUT / "security_guidelines.txt").write_text(SECURITY, encoding="utf-8")
    with (OUT / "products.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(ROWS)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for para in HANDBOOK.split("\n\n"):
        pdf.multi_cell(0, 7, para)
        pdf.ln(3)
    pdf.output(str(OUT / "company_handbook.pdf"))
    print("Wrote", *sorted(p.name for p in OUT.iterdir() if p.suffix != ".py"))


if __name__ == "__main__":
    main()
