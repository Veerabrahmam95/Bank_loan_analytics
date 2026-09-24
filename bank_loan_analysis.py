"""
Bank Loan Analytics - Python companion to the Power BI dashboard
(Bank_Loan_Analytics_Dashboard.pbix).

Recomputes the dashboard KPIs and breakdowns from the raw loan dataset
(table `financial_loan`) and exports summary tables and charts.

Usage:
    python bank_loan_analysis.py --input financial_loan.csv --output-dir output
    python bank_loan_analysis.py --demo          # smoke test on synthetic data
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless-safe backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "id", "address_state", "grade", "home_ownership", "issue_date",
    "loan_status", "purpose", "term", "dti", "int_rate",
    "loan_amount", "total_payment",
]
GOOD_STATUSES = {"Fully Paid", "Current"}   # everything else = "Bad" (Charged Off)
BAD_STATUSES = {"Charged Off"}


# --------------------------------------------------------------------------- #
# Load & prepare
# --------------------------------------------------------------------------- #
def load_data(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {p}")
    df = pd.read_excel(p) if p.suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(p)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    return df


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["issue_date"] = pd.to_datetime(df["issue_date"], errors="coerce", dayfirst=True)
    df["month"] = df["issue_date"].dt.to_period("M").dt.to_timestamp()
    # Interest rate / DTI are stored as fractions (0.12) in the source data
    for col in ("int_rate", "dti"):
        if df[col].max() <= 1.5:
            df[col] = df[col] * 100
    df["good_vs_bad_loan"] = np.where(df["loan_status"].isin(GOOD_STATUSES), "Good", "Bad")
    return df


# --------------------------------------------------------------------------- #
# KPIs (mirror the DAX measures used in the dashboard)
# --------------------------------------------------------------------------- #
def kpis(df: pd.DataFrame) -> dict:
    n = df["id"].nunique()
    return {
        "Total Loan Applications": n,
        "Total Funded Amount": df["loan_amount"].sum(),
        "Total Amount Received": df["total_payment"].sum(),
        "Average Interest Rate (%)": df["int_rate"].mean(),
        "Average DTI (%)": df["dti"].mean(),
        "Good Loan %": 100 * (df["good_vs_bad_loan"] == "Good").sum() / n if n else 0,
        "Bad Loan %": 100 * (df["good_vs_bad_loan"] == "Bad").sum() / n if n else 0,
    }


def good_bad_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("good_vs_bad_loan")
              .agg(applications=("id", "nunique"),
                   funded_amount=("loan_amount", "sum"),
                   amount_received=("total_payment", "sum"))
              .reset_index())


def by_loan_status(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("loan_status")
              .agg(applications=("id", "nunique"),
                   funded_amount=("loan_amount", "sum"),
                   amount_received=("total_payment", "sum"),
                   avg_interest_rate=("int_rate", "mean"),
                   avg_dti=("dti", "mean"))
              .reset_index())


def count_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    return (df.groupby(col)["id"].nunique()
              .sort_values(ascending=False)
              .rename("applications").reset_index())


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("month")
              .agg(applications=("id", "nunique"),
                   funded_amount=("loan_amount", "sum"),
                   amount_received=("total_payment", "sum"))
              .reset_index().sort_values("month"))


# --------------------------------------------------------------------------- #
# Charts (one PNG per dashboard visual)
# --------------------------------------------------------------------------- #
def _save(fig, out: Path, name: str):
    fig.tight_layout()
    fig.savefig(out / name, dpi=150)
    plt.close(fig)


def make_charts(df: pd.DataFrame, out: Path):
    m = monthly_trend(df)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(m["month"], m["applications"], marker="o")
    ax.set(title="Monthly Loan Applications", ylabel="Applications")
    _save(fig, out, "01_monthly_applications.png")

    s = count_by(df, "address_state").head(10)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(s["address_state"], s["applications"])
    ax.set(title="Loan Applications by State (Top 10)", ylabel="Applications")
    _save(fig, out, "02_applications_by_state.png")

    t = count_by(df, "term")
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(t["applications"], labels=t["term"], autopct="%1.1f%%",
           wedgeprops={"width": 0.45})
    ax.set_title("Loan Applications by Term")
    _save(fig, out, "03_applications_by_term.png")

    h = count_by(df, "home_ownership")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(h["home_ownership"], h["applications"])
    ax.set(title="Loan Applications by Home Ownership", ylabel="Applications")
    _save(fig, out, "04_applications_by_home_ownership.png")

    p = count_by(df, "purpose").sort_values("applications")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(p["purpose"], p["applications"])
    ax.set(title="Loan Applications by Purpose", xlabel="Applications")
    _save(fig, out, "05_applications_by_purpose.png")

    g = good_bad_summary(df)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(g["applications"], labels=g["good_vs_bad_loan"], autopct="%1.1f%%",
           wedgeprops={"width": 0.45})
    ax.set_title("Good vs Bad Loans")
    _save(fig, out, "06_good_vs_bad.png")

    ls = by_loan_status(df)
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(ls))
    ax.bar(x - 0.2, ls["funded_amount"], 0.4, label="Funded")
    ax.bar(x + 0.2, ls["amount_received"], 0.4, label="Received")
    ax.set_xticks(x, ls["loan_status"])
    ax.set(title="Funded vs Received Amount by Loan Status")
    ax.legend()
    _save(fig, out, "07_funded_vs_received_by_status.png")


# --------------------------------------------------------------------------- #
# Synthetic data (for smoke-testing only - NOT real results)
# --------------------------------------------------------------------------- #
def demo_data(n: int = 2000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    loan = rng.integers(1000, 35000, n)
    return pd.DataFrame({
        "id": np.arange(1, n + 1),
        "address_state": rng.choice(["CA", "NY", "TX", "FL", "IL", "NJ"], n),
        "grade": rng.choice(list("ABCDEFG"), n),
        "home_ownership": rng.choice(["RENT", "MORTGAGE", "OWN", "OTHER"], n),
        "issue_date": pd.Timestamp("2021-01-01") + pd.to_timedelta(rng.integers(0, 365, n), "D"),
        "loan_status": rng.choice(["Fully Paid", "Current", "Charged Off"], n, p=[.8, .06, .14]),
        "purpose": rng.choice(["debt_consolidation", "credit_card", "car", "other"], n),
        "term": rng.choice(["36 months", "60 months"], n),
        "dti": rng.uniform(0.02, 0.30, n),
        "int_rate": rng.uniform(0.06, 0.24, n),
        "loan_amount": loan,
        "total_payment": (loan * rng.uniform(0.3, 1.3, n)).round(),
    })


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Bank Loan Analytics")
    ap.add_argument("--input", help="Path to financial_loan .csv/.xlsx")
    ap.add_argument("--output-dir", default="output")
    ap.add_argument("--demo", action="store_true", help="Run on synthetic data")
    args = ap.parse_args()
    if not args.demo and not args.input:
        ap.error("provide --input <file> or use --demo")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = prepare(demo_data() if args.demo else load_data(args.input))
    k = kpis(df)

    print("\n=== KEY METRICS ===")
    for name, val in k.items():
        print(f"{name:28s}: {val:,.2f}")

    with pd.ExcelWriter(out / "loan_summary.xlsx") as xw:
        pd.Series(k, name="value").to_frame().to_excel(xw, sheet_name="KPIs")
        good_bad_summary(df).to_excel(xw, sheet_name="Good_vs_Bad", index=False)
        by_loan_status(df).to_excel(xw, sheet_name="By_Loan_Status", index=False)
        monthly_trend(df).to_excel(xw, sheet_name="Monthly_Trend", index=False)
        for col in ("address_state", "purpose", "term", "home_ownership", "grade"):
            count_by(df, col).to_excel(xw, sheet_name=f"By_{col}"[:31], index=False)

    make_charts(df, out)
    print(f"\nSaved summary workbook and charts to: {out.resolve()}")


if __name__ == "__main__":
    main()
