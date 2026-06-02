# Backend

FastAPI 后端负责 API、Agent 编排和 mock 商品数据访问。

## 核心接口

- `GET /health`
- `POST /api/chat`
- `GET /api/products`
- `GET /api/products/{product_id}`
- `POST /api/compare`

## Agent 流程

```text
extract_intent
  -> check_clarification
  -> write_clarification | search_products
  -> rank_products
  -> compare_products
  -> write_recommendation
```

第一版用规则模拟 Agent 节点，目的是先把状态、工具调用、前后端联动跑通。
