---
topic: Sales Orders
description: 訂單主檔與明細，含客戶、業務員、出貨狀態。Covers order lifecycle from creation to shipment.
tables: [FACT_SALES_ORDER, DIM_CUSTOMER, DIM_SALESPERSON]
---

# Sales Orders

Grain: one row per order line in `FACT_SALES_ORDER`. Conformed dimensions
`DIM_CUSTOMER` and `DIM_SALESPERSON` are shared with the finance and CRM marts.

## FACT_SALES_ORDER
| Column | Type | Description |
|--------|------|-------------|
| ORDER_LINE_ID | BIGINT (PK) | Surrogate key, one per order line. |
| ORDER_ID | BIGINT | Business order number (訂單編號). |
| CUSTOMER_KEY | BIGINT (FK) | → DIM_CUSTOMER.CUSTOMER_KEY. |
| SALESPERSON_KEY | BIGINT (FK) | → DIM_SALESPERSON.SALESPERSON_KEY. |
| ORDER_DATE | DATE | Date the order was created. |
| SHIP_DATE | DATE | Date shipped; NULL until fulfilled. |
| SHIP_STATUS | VARCHAR(16) | PENDING / PARTIAL / SHIPPED / CANCELLED (出貨狀態). |
| QUANTITY | INT | Units ordered on the line. |
| UNIT_PRICE | DECIMAL(18,4) | Price per unit in ORDER_CURRENCY. |
| LINE_AMOUNT | DECIMAL(18,2) | QUANTITY × UNIT_PRICE, net of line discount. |
| ORDER_CURRENCY | CHAR(3) | ISO 4217 currency code. |

## DIM_CUSTOMER
| Column | Type | Description |
|--------|------|-------------|
| CUSTOMER_KEY | BIGINT (PK) | Surrogate key. |
| CUSTOMER_ID | VARCHAR(20) | Source system customer code. |
| CUSTOMER_NAME | VARCHAR(200) | Legal / display name (客戶名稱). |
| SEGMENT | VARCHAR(40) | ENTERPRISE / SMB / RETAIL. |
| COUNTRY | CHAR(2) | ISO 3166-1 alpha-2 billing country. |
| CREDIT_TERMS_DAYS | INT | Net payment terms in days. |

## DIM_SALESPERSON
| Column | Type | Description |
|--------|------|-------------|
| SALESPERSON_KEY | BIGINT (PK) | Surrogate key. |
| EMPLOYEE_ID | VARCHAR(20) | HR employee number. |
| SALESPERSON_NAME | VARCHAR(120) | Full name (業務員). |
| REGION | VARCHAR(40) | Sales region / territory. |
| MANAGER_ID | VARCHAR(20) | Reporting manager's EMPLOYEE_ID. |
