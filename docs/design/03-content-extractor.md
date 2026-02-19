# 03 多模态文案提取器模块 - 详细设计

## 一、概述

**目标**：从视频/图片中提取所有可读文字，多源合并为连贯、去重后的文案。

**流水线**：字幕 → ASR → OCR → 合并去重 →（可选）LLM 清洗

---

## 二、统一数据模型

### 2.1 带时间戳的文本片段

```python
from dataclasses import dataclass
from enum import Enum

class TextSource(str, Enum):
    SUBTITLE = "subtitle"
    ASR = "asr"
    OCR = "ocr"

@dataclass
class TextSegment:
    source: TextSource
    start_time: float   # 秒
    end_time: float     # 秒
    text: str
    confidence: float = 1.0  # 置信度 0-1
    extra: dict = None       # 扩展信息，如 OCR 的 bbox
```

### 2.2 提取器抽象接口

```python
from abc import ABC, abstractmethod

class IContentExtractor(ABC):
    """单模态提取器基类"""

    @abstractmethod
    def extract(self, media_path: str, **kwargs) -> list[TextSegment]:
        """从媒体文件提取文本片段"""
        pass

    @property
    @abstractmethod
    def source_type(self) -> TextSource:
        pass
```

---

## 三、字幕提取器 (SubtitleExtractor)

### 3.1 职责

- 解析外挂字幕（SRT、VTT、ASS）或内嵌字幕
- 输出带时间轴的 `TextSegment(source=SUBTITLE)`

### 3.2 输入来源

- 外挂字幕 URL：下载后解析
- 外挂字幕路径：本地文件
- 内嵌字幕：ffmpeg 提取

### 3.3 实现逻辑

```python
# 伪代码
def extract(self, media_path: str, subtitle_path: Optional[str] = None) -> list[TextSegment]:
    if subtitle_path:
        return self._parse_external_subtitle(subtitle_path)
    # 尝试从视频提取内嵌字幕
    return self._extract_embedded_subtitle(media_path)

def _parse_srt(self, content: str) -> list[TextSegment]:
    # 解析 SRT 格式：序号、时间轴、文本
    # 00:01:23,456 --> 00:01:25,789
    pass
```

### 3.4 支持格式

| 格式 | 扩展名 | 解析库 |
|------|--------|--------|
| SRT | .srt | 自研或 pysrt |
| VTT | .vtt | webvtt-py |
| ASS | .ass | ass 库 |
| 内嵌 | - | ffmpeg -i video.mp4 -map 0:s:0 sub.srt |

---

## 四、ASR 提取器 (ASRExtractor)

### 4.1 职责

从视频/音频中识别语音，输出带时间戳的文本。

### 4.2 技术选型

| 方案 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| Whisper | 多语言、质量高、可本地 | 计算量大 | 通用 |
| FunASR | 中文优化、流式 | 依赖较多 | 纯中文 |
| 阿里云 ASR | 免部署 | 收费、需网络 | 快速验证 |

### 4.3 预处理流程

```
视频 ──► ffmpeg 提取音频 ──► 格式转换 (wav/mp3) ──► 采样率 16k
```

```bash
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav
```

### 4.4 Whisper 调用设计

```python
# 配置：模型大小 base/small/medium/large-v3
# 策略：长音频分段（如 30s）避免 OOM
# 输出：带 timestamp 的 segments

import whisper

def extract(self, media_path: str, model_size: str = "base") -> list[TextSegment]:
    audio_path = self._extract_audio(media_path)
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path, word_timestamps=True, language="zh")
    return self._whisper_to_segments(result)
```

### 4.5 输出转换

Whisper 返回格式：
```python
{
  "segments": [
    {"start": 0.0, "end": 2.5, "text": "你好世界"},
    ...
  ]
}
```
映射为 `TextSegment(source=ASR, start_time, end_time, text)`。

---

## 五、OCR 提取器 (OCRExtractor)

### 5.1 职责

从视频关键帧或图片中识别文字。

### 5.2 流程

```
视频 ──► 按间隔采样帧 ──► 每帧 OCR ──► 按时间戳组装 TextSegment
```

### 5.3 帧采样策略

| 配置 | 间隔 | 适用场景 | 性能 |
|------|------|----------|------|
| 密集 | 0.5s | 字幕变化快 | 耗时长 |
| 标准 | 1s | 默认 | 平衡 |
| 稀疏 | 2s | 纯语音多、文字少 | 快 |

### 5.4 实现要点

```python
def extract(self, media_path: str, interval_sec: float = 1.0) -> list[TextSegment]:
    frames = self._sample_frames(media_path, interval_sec)
    segments = []
    for t, img in frames:
        texts = self._ocr_engine.recognize(img)
        for text in texts:
            segments.append(TextSegment(
                source=TextSource.OCR,
                start_time=t, end_time=t + interval_sec,
                text=text
            ))
    return segments
```

### 5.5 PaddleOCR 使用

```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=True)
result = ocr.ocr(img, cls=True)
# result: [[[box], (text, conf)], ...]
```

### 5.6 去重与合并

同一帧内可能识别出多行，相邻帧可能重复：
- 帧内：按行合并
- 帧间：编辑距离去重，相似度 > 0.9 视为重复

---

## 六、合并器 (SegmentMerger)

### 6.1 职责

将多源 `TextSegment` 按时间轴合并、去重，输出最终文案。

### 6.2 优先级

`字幕 > ASR > OCR`（同时间重叠时保留高优先级）

### 6.3 算法流程

```
1. 按 start_time 排序所有 segment
2. 定义重叠阈值：若 |start_a - start_b| < 0.5 且 文本相似度 > 0.85，视作重复
3. 遍历排序后列表：
   - 若与已选中的 segment 重叠且来源优先级低，跳过
   - 否则加入结果
4. 按时间顺序拼接文本，段落间用换行分隔
```

### 6.4 去重逻辑

```python
def _is_duplicate(seg_a: TextSegment, seg_b: TextSegment) -> bool:
    if abs(seg_a.start_time - seg_b.start_time) > 1.0:
        return False  # 时间差大，不算重复
    sim = text_similarity(seg_a.text, seg_b.text)  # Jaccard / 编辑距离
    return sim > 0.85
```

### 6.5 输出格式

```python
@dataclass
class MergedResult:
    segments: list[TextSegment]  # 去重后的有序片段
    full_text: str               # 拼接后的完整文案
    stats: dict                  # 各来源的占比、字数等
```

---

## 七、LLM 清洗器（可选）

### 7.1 职责

对 `full_text` 做润色、分段、加标题，提升可读性。

### 7.2 提示词示例

```
你是一个文案整理助手。下面是从视频中提取的原始文案，可能含有重复、口语化、断句不当等问题。
请完成：
1. 去除重复和冗余
2. 润色语序，保持原意
3. 按语义分段，每段加简短小标题
4. 输出为 Markdown 格式

原始文案：
---
{full_text}
---
```

### 7.3 接口

```python
def clean_with_llm(text: str, api_key: str = None) -> str:
    # 调用 OpenAI / 本地 Ollama 等
    pass
```

---

## 八、流水线编排

```python
class ExtractPipeline:
    def __init__(self, config: ExtractConfig):
        self.subtitle_extractor = SubtitleExtractor()
        self.asr_extractor = ASRExtractor(config.asr_model)
        self.ocr_extractor = OCRExtractor(config.ocr_interval)
        self.merger = SegmentMerger()

    def run(self, media_path: str, subtitle_path: Optional[str] = None,
            progress_callback=None) -> MergedResult:
        all_segments = []

        # 1. 字幕
        if subtitle_path or self._has_embedded_subtitle(media_path):
            segs = self.subtitle_extractor.extract(media_path, subtitle_path)
            all_segments.extend(segs)
            if progress_callback:
                progress_callback("subtitle", 100)

        # 2. ASR（无字幕或配置要求全量时）
        if self._need_asr(all_segments, media_path):
            segs = self.asr_extractor.extract(media_path)
            all_segments.extend(segs)
            if progress_callback:
                progress_callback("asr", 100)

        # 3. OCR
        segs = self.ocr_extractor.extract(media_path)
        all_segments.extend(segs)
        if progress_callback:
            progress_callback("ocr", 100)

        # 4. 合并
        merged = self.merger.merge(all_segments)
        if progress_callback:
            progress_callback("merging", 100)

        return merged
```

---

## 九、配置项

```yaml
extractor:
  subtitle:
    enabled: true
    formats: [srt, vtt, ass]

  asr:
    provider: whisper  # whisper | funasr | aliyun
    model_size: base
    language: zh

  ocr:
    provider: paddleocr
    interval: 1.0
    skip_if_subtitle_rich: true  # 字幕丰富时可跳过 OCR

  merger:
    overlap_threshold: 0.5
    similarity_threshold: 0.85

  llm_clean:
    enabled: false
    provider: openai  # openai | ollama | ...
```
