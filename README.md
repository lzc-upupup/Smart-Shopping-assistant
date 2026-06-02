# Smart Shopping Agent

第一版：FastAPI + Vue + LangGraph + mock 商品库。

这个版本先实现一个可本地运行的购物 Agent 工作流：

- 多轮聊天入口
- 购物意图抽取
- 缺少关键信息时追问
- mock 商品搜索
- 商品排序和对比
- 推荐理由生成

当前版本不依赖外部 LLM API，后续可以把 `backend/app/agent/nodes.py` 里的规则节点替换为真实模型调用。

## 目录

```text
backend/   FastAPI + LangGraph 后端
frontend/  Vue + Vite 前端
```

## 后端启动

```powershell
cd backend
conda activate shopping-agent
python -m uvicorn app.main:app --reload --port 8000
```

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

前端默认访问 `http://localhost:8000` 的后端接口。
