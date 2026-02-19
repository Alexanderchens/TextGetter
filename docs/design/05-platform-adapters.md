# 05 平台适配器模块 - 详细设计

## 一、概述

平台适配器是**平台解析器**的具体实现，每个主流平台一个适配器，负责从 URL 获取视频/图片的真实下载地址与元数据。

**与解析器的关系**：`PlatformParser` 负责调度，`PlatformAdapter` 负责具体平台的实现。

---

## 二、适配器接口（与 02 平台解析器 对齐）

```python
class IPlatformAdapter(ABC):
    @abstractmethod
    def can_handle(self, input_str: str) -> bool:
        pass

    @abstractmethod
    def parse(self, input_str: str) -> PlatformParseResult:
        pass

    @property
    def platform(self) -> PlatformType:
        pass
```

---

## 三、B站适配器 (BilibiliAdapter)

### 3.1 支持的 URL 形式

- `https://www.bilibili.com/video/BV1xx411c7mD`
- `https://b23.tv/xxxxx`（短链，需先解析）
- `https://www.bilibili.com/video/av170001`（旧版 av 号）

### 3.2 解析策略

**方案 A：yt-dlp**

```bash
yt-dlp -f "best[height<=720]" --write-subs --sub-lang zh-Hans -o "%(id)s.%(ext)s" <url>
```

- 可获取视频流、字幕（若有 CC）
- 需处理 yt-dlp 输出，解析文件路径

**方案 B：B 站 API（非官方）**

- 解析 bv 号 → 请求 `https://api.bilibili.com/x/web-interface/view?bvid=xxx`
- 获取 cid、title、desc、owner 等
- 再请求 `https://api.bilibili.com/x/player/playurl` 获取视频流
- 字幕：`https://api.bilibili.com/x/player/v2?bvid=xx&cid=xx` 或 CC 接口
- 注意：需 Cookie、Referer，有风控风险

**推荐**：优先 yt-dlp，稳定且维护成本低。

### 3.3 输出示例

```python
PlatformParseResult(
    platform=PlatformType.BILIBILI,
    media_list=[
        MediaResource(
            url="https://xxx.bilivideo.com/xxx.m4s",
            media_type="video",
            duration_sec=300,
            subtitle_url="https://api.bilibili.com/xxx/subtitle"
        )
    ],
    metadata={
        "title": "视频标题",
        "author": "UP 主名",
        "bvid": "BV1xx411c7mD",
        "duration": 300
    },
    raw_input="https://www.bilibili.com/video/BV1xx411c7mD"
)
```

---

## 四、抖音适配器 (DouyinAdapter)

### 4.1 支持的 URL 形式

- `https://www.douyin.com/video/7031234567890`
- `https://v.douyin.com/xxxxx`（短链）
- `https://www.iesdouyin.com/share/video/xxx`

### 4.2 难点

- 强反爬：签名、Cookie、设备指纹
- 水印、无官方下载入口
- 链接经常变动，需持续维护

### 4.3 策略

| 方案 | 可行性 | 说明 |
|------|--------|------|
| yt-dlp | 视版本而定 | 部分版本支持 douyin，可能随时失效 |
| 第三方解析 API | 可用 | 需合规评估，可能收费 |
| 本地上传 | 推荐 | 用户自行下载后上传，100% 可行 |

**实现建议**：
1. 先尝试 yt-dlp，成功则返回
2. 失败则返回 `PlatformParseResult` 带 `error="平台限制，建议下载视频后本地上传"`
3. 配置项控制是否启用第三方 API（若引入）

### 4.4 短链解析

```python
# v.douyin.com 会 302 到 iesdouyin.com
# 需带 User-Agent、Cookie 模拟移动端
```

---

## 五、快手适配器 (KuaishouAdapter)

### 5.1 支持的 URL 形式

- `https://www.kuaishou.com/short-video/xxx`
- `https://v.kuaishou.com/xxx`

### 5.2 策略

类似抖音，优先 yt-dlp，备选本地上传提示。
快手部分内容 yt-dlp 支持较好，可优先尝试。

---

## 六、小红书适配器 (XiaohongshuAdapter)

### 6.1 内容类型

- 图文笔记：多张图片 + 正文
- 视频笔记：单个视频

### 6.2 URL 形式

- `https://www.xiaohongshu.com/explore/xxx`
- `https://xhslink.com/xxxxx`（短链）

### 6.3 解析要点

- 图文：需获取图片 URL 列表，走 OCR 流程
- 视频：获取视频 URL，走字幕/ASR/OCR
- 正文：若页面可爬，可直接提取，减少 OCR 依赖
- 反爬：登录态、签名，难度较高

**输出**：
```python
# 图文
media_list = [
    MediaResource(url="https://...", media_type="image"),
    MediaResource(url="https://...", media_type="image"),
]
metadata = {"title": "笔记标题", "desc": "正文（若能获取）"}

# 视频
media_list = [MediaResource(url="...", media_type="video")]
```

---

## 七、微信视频号适配器 (WeixinChannelsAdapter)

### 7.1 现状

视频号封闭，无公开 API，链接通常需在微信内打开，外部分析难度极大。

### 7.2 策略

- **不实现链接解析**，或返回明确错误
- **仅支持本地上传**：用户录屏/下载后上传
- 平台识别：若输入为本地文件，`platform=LOCAL`，无需专门 Weixin 适配器

---

## 八、本地文件适配器 (LocalAdapter)

### 8.1 职责

处理用户上传的本地视频/图片，校验格式并返回 `MediaResource(local_path=...)`。

### 8.2 逻辑

```python
def parse(self, input_str: str) -> PlatformParseResult:
    path = self._resolve_path(input_str)  # 处理 file:// 等
    if not os.path.exists(path):
        return PlatformParseResult(..., error="文件不存在")

    media_type = self._detect_media_type(path)  # video | image
    return PlatformParseResult(
        platform=PlatformType.LOCAL,
        media_list=[MediaResource(local_path=path, media_type=media_type)],
        metadata={"filename": os.path.basename(path)},
        raw_input=input_str
    )
```

### 8.3 支持的格式

**视频**：mp4, mkv, webm, mov, avi, flv  
**图片**：jpg, jpeg, png, webp, gif（多图可批量）

---

## 九、适配器注册与优先级

```python
registry = PlatformParserRegistry()
registry.register(LocalAdapter(), priority=100)   # 最高，先判断本地
registry.register(BilibiliAdapter(), priority=90)
registry.register(DouyinAdapter(), priority=80)
registry.register(KuaishouAdapter(), priority=70)
registry.register(XiaohongshuAdapter(), priority=60)
# WeixinAdapter 可选，或仅返回 unsupported
```

---

## 十、通用能力抽取

### 10.1 短链解析工具

```python
def resolve_redirect(url: str, max_hops: int = 3) -> str:
    """追踪重定向，返回最终 URL"""
    pass
```

### 10.2 HTTP 请求封装

- 统一 User-Agent、超时
- 支持代理配置（按平台可选）
- Cookie 管理（若需登录态）

### 10.3 限流

按平台、按 IP 限制请求频率，避免封禁。

---

## 十一、配置模板

```yaml
adapters:
  bilibili:
    enabled: true
    use_ytdlp: true
    # api_fallback: false

  douyin:
    enabled: true
    use_ytdlp: true
    fallback_message: "平台限制，请下载后本地上传"

  xiaohongshu:
    enabled: true
    # 图文需单独处理 OCR 流程
```
