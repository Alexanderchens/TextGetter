# 07 API 网关层 - 详细设计

## 一、概述

API 网关层是前端与后端的桥梁，提供 REST 接口、WebSocket 实时进度、文件上传等能力。

---

## 二、技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 异步、自动文档、类型校验 |
| 文件上传 | FastAPI UploadFile | multipart/form-data |
| WebSocket | FastAPI WebSocket | 实时进度推送 |
| 跨域 | CORSMiddleware | 前后端分离 |

---

## 三、REST API 设计

### 3.1 任务相关

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/tasks | 创建提取任务 |
| GET | /api/tasks/{taskId} | 获取任务详情（含进度、结果） |
| POST | /api/tasks/{taskId}/cancel | 取消任务 |
| GET | /api/tasks | 历史任务列表（分页） |
| DELETE | /api/tasks/{taskId} | 删除任务及关联数据 |

### 3.2 创建任务

**请求**：
```
POST /api/tasks
Content-Type: application/json

{
  "input": "https://www.bilibili.com/video/BV1xx411c7mD",
  "options": {
    "extractMode": "subtitle_first",  // subtitle_first | full | asr_only
    "ocrInterval": 1.0,
    "enableLLMClean": false
  }
}
```

或文件上传：
```
POST /api/tasks
Content-Type: multipart/form-data

input: (file) 视频文件
options: (JSON string) 同上
```

**响应**：
```json
{
  "taskId": "uuid-xxx",
  "status": "pending",
  "message": "任务已创建"
}
```

### 3.3 获取任务详情

**请求**：`GET /api/tasks/{taskId}`

**响应**：
```json
{
  "id": "uuid-xxx",
  "input": "https://...",
  "platform": "bilibili",
  "status": "extracting",
  "progress": 45,
  "stageProgress": {
    "parsing": {"status": "done", "progress": 100},
    "downloading": {"status": "done", "progress": 100},
    "asr": {"status": "running", "progress": 45, "message": "语音识别中..."},
    "ocr": {"status": "pending", "progress": 0},
    "merge": {"status": "pending", "progress": 0}
  },
  "metadata": {
    "title": "视频标题",
    "author": "UP主"
  },
  "result": null,
  "error": null,
  "createdAt": "2025-02-19T10:00:00Z",
  "updatedAt": "2025-02-19T10:02:30Z"
}
```

完成时 `result` 结构：
```json
{
  "result": {
    "fullText": "完整文案内容...",
    "segments": [
      {
        "source": "subtitle",
        "startTime": 0,
        "endTime": 2.5,
        "text": "第一段文字"
      }
    ],
    "stats": {
      "subtitle": {"charCount": 500, "segmentCount": 20},
      "asr": {"charCount": 100, "segmentCount": 5},
      "ocr": {"charCount": 50, "segmentCount": 3}
    }
  }
}
```

### 3.4 历史列表

**请求**：`GET /api/tasks?platform=bilibili&status=completed&limit=20&offset=0`

**响应**：
```json
{
  "items": [
    {
      "id": "uuid-xxx",
      "platform": "bilibili",
      "status": "completed",
      "metadata": {"title": "..."},
      "createdAt": "..."
    }
  ],
  "total": 100
}
```

---

## 四、导出接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/tasks/{taskId}/export?format=markdown | 导出为 Markdown |
| GET | /api/tasks/{taskId}/export?format=txt | 导出为 TXT |

**响应**：`Content-Disposition: attachment; filename="xxx.md"`，直接返回文件流。

或返回 JSON：
```json
{
  "content": "# 标题\n\n文案内容...",
  "format": "markdown"
}
```

---

## 五、WebSocket 设计

### 5.1 连接

```
WS /ws/tasks/{taskId}
```

- 客户端在进入提取详情页时建立连接
- 服务端在任务进度变更时推送消息
- 任务完成或失败后，服务端可主动关闭连接

### 5.2 消息格式

**服务端 → 客户端**：
```json
{
  "type": "progress",
  "taskId": "uuid-xxx",
  "stage": "asr",
  "progress": 60,
  "message": "语音识别进行中..."
}
```

```json
{
  "type": "completed",
  "taskId": "uuid-xxx",
  "result": { ... }
}
```

```json
{
  "type": "failed",
  "taskId": "uuid-xxx",
  "error": "解析失败：平台限制"
}
```

**客户端 → 服务端**：可发送 `ping` 保活，服务端回复 `pong`。

### 5.3 降级

若 WebSocket 不可用（如部分网络环境），前端可退化为轮询 `GET /api/tasks/{taskId}`，每 2 秒一次。

---

## 六、错误响应规范

```json
{
  "error": {
    "code": "UNSUPPORTED_PLATFORM",
    "message": "不支持的链接，请尝试本地上传",
    "detail": {}
  }
}
```

**常见错误码**：
| code | HTTP | 说明 |
|------|------|------|
| UNSUPPORTED_PLATFORM | 400 | 无法识别的平台 |
| TASK_NOT_FOUND | 404 | 任务不存在 |
| TASK_ALREADY_CANCELLED | 400 | 任务已取消 |
| PARSE_FAILED | 502 | 平台解析失败 |
| DOWNLOAD_FAILED | 502 | 媒体下载失败 |

---

## 七、安全与限流

| 措施 | 说明 |
|------|------|
| 请求体大小限制 | 如 100MB，防止大文件耗尽资源 |
| 创建任务频率 | 每 IP 每分钟最多 N 次 |
| 文件类型校验 | 仅允许视频/图片格式 |
| 路径穿越防护 | 上传文件名、路径做安全校验 |

---

## 八、CORS 配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-domain.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```
