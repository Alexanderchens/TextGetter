# 01 统一前端模块 - 详细设计

## 一、概述

统一前端作为用户唯一入口，提供链接粘贴、文件上传、任务管理、文案展示与导出等完整能力。

---

## 二、技术栈

| 类别 | 选型 | 理由 |
|------|------|------|
| 框架 | React 18 + TypeScript | 生态成熟，类型安全 |
| 构建 | Vite | 启动快，HMR 友好 |
| 样式 | Tailwind CSS | 快速布局，设计一致 |
| 状态管理 | Zustand | 轻量，适合中等复杂度 |
| 请求 | TanStack Query (React Query) | 缓存、重试、轮询 |
| 路由 | React Router v6 | SPA 标准方案 |
| 桌面版（可选） | Tauri / Electron | 本地文件访问、系统集成 |

---

## 三、页面与路由

```
/                    首页 - 输入区 + 快捷操作
/extract/:taskId     提取详情 - 进度 + 文案展示 + 编辑
/history             历史记录 - 任务列表
/settings            设置 - 模型选择、导出偏好
```

---

## 四、核心页面设计

### 4.1 首页 (/)

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│  Logo / 标题                                            │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │  Tab: 链接提取 | 文件上传                          │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  输入框 / 拖拽区                                   │   │
│  │  [ 粘贴链接或拖入文件 ]                            │   │
│  │                                                   │   │
│  │  [ 开始提取 ] [ 高级选项 ▼ ]                        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  近期任务（卡片列表，可点击跳转详情）                      │
└─────────────────────────────────────────────────────────┘
```

**高级选项**（可折叠）：
- 提取模式：字幕优先 / 全量多模态 / 仅语音
- OCR 采样间隔：0.5s / 1s / 2s
- 是否启用 LLM 清洗

### 4.2 提取详情页 (/extract/:taskId)

**布局**：
```
┌─────────────────────────────────────────────────────────┐
│  ← 返回  任务 #xxx  平台: B站  状态: 提取中 60%          │
├──────────────────┬──────────────────────────────────────┤
│  进度面板         │  文案预览区                           │
│                  │                                      │
│  ✓ 平台识别      │  ┌────────────────────────────────┐  │
│  ✓ 媒体下载      │  │ [来源] 00:12-00:25 字幕          │  │
│  ◐ ASR 进行中   │  │ 这是一段从字幕提取的文字...       │  │
│  ○ OCR 等待     │  │ [来源] 00:25-00:40 语音          │  │
│  ○ 合并去重     │  │ 这是语音识别的结果...             │  │
│                  │  └────────────────────────────────┘  │
│  [ 重试 ] [ 取消 ]│  [ 编辑 ] [ 导出 ▼ ] [ 总结 ]         │
└──────────────────┴──────────────────────────────────────┘
```

**进度阶段**（与后端 TaskState 对齐）：
- `pending` - 等待
- `parsing` - 平台解析
- `downloading` - 媒体下载
- `extracting_subtitle` - 字幕提取
- `extracting_asr` - 语音识别
- `extracting_ocr` - 画面文字识别
- `merging` - 合并去重
- `completed` / `failed`

### 4.3 历史记录页 (/history)

- 列表展示：平台图标、标题、创建时间、状态
- 筛选：按平台、时间、状态
- 操作：查看详情、删除、重新提取

---

## 五、组件拆分

```
src/
├── components/
│   ├── common/
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── Toast.tsx
│   │   └── Modal.tsx
│   ├── extract/
│   │   ├── LinkInput.tsx        # 链接输入 + 平台预览
│   │   ├── FileUpload.tsx       # 拖拽上传
│   │   ├── ExtractOptions.tsx   # 高级选项
│   │   ├── ProgressPanel.tsx    # 阶段进度
│   │   └── ContentViewer.tsx    # 文案展示（分段、来源标签）
│   ├── export/
│   │   ├── ExportModal.tsx      # 导出格式选择
│   │   └── CopyButton.tsx       # 一键复制
│   └── layout/
│       ├── Header.tsx
│       └── Sidebar.tsx
├── pages/
│   ├── HomePage.tsx
│   ├── ExtractDetailPage.tsx
│   └── HistoryPage.tsx
├── hooks/
│   ├── useExtractTask.ts        # 创建任务、轮询状态
│   ├── useWebSocket.ts          # 实时进度
│   └── useExport.tsx
├── stores/
│   ├── taskStore.ts             # 任务列表、当前任务
│   └── settingsStore.ts         # 用户偏好
├── api/
│   ├── client.ts                # axios/fetch 封装
│   ├── tasks.ts                 # 任务相关 API
│   └── types.ts                 # 请求/响应类型
└── utils/
    ├── platformIcon.ts          # 平台图标映射
    └── formatters.ts            # 时间、文件大小格式化
```

---

## 六、状态管理

### 6.1 任务状态 (taskStore)

```typescript
interface TaskState {
  tasks: Task[];
  currentTaskId: string | null;
}

interface Task {
  id: string;
  input: string;           // 链接或文件路径
  platform: PlatformType;
  status: TaskStatus;
  progress: number;        // 0-100
  stages: StageProgress[]; // 各阶段详情
  result?: ExtractedContent;
  error?: string;
  createdAt: string;
  updatedAt: string;
}

interface StageProgress {
  stage: 'parsing' | 'downloading' | 'asr' | 'ocr' | 'merging';
  status: 'pending' | 'running' | 'done' | 'skipped' | 'error';
  progress?: number;
  message?: string;
}
```

### 6.2 设置状态 (settingsStore)

```typescript
interface Settings {
  extractMode: 'subtitle_first' | 'full' | 'asr_only';
  ocrInterval: number;      // 秒
  enableLLMClean: boolean;
  defaultExportFormat: 'markdown' | 'txt';
}
```

---

## 七、API 调用流程

### 7.1 创建提取任务

```
POST /api/tasks
Body: { input: string, options?: ExtractOptions }
Response: { taskId: string }

→ 跳转 /extract/:taskId
→ 开启 WebSocket 或轮询获取进度
```

### 7.2 实时进度（二选一）

- **WebSocket**：`ws://host/ws/tasks/{taskId}`，服务端推送进度
- **轮询**：`GET /api/tasks/{taskId}`，每 1-2 秒轮询

### 7.3 导出

```
POST /api/tasks/{taskId}/export
Body: { format: 'markdown' | 'txt' }
Response: 文件流 或 { content: string }
```

---

## 八、文案展示组件 (ContentViewer) 详细设计

**需求**：分段展示，每段标注来源（字幕/语音/OCR）和时间轴。

**数据结构**：
```typescript
interface ContentSegment {
  id: string;
  source: 'subtitle' | 'asr' | 'ocr';
  startTime: number;   // 秒
  endTime: number;     // 秒
  text: string;
  confidence?: number; // 可选，ASR 置信度
}
```

**交互**：
- 点击某段可高亮，若有视频预览可跳转对应时间
- 支持整段编辑（内联或弹窗）
- 来源标签颜色区分：字幕=绿、语音=蓝、OCR=橙

---

## 九、导出功能

| 格式 | 实现方式 | 说明 |
|------|----------|------|
| Markdown | 前端拼接 | 分段 + 来源注释 |
| TXT | 前端拼接 | 纯文本，可选保留/去掉时间轴 |
| 复制到剪贴板 | navigator.clipboard | 即时复制 |
| Notion（可选） | 调用 Notion API | 需用户配置 Token |

---

## 十、错误与边界处理

| 场景 | 处理方式 |
|------|----------|
| 不支持的链接 | Toast 提示 + 建议本地上传 |
| 任务失败 | 详情页展示错误信息 + 重试按钮 |
| 网络断开 | 乐观重试，必要时提示检查连接 |
| 大文件上传 | 分片上传 + 进度条 |
| 长时间任务 | 允许离开页面，历史记录可恢复 |

---

## 十一、无障碍与性能

- 主要操作支持键盘导航（Tab、Enter）
- 图片/图标提供 alt 文本
- 长列表虚拟滚动（若历史记录很多）
- 路由懒加载，首屏精简
