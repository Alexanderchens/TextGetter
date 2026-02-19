# 02 平台解析器模块 - 详细设计

## 一、概述

**职责**：从用户输入（URL 或本地路径）识别平台类型，获取可处理的媒体资源（视频 URL、图片 URL 等）及元数据。

**输入**：
- 视频链接（含短链、分享链接）
- 本地文件路径

**输出**：`PlatformParseResult`，供下游下载与提取使用。

---

## 二、接口定义

### 2.1 解析结果模型

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class PlatformType(str, Enum):
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    KUAISHOU = "kuaishou"
    XIAOHONGSHU = "xiaohongshu"
    WEIXIN = "weixin"
    LOCAL = "local"
    UNKNOWN = "unknown"

@dataclass
class MediaResource:
    """单个媒体资源（视频或图片）"""
    url: Optional[str] = None      # 远程 URL，local 时为空
    local_path: Optional[str] = None
    media_type: str = "video"      # "video" | "image"
    duration_sec: Optional[float] = None
    subtitle_url: Optional[str] = None  # 外挂字幕 URL（若有）

@dataclass
class PlatformParseResult:
    platform: PlatformType
    media_list: list[MediaResource]  # 支持一个视频多画质、或图文多图
    metadata: dict  # title, author, publish_time 等
    raw_input: str
    error: Optional[str] = None
```

### 2.2 解析器接口

```python
from abc import ABC, abstractmethod

class IPlatformParser(ABC):
    """平台解析器抽象接口"""

    @abstractmethod
    def can_handle(self, input_str: str) -> bool:
        """是否可处理该输入"""
        pass

    @abstractmethod
    def parse(self, input_str: str) -> PlatformParseResult:
        """执行解析，返回媒体资源与元数据"""
        pass

    @property
    @abstractmethod
    def platform(self) -> PlatformType:
        pass
```

---

## 三、平台识别流程

```
输入 input
    │
    ├─► 是否为本地路径？ ──► is_local_file(input)
    │         │
    │         ├─ Yes ──► LocalParser.parse() ──► PlatformParseResult(platform=LOCAL)
    │         │
    │         └─ No ──► 继续
    │
    └─► URL 正则匹配
              │
              for adapter in sorted_adapters:
                  if adapter.can_handle(input):
                      return adapter.parse(input)
              │
              └─► 无匹配 ──► UnsupportedPlatformError
```

### 3.1  platform 匹配规则（优先级从高到低）

| 平台 | 正则模式 | 说明 |
|------|----------|------|
| bilibili | `bilibili\.com`, `b23\.tv`, `bili22\.com` | 短链需先解析跳转 |
| douyin | `douyin\.com`, `iesdouyin\.com`, `v\.douyin\.com` | |
| kuaishou | `kuaishou\.com`, `v\.kuaishou\.com`, `快手` | |
| xiaohongshu | `xiaohongshu\.com`, `xhslink\.com` | |
| weixin | `mp\.weixin\.qq\.com`, `channels\.weixin\.qq\.com` | 公众号 / 视频号 |
| local | 绝对路径或 file:// | |

### 3.2 本地文件判断

```python
import os

def is_local_file(input_str: str) -> bool:
    s = input_str.strip()
    if s.startswith("file://"):
        return True
    if os.path.isabs(s) and os.path.exists(s):
        return True
    # 相对路径且存在
    if os.path.exists(s):
        return True
    return False
```

---

## 四、解析器调度器

```python
class PlatformParserRegistry:
    """解析器注册中心，按优先级调度"""

    def __init__(self):
        self._parsers: list[IPlatformParser] = []

    def register(self, parser: IPlatformParser, priority: int = 0):
        self._parsers.append((priority, parser))
        self._parsers.sort(key=lambda x: -x[0])  # 高优先级在前

    def parse(self, input_str: str) -> PlatformParseResult:
        if is_local_file(input_str):
            return self._local_parser.parse(input_str)

        for _, parser in self._parsers:
            if parser.can_handle(input_str):
                return parser.parse(input_str)

        raise UnsupportedPlatformError(f"不支持的链接或输入: {input_str[:50]}...")
```

---

## 五、各平台解析要点（设计层）

### 5.1 LocalParser

- 输入：本地路径
- 逻辑：校验文件存在、识别视频/图片（扩展名 + magic bytes）
- 输出：`MediaResource(local_path=..., media_type="video"|"image")`

### 5.2 BilibiliParser

- 输入：`https://www.bilibili.com/video/BV1xx411c7mD` 等
- 逻辑：
  - 解析 bv 号
  - 调用 B 站 API 或 yt-dlp 获取视频流 URL、字幕 URL
  - 若有 CC 字幕，填充 `subtitle_url`
- 输出：`media_list` 含一个视频资源，`metadata` 含 title、author、duration

### 5.3 DouyinParser

- 难点：反爬、无官方下载
- 策略：
  - 优先：yt-dlp（若支持）
  - 备选：第三方解析服务（需合规评估）
  - 降级：返回友好提示，建议用户本地上传
- 输出：若有直接 URL 则返回，否则返回 `error` + 建议

### 5.4 XiaohongshuParser

- 输入：笔记链接
- 逻辑：图文为主，解析返回多张图片 URL 或视频 URL
- 输出：`media_list` 可能为多张图片

### 5.5 WeixinParser

- 视频号：封闭，通常无法直接解析
- 策略：仅处理可解析的链接，否则提示用户录屏后本地上传

---

## 六、短链与重定向

部分平台使用短链（如 b23.tv），需先解析真实 URL：

```python
def resolve_short_url(url: str) -> str:
    """追踪 1-2 次重定向，获取最终 URL"""
    # 使用 requests.head 或 requests.get(allow_redirects=True)
    # 注意：部分短链需带 Cookie/User-Agent 才能正确跳转
    pass
```

---

## 七、错误定义

```python
class PlatformParseError(Exception):
    def __init__(self, message: str, platform: Optional[PlatformType] = None):
        self.message = message
        self.platform = platform

class UnsupportedPlatformError(PlatformParseError):
    pass

class ParseNetworkError(PlatformParseError):
    """网络请求失败"""
    pass

class ParseRateLimitError(PlatformParseError):
    """触发平台限流"""
    pass
```

---

## 八、配置项

```yaml
# config/parser.yaml
parser:
  timeout: 30
  max_redirects: 3
  user_agent: "Mozilla/5.0 ..."

  platforms:
    douyin:
      enabled: true
      fallback_to_upload_hint: true
    bilibili:
      enabled: true
      prefer_subtitle: true
```

---

## 九、与下游模块的衔接

- **任务编排器**：调用 `registry.parse(input)`，得到 `PlatformParseResult`
- **媒体下载**：根据 `media_list` 中的 `url` 或 `local_path` 下载/复制到工作目录
- **提取器**：根据 `media_type`、`subtitle_url` 决定是否走字幕/ASR/OCR 分支
