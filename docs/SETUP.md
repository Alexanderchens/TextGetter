# 环境配置与运行指南

本文档详细介绍 GetTheText 项目的环境配置、依赖安装与运行方式。

---

## 一、环境要求

### 1.1 必选环境

| 依赖 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.10+ | 后端运行环境 |
| Node.js | 18+ | 前端构建与开发 |
| ffmpeg | 最新稳定版 | 从视频提取音频（ASR 前置） |
| npm / pnpm | 随 Node.js 安装 | 前端依赖管理 |

### 1.2 可选环境

| 依赖 | 用途 |
|------|------|
| openai-whisper | 语音识别 (ASR)，未安装时仅使用字幕 |
| NVIDIA GPU + CUDA | 加速 Whisper 模型推理 |
| yt-dlp | B 站等平台链接解析（已在 requirements 中） |

### 1.3 环境检查

```bash
# 检查 Python 版本
python --version   # 或 python3 --version

# 检查 Node.js 版本
node --version

# 检查 ffmpeg 是否已安装
ffmpeg -version
```

---

## 二、系统依赖安装

### 2.1 ffmpeg

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
- 从 [ffmpeg 官网](https://ffmpeg.org/download.html) 下载
- 解压后将 `bin` 目录加入系统 PATH

---

## 三、项目依赖安装

### 3.1 克隆项目

```bash
git clone https://github.com/Alexanderchens/TextGetter.git
cd TextGetter
```

### 3.2 后端依赖

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**可选：安装 Whisper（语音识别）**
```bash
pip install openai-whisper
```

> 若未安装 Whisper，系统仍可运行，但仅能提取字幕，无法对纯语音视频进行 ASR 识别。

### 3.3 前端依赖

```bash
cd frontend
npm install
```

---

## 四、配置说明

### 4.1 后端配置

后端使用 `pydantic-settings` 管理配置，可通过环境变量或 `.env` 文件覆盖。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/getthetext.db` | 数据库连接 |
| `DEBUG` | `false` | 调试模式 |
| `ASR_MODEL` | `base` | Whisper 模型 (tiny/base/small/medium/large-v3) |

创建 `backend/.env` 示例：
```env
DEBUG=false
ASR_MODEL=base
```

### 4.2 前端配置

前端默认请求 `http://localhost:8000` 的后端 API。若需修改，编辑 `frontend/src/api/client.ts` 中的 `API_BASE`。

---

## 五、运行方式

### 5.1 开发模式（推荐）

**终端 1 - 启动后端：**
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 - 启动前端：**
```bash
cd frontend
npm run dev
```

- 后端 API 文档：http://localhost:8000/docs
- 前端地址：http://localhost:5173

### 5.2 使用 run.sh 脚本

```bash
cd backend
chmod +x run.sh
./run.sh
```

该脚本会启动后端服务（端口 8000），前端需另外启动。

### 5.3 生产构建

**前端构建：**
```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/`，可部署到任意静态文件服务器。

**后端生产运行：**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 六、数据目录

首次运行后，后端会自动创建以下目录：

```
backend/
├── data/
│   ├── getthetext.db    # SQLite 数据库
│   └── cache/           # 下载的视频/字幕缓存（按任务 ID 分目录）
```

缓存目录会在任务完成后按策略清理，可在配置中调整 `retention_days`。

---

## 七、常见问题

### Q: ffmpeg 未找到

确保 ffmpeg 已安装且加入 PATH。在终端执行 `ffmpeg -version` 验证。

### Q: B 站链接解析失败

1. 确认已安装 yt-dlp：`pip install yt-dlp`
2. 保持 yt-dlp 为最新版：`pip install -U yt-dlp`
3. 部分视频可能因地区、会员等原因无法解析，可尝试本地上传

### Q: ASR 识别很慢 / 报错

1. 未安装 Whisper 时 ASR 会跳过，仅用字幕
2. 安装后仍慢可选用更小模型：在 `.env` 中设置 `ASR_MODEL=tiny`
3. 若有 NVIDIA GPU，Whisper 会自动使用 CUDA 加速

### Q: 跨域错误 (CORS)

后端已配置允许 `http://localhost:5173`。若前端使用其他端口，需在 `backend/app/main.py` 的 `allow_origins` 中添加。

---

## 八、一键命令汇总

```bash
# 完整启动（分两个终端）
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```
