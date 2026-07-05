---
topic: Credit Exposure
description: 交易對手信用曝險快照，含評等、擔保與限額。Daily counterparty credit exposure with rating, collateral and limits.
tables: [FACT_CREDIT_EXPOSURE, DIM_COUNTERPARTY, DIM_RATING]
---

# Credit Exposure

Grain: one row per counterparty per snapshot date in `FACT_CREDIT_EXPOSURE`.
Used by the credit-risk KRIs (limit utilisation, watchlist concentration).

## FACT_CREDIT_EXPOSURE
| Column | Type | Description |
|--------|------|-------------|
| EXPOSURE_ID | BIGINT (PK) | Surrogate key per counterparty-day. |
| SNAPSHOT_DATE | DATE | As-of date of the exposure (曝險日期). |
| COUNTERPARTY_KEY | BIGINT (FK) | → DIM_COUNTERPARTY.COUNTERPARTY_KEY. |
| RATING_KEY | BIGINT (FK) | → DIM_RATING.RATING_KEY at snapshot. |
| GROSS_EXPOSURE | DECIMAL(18,2) | Total exposure before mitigation, base currency. |
| COLLATERAL_VALUE | DECIMAL(18,2) | Eligible collateral held (擔保品價值). |
| NET_EXPOSURE | DECIMAL(18,2) | GROSS_EXPOSURE − COLLATERAL_VALUE, floored at 0. |
| CREDIT_LIMIT | DECIMAL(18,2) | Approved limit for the counterparty. |
| LIMIT_UTILISATION_PCT | DECIMAL(9,4) | NET_EXPOSURE / CREDIT_LIMIT. |
| WATCHLIST_FLAG | BOOLEAN | TRUE if flagged by credit committee. |

## DIM_COUNTERPARTY
| Column | Type | Description |
|--------|------|-------------|
| COUNTERPARTY_KEY | BIGINT (PK) | Surrogate key. |
| COUNTERPARTY_ID | VARCHAR(20) | Source counterparty code. |
| LEGAL_NAME | VARCHAR(200) | Registered legal name (法人名稱). |
| INDUSTRY_CODE | VARCHAR(10) | NAICS / GICS sector code. |
| DOMICILE_COUNTRY | CHAR(2) | ISO 3166-1 country of incorporation. |
| PARENT_COUNTERPARTY_ID | VARCHAR(20) | Ultimate parent for group aggregation. |

## DIM_RATING
| Column | Type | Description |
|--------|------|-------------|
| RATING_KEY | BIGINT (PK) | Surrogate key. |
| AGENCY | VARCHAR(20) | SP / MOODYS / FITCH / INTERNAL. |
| RATING_CODE | VARCHAR(6) | e.g. AAA, BBB-, Ba1. |
| RATING_RANK | INT | Ordinal (1 = strongest) for sorting/thresholds. |
| IS_INVESTMENT_GRADE | BOOLEAN | TRUE for IG ratings. |
