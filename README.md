# GetTheText

<p align="center">
  <strong>多模态视频文案提取工具</strong><br/>
  从短视频中逆向提取文案，助力知识归纳与总结
</p>

<p align="center">
  <!-- 开源后可取消注释
  <img src="https://img.shields.io/github/license/your-username/GetTheText?style=flat-square" alt="license" />
  <img src="https://img.shields.io/github/stars/your-username/GetTheText?style=flat-square" alt="stars" />
  <img src="https://img.shields.io/github/issues/your-username/GetTheText?style=flat-square" alt="issues" />
  -->
</p>

---

## ✨ 特性

- **多平台支持**：抖音、快手、B 站、小红书等主流短视频平台
- **多模态提取**：字幕解析 + 语音识别 (ASR) + 画面文字识别 (OCR)，多源合并
- **统一入口**：粘贴链接或上传本地视频，自动识别平台并提取
- **可编辑导出**：支持文案编辑、去重、Markdown/TXT 导出
- **本地优先**：ASR/OCR 可完全本地运行，隐私可控

---

## 🎯 适用场景

- 收藏了大量有价值视频，希望提取文案做知识整理
- 学习优质内容的表达方式与结构
- 批量处理视频，建立个人知识库

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（前端）
- ffmpeg
- （可选）NVIDIA GPU，用于加速 ASR/OCR

### 安装与运行

```bash
# 克隆仓库
git clone https://github.com/Alexanderchens/TextGetter.git
cd TextGetter

# 后端
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 前端（另开终端）
cd frontend && npm install && npm run dev
```

> 📖 **完整说明**：环境配置、依赖安装、运行方式及常见问题，请参阅 [环境配置与运行指南](docs/SETUP.md)。

**使用方式**：
- **B 站链接**：粘贴 BV/av 链接，自动下载并提取
- **本地上传**：拖拽或选择视频/图片文件，自动提取文案
- **本地路径**：输入本地文件的完整路径（如 `/Users/xxx/video.mp4`），点击开始提取

---

## 📖 使用方式

1. **链接提取**：在输入框粘贴视频链接（如 B 站、抖音链接），自动识别并提取
2. **本地上传**：上传已下载的视频或图片，适用于平台限制或录屏内容
3. **查看与编辑**：提取结果按来源标注（字幕/语音/OCR），可手动合并润色
4. **导出**：支持导出为 Markdown、TXT 等格式

---

## 📱 支持平台

| 平台     | 链接解析 | 本地文件 | 说明         |
|----------|----------|----------|--------------|
| B 站     | ✅       | ✅       | 支持 BV/av 链接，自动下载字幕 |
| 抖音     | 规划中   | ✅       | 建议本地上传 |
| 快手     | 规划中   | ✅       | -            |
| 小红书   | 规划中   | ✅       | 图文 OCR     |
| 视频号   | -        | ✅       | 需用户录屏   |
| 本地文件 | -        | ✅       | 通用支持     |

---

## 🏗️ 项目结构

```
GetTheText/
├── frontend/          # 统一前端（React/Vue）
├── backend/           # 后端服务（FastAPI）
│   ├── parsers/       # 平台解析器
│   └── extractors/    # ASR、OCR、字幕提取
├── docs/
│   ├── SETUP.md          # 环境配置与运行指南
│   └── ARCHITECTURE.md   # 详细架构设计
└── README.md
```

- [环境配置与运行指南](docs/SETUP.md)
- [架构与模块说明](docs/ARCHITECTURE.md)

---

## ⚙️ 技术栈

| 模块     | 技术                    |
|----------|-------------------------|
| 前端     | React + Vite + Tailwind |
| 后端     | FastAPI (Python)        |
| ASR      | Whisper / FunASR        |
| OCR      | PaddleOCR               |
| 媒体处理 | ffmpeg, yt-dlp          |

---

## 🤝 参与贡献

欢迎提 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建分支 `git checkout -b feature/xxx`
3. 提交修改 `git commit -m 'feat: xxx'`
4. 推送分支 `git push origin feature/xxx`
5. 提交 Pull Request

---

## ⚠️ 免责声明

- 本工具**仅供个人学习与知识整理**，请勿用于商业用途或侵犯他人版权
- 使用前请遵守各平台的用户协议与法律法规
- 提取的内容版权归原作者所有，请勿擅自传播或商用
- 作者不对因使用本工具产生的任何后果负责

---

## 📄 开源协议

[MIT License](LICENSE)
