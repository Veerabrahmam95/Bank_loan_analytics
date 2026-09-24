# Bank Loan Analytics Dashboard

An end-to-end loan portfolio analysis: a **Power BI dashboard** (`Bank_Loan_Analytics_Dashboard.pbix`) plus a **Python script** that reproduces the same KPIs and charts from the raw data.

## Dashboard overview

The Power BI report has two pages (1920 × 1080):

| Page | What it shows |
|------|---------------|
| **Overview** | Headline KPIs, monthly application trend, applications by state (map), purpose (treemap), home ownership (bar) and term (donut) |
| **Summary** | Good vs Bad loan split, and funded amount, amount received, interest rate and DTI broken down by loan status |

Both pages have slicers for **Grade** and **Purpose**, and a page navigator.

### KPIs

| KPI | Definition |
|-----|-----------|
| Total Loan Applications | Count of loan IDs |
| Total Funded Amount | Sum of `loan_amount` |
| Total Amount Received | Sum of `total_payment` |
| Average Interest Rate | Mean of `int_rate` |
| Average DTI Ratio | Mean of `dti` (debt-to-income) |
| Good Loan % | Applications with status *Fully Paid* or *Current* ÷ total applications |
| Bad Loan % | Applications with status *Charged Off* ÷ total applications |

## Key results

| Metric | Value |
|--------|-------|
| Total loan applications | 38,576 |
| Total funded amount | 435.8M |
| Total amount received | 473.1M |
| Average interest rate | 12.05% |
| Average DTI ratio | 13.33% |
| Good loans / Bad loans | 86.18% / 13.82% |

Charged-off loans (5,333 applications, 65.5M funded) returned only 37.3M. See the project report for the full analysis.

## Repository contents

```
├── bank_loan_analysis.py              # Python analysis script
├── requirements.txt                   # Python dependencies
├── README.md
├── Bank_Loan_Project_Report.docx      # Project report
├── Bank_Loan_Analytics_Dashboard.pbix # Power BI report
└── data/financial_loan.csv            # (add your dataset here)
```

## Getting started

```bash
pip install -r requirements.txt

# Run on the real dataset
python bank_loan_analysis.py --input data/financial_loan.csv --output-dir output

# Or smoke-test on synthetic data (numbers are NOT real)
python bank_loan_analysis.py --demo
```

**Outputs** (in `output/`): `loan_summary.xlsx` (KPIs and all breakdown tables) and seven PNG charts matching the dashboard visuals.

### Expected dataset columns

`id, address_state, grade, home_ownership, issue_date, loan_status, purpose, term, dti, int_rate, loan_amount, total_payment`

Column names are case-insensitive. Interest rate and DTI may be stored as fractions (0.12) or percentages (12); the script handles both.

### Opening the dashboard

Open the `.pbix` in Power BI Desktop. The data source is the `financial_loan` table.

## Tech stack

Power BI Desktop (DAX) · Python 3 · pandas · NumPy · matplotlib · openpyxl

## Notes

- Good/Bad classification: *Fully Paid* and *Current* = Good; *Charged Off* = Bad.
- The state map uses the Azure Maps visual, which needs the Azure Maps tenant setting enabled in Power BI. If it shows a blank message, ask your admin to enable it.
- Dates are parsed day-first; adjust `prepare()` in the script if your file uses another format.
