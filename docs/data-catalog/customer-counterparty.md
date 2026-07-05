---
topic: Customer & Counterparty
description: 客戶主檔與 KYC/AML 風險評分，供合規與集中度指標。Customer master with KYC/AML scoring for compliance and concentration KRIs.
tables: [FACT_CUSTOMER_RISK, DIM_CUSTOMER, DIM_KYC_STATUS]
---

# Customer & Counterparty

Grain: one row per customer per risk-review cycle in `FACT_CUSTOMER_RISK`.
`DIM_CUSTOMER` here is the same conformed dimension used by Sales Orders.

## FACT_CUSTOMER_RISK
| Column | Type | Description |
|--------|------|-------------|
| RISK_REVIEW_ID | BIGINT (PK) | Surrogate key per review. |
| REVIEW_DATE | DATE | Date of the risk review (覆核日期). |
| CUSTOMER_KEY | BIGINT (FK) | → DIM_CUSTOMER.CUSTOMER_KEY. |
| KYC_STATUS_KEY | BIGINT (FK) | → DIM_KYC_STATUS.KYC_STATUS_KEY. |
| AML_RISK_SCORE | DECIMAL(5,2) | Model AML risk score, 0–100 (洗錢風險分數). |
| PEP_FLAG | BOOLEAN | TRUE if politically exposed person. |
| SANCTIONS_HIT | BOOLEAN | TRUE if matched a sanctions list. |
| TOTAL_RELATIONSHIP_VALUE | DECIMAL(18,2) | Aggregate balance across products. |
| NEXT_REVIEW_DUE | DATE | Scheduled next review date. |

## DIM_CUSTOMER
| Column | Type | Description |
|--------|------|-------------|
| CUSTOMER_KEY | BIGINT (PK) | Surrogate key (conformed). |
| CUSTOMER_ID | VARCHAR(20) | Source system customer code. |
| CUSTOMER_NAME | VARCHAR(200) | Legal / display name (客戶名稱). |
| SEGMENT | VARCHAR(40) | ENTERPRISE / SMB / RETAIL. |
| COUNTRY | CHAR(2) | ISO 3166-1 domicile country. |
| ONBOARD_DATE | DATE | Relationship start date. |

## DIM_KYC_STATUS
| Column | Type | Description |
|--------|------|-------------|
| KYC_STATUS_KEY | BIGINT (PK) | Surrogate key. |
| STATUS_CODE | VARCHAR(20) | VERIFIED / PENDING / EXPIRED / REJECTED. |
| STATUS_DESC | VARCHAR(120) | Human-readable description (狀態說明). |
| IS_COMPLIANT | BOOLEAN | TRUE if status permits transacting. |
