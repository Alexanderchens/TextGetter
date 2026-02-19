# 06 数据层模块 - 详细设计

## 一、概述

数据层负责任务记录、提取结果、媒体缓存的持久化与查询，可选知识库/向量存储。

---

## 二、存储组件

| 组件 | 用途 | 技术选型 |
|------|------|----------|
| 任务记录 | 任务元信息、状态、进度 | SQLite / PostgreSQL |
| 提取结果 | 文案内容、分段 | 同库或 JSON 文件 |
| 媒体缓存 | 下载的视频/音频 | 本地文件系统 / 对象存储 |
| 知识库（可选） | 向量索引、语义检索 | Chroma / Milvus / pgvector |

---

## 三、任务表设计

### 3.1 tasks 表

```sql
CREATE TABLE tasks (
    id              TEXT PRIMARY KEY,
    input           TEXT NOT NULL,           -- 原始链接或路径
    platform        TEXT NOT NULL,
    status          TEXT NOT NULL,          -- created|pending|parsing|...
    progress        INTEGER DEFAULT 0,       -- 0-100
    stage_progress  JSONB,                   -- {"asr": {"status":"running","progress":50}}
    error           TEXT,
    metadata        JSONB,                  -- 平台返回的 title、author 等
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_platform ON tasks(platform);
```

### 3.2 task_results 表（提取结果）

```sql
CREATE TABLE task_results (
    task_id         TEXT PRIMARY KEY REFERENCES tasks(id),
    full_text       TEXT NOT NULL,           -- 合并后的完整文案
    segments        JSONB NOT NULL,          -- [{"source":"asr","start":0,"end":2.5,"text":"..."}]
    stats           JSONB,                   -- 各来源字数、占比等
    created_at      TIMESTAMP DEFAULT NOW()
);
```

**合并存储方案**：若结果较大，可考虑 `full_text` 存文件路径，DB 仅存 segments 的轻量索引。

---

## 四、媒体缓存设计

### 4.1 存储策略

```
storage/
├── cache/
│   ├── {task_id}/
│   │   ├── video.mp4          # 下载的视频
│   │   ├── audio.wav          # 提取的音频（可选保留）
│   │   └── subtitle.srt        # 外挂字幕（若有）
│   └── ...
├── temp/                      # 临时文件，任务完成后可清理
└── ...
```

### 4.2 清理策略

| 策略 | 说明 |
|------|------|
| 任务完成后立即删除 | 节省空间，无法重复提取 |
| 保留 N 天 | 按 `created_at` 清理，默认 7 天 |
| 手动清理 | 设置页提供「清空缓存」按钮 |

**配置**：
```yaml
storage:
  cache_root: ./data/cache
  retention_days: 7
  max_total_size_gb: 20
```

### 4.3 与任务关联

- 任务创建时分配 `task_id`
- 下载媒体到 `cache/{task_id}/`
- 提取完成后，结果中引用 `media_path`，清理时一并删除

---

## 五、Repository 层设计

### 5.1 TaskRepository

```python
class TaskRepository:
    def create(self, task: Task) -> None: ...
    def get(self, task_id: str) -> Optional[Task]: ...
    def update(self, task: Task) -> None: ...
    def list(self, platform: str = None, status: str = None,
             limit: int = 50, offset: int = 0) -> list[Task]: ...
    def delete(self, task_id: str) -> None: ...
```

### 5.2 TaskResultRepository

```python
class TaskResultRepository:
    def save(self, task_id: str, result: ExtractResult) -> None: ...
    def get(self, task_id: str) -> Optional[ExtractResult]: ...
    def delete(self, task_id: str) -> None: ...
```

### 5.3 StorageService（媒体文件）

```python
class StorageService:
    def get_task_dir(self, task_id: str) -> Path: ...
    def save_media(self, task_id: str, url: str, filename: str) -> Path: ...
    def get_media_path(self, task_id: str, filename: str) -> Path: ...
    def cleanup_task(self, task_id: str) -> None: ...
    def cleanup_expired(self, retention_days: int) -> int: ...
```

---

## 六、知识库（可选扩展）

### 6.1 用途

- 对历史提取的文案做向量索引
- 支持语义搜索、相似内容推荐
- 为「知识归纳」功能提供检索基础

### 6.2 数据模型

```python
# 文档块（可对长文案做切片）
DocumentChunk = {
    "id": str,
    "task_id": str,
    "content": str,
    "embedding": list[float],
    "metadata": {"source": "asr", "start_time": 0, ...}
}
```

### 6.3 技术选型

| 方案 | 优点 | 适用 |
|------|------|------|
| Chroma | 轻量、易嵌入 | 本地单机 |
| pgvector | 与 PG 一体 | 已有 PostgreSQL |
| Milvus | 大规模 | 生产级 |

### 6.4 接口（可选实现）

```python
class KnowledgeService:
    def add_document(self, task_id: str, content: str, metadata: dict) -> None: ...
    def search(self, query: str, top_k: int = 10) -> list[SearchResult]: ...
    def delete_by_task(self, task_id: str) -> None: ...
```

---

## 七、 migrations

建议使用 Alembic 管理 SQL 迁移：

```
migrations/
├── versions/
│   ├── 001_initial.py
│   └── ...
└── env.py
```

---

## 八、连接与配置

```python
# 开发环境：SQLite
DATABASE_URL = "sqlite:///./data/getthetext.db"

# 生产环境：PostgreSQL
DATABASE_URL = "postgresql://user:pass@host:5432/getthetext"
```

使用 SQLAlchemy 或 asyncpg + 原生 SQL，按项目偏好选择。
