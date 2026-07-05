---
topic: Regulatory & Operational Events
description: 合規違規與作業損失事件，供作業風險與法遵指標。Compliance breaches and operational loss events for op-risk KRIs.
tables: [FACT_RISK_EVENT, DIM_EVENT_TYPE, DIM_BUSINESS_UNIT]
---

# Regulatory & Operational Events

Grain: one row per logged risk event in `FACT_RISK_EVENT`. Feeds the
regulatory-breach count and operational-loss KRIs by business unit.

## FACT_RISK_EVENT
| Column | Type | Description |
|--------|------|-------------|
| EVENT_ID | BIGINT (PK) | Surrogate key per event. |
| EVENT_DATE | DATE | Date the event occurred (事件日期). |
| DISCOVERED_DATE | DATE | Date the event was discovered. |
| EVENT_TYPE_KEY | BIGINT (FK) | → DIM_EVENT_TYPE.EVENT_TYPE_KEY. |
| BUSINESS_UNIT_KEY | BIGINT (FK) | → DIM_BUSINESS_UNIT.BUSINESS_UNIT_KEY. |
| SEVERITY | VARCHAR(10) | LOW / MEDIUM / HIGH / CRITICAL. |
| GROSS_LOSS | DECIMAL(18,2) | Direct financial loss (毛損失). |
| RECOVERY_AMOUNT | DECIMAL(18,2) | Amount recovered / insured. |
| NET_LOSS | DECIMAL(18,2) | GROSS_LOSS − RECOVERY_AMOUNT. |
| IS_REGULATORY_BREACH | BOOLEAN | TRUE if a reportable breach. |
| STATUS | VARCHAR(16) | OPEN / IN_REVIEW / CLOSED. |

## DIM_EVENT_TYPE
| Column | Type | Description |
|--------|------|-------------|
| EVENT_TYPE_KEY | BIGINT (PK) | Surrogate key. |
| BASEL_CATEGORY | VARCHAR(60) | Basel II operational-risk category. |
| EVENT_TYPE_NAME | VARCHAR(120) | Display name (事件類型). |
| IS_REPORTABLE | BOOLEAN | TRUE if regulator-reportable by default. |

## DIM_BUSINESS_UNIT
| Column | Type | Description |
|--------|------|-------------|
| BUSINESS_UNIT_KEY | BIGINT (PK) | Surrogate key. |
| BU_CODE | VARCHAR(20) | Source business-unit code. |
| BU_NAME | VARCHAR(120) | Display name (單位名稱). |
| DIVISION | VARCHAR(60) | Parent division. |
| REGION | VARCHAR(40) | Operating region. |
