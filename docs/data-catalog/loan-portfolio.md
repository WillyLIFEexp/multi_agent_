---
topic: Loan Portfolio
description: 放款餘額與逾期狀態，供信用損失與 NPL 指標使用。Loan balances and delinquency for ECL and NPL metrics.
tables: [FACT_LOAN_BALANCE, DIM_LOAN, DIM_PRODUCT]
---

# Loan Portfolio

Grain: one row per loan per month-end in `FACT_LOAN_BALANCE`. Feeds the
non-performing-loan (NPL) ratio and expected-credit-loss (ECL) risk indicators.

## FACT_LOAN_BALANCE
| Column | Type | Description |
|--------|------|-------------|
| BALANCE_ID | BIGINT (PK) | Surrogate key per loan-month. |
| PERIOD_END | DATE | Month-end reporting date (報表月底). |
| LOAN_KEY | BIGINT (FK) | → DIM_LOAN.LOAN_KEY. |
| PRODUCT_KEY | BIGINT (FK) | → DIM_PRODUCT.PRODUCT_KEY. |
| PRINCIPAL_OUTSTANDING | DECIMAL(18,2) | Remaining principal (本金餘額). |
| INTEREST_ACCRUED | DECIMAL(18,2) | Accrued but unpaid interest. |
| DAYS_PAST_DUE | INT | Days overdue; 0 if current (逾期天數). |
| STAGE | TINYINT | IFRS 9 stage 1 / 2 / 3. |
| ECL_AMOUNT | DECIMAL(18,2) | Expected credit loss provision. |
| NPL_FLAG | BOOLEAN | TRUE if DAYS_PAST_DUE ≥ 90. |

## DIM_LOAN
| Column | Type | Description |
|--------|------|-------------|
| LOAN_KEY | BIGINT (PK) | Surrogate key. |
| LOAN_ID | VARCHAR(24) | Source loan account number. |
| BORROWER_ID | VARCHAR(20) | Borrowing customer code. |
| ORIGINATION_DATE | DATE | Loan disbursement date. |
| MATURITY_DATE | DATE | Contractual maturity. |
| ORIGINAL_AMOUNT | DECIMAL(18,2) | Amount at origination. |
| INTEREST_RATE_PCT | DECIMAL(9,4) | Contractual annual rate. |

## DIM_PRODUCT
| Column | Type | Description |
|--------|------|-------------|
| PRODUCT_KEY | BIGINT (PK) | Surrogate key. |
| PRODUCT_CODE | VARCHAR(20) | Source product code. |
| PRODUCT_NAME | VARCHAR(120) | Display name (產品名稱). |
| PRODUCT_CATEGORY | VARCHAR(40) | MORTGAGE / AUTO / CARD / CORPORATE. |
| IS_SECURED | BOOLEAN | TRUE if collateralised. |
