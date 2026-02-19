# 04 任务编排调度器模块 - 详细设计

## 一、概述

**职责**：承接用户提交的提取请求，协调平台解析、媒体下载、多模态提取、结果存储等步骤，管理任务生命周期，支持进度回调与重试。

---

## 二、任务状态机

```
                    ┌──────────┐
                    │  created │
                    └────┬─────┘
                         │
                         ▼
┌────────────┐     ┌─────────────┐     ┌─────────────┐
│  cancelled │◄────│   pending   │────►│   parsing   │
└────────────┘     └─────────────┘     └──────┬──────┘
                                              │
                         ┌────────────────────┘
                         ▼
                  ┌─────────────┐
                  │ downloading │
                  └──────┬──────┘
                         │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
  ┌────────────┐   ┌────────────┐   ┌────────────┐
  │  extracting │   │  merging   │   │   failed   │
  │ (asr/ocr)  │   └─────┬──────┘   └────────────┘
  └─────┬──────┘         │
        │                ▼
        │         ┌─────────────┐
        └────────►│  completed  │
                  └─────────────┘
```

### 2.1 状态定义

```python
from enum import Enum

class TaskStatus(str, Enum):
    CREATED = "created"       # 刚创建
    PENDING = "pending"       # 排队中
    PARSING = "parsing"       # 平台解析
    DOWNLOADING = "downloading"  # 媒体下载
    EXTRACTING = "extracting"   # 字幕/ASR/OCR 提取
    MERGING = "merging"       # 合并去重
    COMPLETED = "completed"   # 完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 用户取消
```

### 2.2 子阶段（提取阶段内部）

```python
class ExtractStage(str, Enum):
    SUBTITLE = "subtitle"
    ASR = "asr"
    OCR = "ocr"
    MERGE = "merge"
```

---

## 三、任务模型

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Task:
    id: str
    input: str                    # 链接或本地路径
    platform: str
    status: TaskStatus
    progress: int                 # 0-100
    stage_progress: dict          # {stage: {status, progress, message}}
    result: Optional[ExtractResult] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    meta: dict = None             # 扩展信息
```

### 3.1 阶段进度结构

```python
@dataclass
class StageProgress:
    stage: str                    # parsing | downloading | subtitle | asr | ocr | merge
    status: str                   # pending | running | done | skipped | error
    progress: int = 0             # 0-100
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
```

---

## 四、任务执行流程

```
execute_task(task_id)
    │
    ├─► 1. PARSING
    │       platform_parser.parse(input)
    │       ├─ 成功 → media_list, metadata
    │       └─ 失败 → FAILED, 可重试
    │
    ├─► 2. DOWNLOADING
    │       for media in media_list:
    │           download(media.url) → 本地工作目录
    │       ├─ 成功 → local_paths
    │       └─ 失败 → 重试 2 次 → FAILED
    │
    ├─► 3. EXTRACTING
    │       pipeline.run(media_path, progress_cb)
    │       ├─ subtitle (若有)
    │       ├─ asr
    │       ├─ ocr
    │       └─ 每步更新 stage_progress
    │
    ├─► 4. MERGING
    │       merger.merge(segments)
    │
    └─► 5. COMPLETED
            save_result(); notify();
```

---

## 五、进度回调机制

### 5.1 回调接口

```python
from typing import Callable

ProgressCallback = Callable[[str, int, Optional[str]], None]
# (stage, progress, message) -> None

def default_progress_callback(stage: str, progress: int, message: str = None):
    # 更新 Task 的 stage_progress 和 progress
    # 通过 WebSocket / 轮询 推送给前端
    pass
```

### 5.2 与 WebSocket 集成

```python
# 任务创建时绑定 task_id 与 WebSocket connection_id
# 每次 progress 更新时，向对应 connection 推送：

{
  "type": "progress",
  "taskId": "xxx",
  "stage": "asr",
  "progress": 45,
  "message": "语音识别进行中..."
}
```

---

## 六、并发与队列

### 6.1 队列选型

| 方案 | 适用场景 | 说明 |
|------|----------|------|
| 内存队列 | 单机、轻量 | 简单，重启丢失 |
| Redis + Celery | 多机、持久化 | 生产推荐 |
| Redis + ARQ | 轻量异步 | Python 原生，比 Celery 简单 |

### 6.2 并发控制

- **全局并发数**：同时执行的提取任务数（默认 2）
- **平台限流**：同一平台（如 douyin）每分钟最多 N 次解析，避免触发反爬
- **资源限制**：ASR/OCR 占用 GPU/CPU，需控制并行度

```yaml
orchestrator:
  max_concurrent_tasks: 2
  platform_rate_limit:
    douyin: 5 per minute
    bilibili: 10 per minute
```

### 6.3 任务优先级

- 默认 FIFO
- 可选：用户主动「优先」可插队（实现时用优先级队列）

---

## 七、重试策略

| 阶段 | 重试次数 | 重试间隔 | 条件 |
|------|----------|----------|------|
| parsing | 2 | 5s | 网络超时、5xx |
| downloading | 2 | 10s | 下载失败 |
| extracting | 0 | - | 通常为本地计算，不重试 |
| merge | 0 | - | 无网络 |

### 7.1 指数退避（可选）

```
第 1 次: 5s
第 2 次: 15s
第 3 次: 45s
```

---

## 八、取消与超时

### 8.1 用户取消

- 前端发起 `POST /api/tasks/{id}/cancel`
- 后端将任务标记为 `cancelled`，若正在执行，尝试中止当前步骤（如停止 ffmpeg、Whisper）
- 已下载的媒体可保留或按策略清理

### 8.2 超时

- 单任务超时：如 30 分钟无进展则标记 `failed`
- 解析超时：单次 HTTP 请求 30s
- 下载超时：大文件可配置更长

---

## 九、降级策略

| 场景 | 降级行为 |
|------|----------|
| 平台解析失败 | 返回错误信息，提示用户「可尝试本地上传」 |
| 字幕提取失败 | 自动走 ASR 分支 |
| ASR 失败（如 OOM） | 尝试换小模型或跳过 ASR，仅保留 OCR |
| OCR 失败 | 跳过 OCR，仅保留字幕/ASR |
| 合并失败 | 返回原始分段，不做去重 |

---

## 十、任务持久化

- 任务创建时写入 DB
- 每次状态/进度变更时更新 `updated_at` 和 `stage_progress`
- 完成后写入 `result`（或 result 存单独表，通过 task_id 关联）
- 支持「历史记录」查询、重新提取（基于原 input 创建新任务）

---

## 十一、接口设计（与 API 层衔接）

### 11.1 创建任务

```python
def create_task(input: str, options: dict) -> str:
    """返回 task_id"""
    task = Task(id=generate_id(), input=input, status=PENDING, ...)
    task_repo.save(task)
    queue.enqueue(execute_task, task.id)
    return task.id
```

### 11.2 查询任务

```python
def get_task(task_id: str) -> Optional[Task]:
    return task_repo.get(task_id)
```

### 11.3 取消任务

```python
def cancel_task(task_id: str) -> bool:
    task = get_task(task_id)
    if task.status in (PENDING, PARSING, DOWNLOADING, EXTRACTING, MERGING):
        task.status = CANCELLED
        task_repo.save(task)
        return True
    return False
```
