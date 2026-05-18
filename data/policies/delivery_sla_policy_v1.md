---
doc_id: delivery_sla_policy_v1
version: 1.0
effective_date: 2026-05-18
owner: Fulfillment Operation
risk_level: medium
---

# 物流时效与赔付政策 v1

## 1. 预计送达

每个订单应以 `order_estimated_delivery_date` 作为预计送达日期。

## 2. 延迟送达判断

如果 `order_delivered_customer_date` 晚于 `order_estimated_delivery_date` 超过 2 个自然日，可以进入延迟补偿判断。

## 3. 未送达

如果订单状态不是 delivered，且超过预计送达日期 5 个自然日仍无送达记录，应生成履约异常工单。

## 4. 人工审批

任何补偿建议、退款建议或工单创建都必须进入人工审批。Agent 不得直接承诺现金赔付。
