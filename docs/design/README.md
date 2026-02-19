# 模块详细设计文档

本目录包含 TextGetter 各核心模块的详细设计，与 [ARCHITECTURE.md](../ARCHITECTURE.md) 中的整体架构对应。

---

## 文档索引

| 文档 | 模块 | 主要内容 |
|------|------|----------|
| [01-frontend.md](01-frontend.md) | 统一前端 | 页面结构、组件拆分、状态管理、API 调用、文案展示 |
| [02-platform-parser.md](02-platform-parser.md) | 平台解析器 | 接口定义、平台识别流程、解析器调度、错误定义 |
| [03-content-extractor.md](03-content-extractor.md) | 多模态文案提取器 | 字幕/ASR/OCR 子模块、合并器、LLM 清洗、流水线编排 |
| [04-task-orchestrator.md](04-task-orchestrator.md) | 任务编排调度器 | 状态机、进度回调、并发队列、重试与降级 |
| [05-platform-adapters.md](05-platform-adapters.md) | 平台适配器 | B站/抖音/快手/小红书等各平台实现要点 |
| [06-data-layer.md](06-data-layer.md) | 数据层 | 表结构、Repository、媒体缓存、知识库扩展 |
| [07-api-gateway.md](07-api-gateway.md) | API 网关 | REST 接口、WebSocket、错误规范、安全限流 |

---

## 模块依赖关系

```
前端 ──► API 网关 ──► 任务编排器 ──┬─► 平台解析器 ──► 平台适配器
                   │              └─► 文案提取器 ──► 字幕/ASR/OCR/合并
                   └─► 数据层（任务、结果、缓存）
```

---

## 阅读建议

1. 先阅读 [ARCHITECTURE.md](../ARCHITECTURE.md) 了解整体架构
2. 按实现顺序阅读：平台解析器 → 平台适配器 → 文案提取器 → 任务编排器 → 数据层 → API 网关 → 前端
3. 各文档包含接口定义、数据结构、伪代码，可直接作为开发参考
