---
topic: Payments & Transactions
description: 支付交易明細與詐欺標記，供詐欺損失與拒付率指標。Payment transactions with fraud flags for loss and chargeback KRIs.
tables: [FACT_PAYMENT_TXN, DIM_MERCHANT, DIM_CHANNEL]
---

# Payments & Transactions

Grain: one row per authorised payment transaction in `FACT_PAYMENT_TXN`.
Source for fraud-loss rate and chargeback-ratio operational risk indicators.

## FACT_PAYMENT_TXN
| Column | Type | Description |
|--------|------|-------------|
| TXN_ID | BIGINT (PK) | Surrogate key per transaction. |
| TXN_TIMESTAMP | TIMESTAMP | Authorisation time, UTC (交易時間). |
| MERCHANT_KEY | BIGINT (FK) | → DIM_MERCHANT.MERCHANT_KEY. |
| CHANNEL_KEY | BIGINT (FK) | → DIM_CHANNEL.CHANNEL_KEY. |
| AMOUNT | DECIMAL(18,2) | Transaction amount (交易金額). |
| CURRENCY | CHAR(3) | ISO 4217 currency code. |
| AUTH_RESULT | VARCHAR(16) | APPROVED / DECLINED / REVERSED. |
| FRAUD_SCORE | DECIMAL(5,4) | Model fraud probability, 0–1. |
| FRAUD_FLAG | BOOLEAN | TRUE if confirmed fraudulent. |
| CHARGEBACK_FLAG | BOOLEAN | TRUE if later charged back (拒付). |

## DIM_MERCHANT
| Column | Type | Description |
|--------|------|-------------|
| MERCHANT_KEY | BIGINT (PK) | Surrogate key. |
| MERCHANT_ID | VARCHAR(20) | Source merchant code. |
| MERCHANT_NAME | VARCHAR(200) | Display name (商戶名稱). |
| MCC | CHAR(4) | Merchant category code. |
| COUNTRY | CHAR(2) | ISO 3166-1 merchant country. |
| RISK_TIER | VARCHAR(10) | LOW / MEDIUM / HIGH. |

## DIM_CHANNEL
| Column | Type | Description |
|--------|------|-------------|
| CHANNEL_KEY | BIGINT (PK) | Surrogate key. |
| CHANNEL_CODE | VARCHAR(20) | Source channel code. |
| CHANNEL_NAME | VARCHAR(80) | POS / ECOMMERCE / MOBILE / ATM. |
| IS_CARD_PRESENT | BOOLEAN | TRUE for card-present channels. |
