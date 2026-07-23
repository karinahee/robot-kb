# 底层切分工具（内部私有，供 chunk.py 调用）
#
# 不直接处理 extractor 输出。
# 当 chunk_markdown 遇到超过 max_chars 的超长 section 时，
# 调用本模块的 chunk_text 做句级二次切分。
#
# 策略：
#   第一层：按「连续两个以上换行（空行）」切段落，累积到接近 target_chars 才提交
#   第二层：若单段落超过 max_chars，按句末标点二次切分为句子级 chunk
#   过滤：低于 min_chars 的碎片合并到前一 chunk 或丢弃

import re


def split_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """按空行切段落，返回 (段落起始偏移, 段落结束偏移, 段落内容) 列表。

    end 延伸到下一段落起始，将段间空白纳入当前段落范围，
    避免字符偏移出现缺口，确保 char_start/char_end 连续覆盖原文。
    """
    raw_segments = list(re.finditer(r'(?:(?!\n\n).)+', text, re.DOTALL))
    paragraphs = []
    for i, m in enumerate(raw_segments):
        content = m.group().strip()
        if not content:
            continue
        p_start = m.start()
        p_end = raw_segments[i + 1].start() if i + 1 < len(raw_segments) else len(text)
        paragraphs.append((p_start, p_end, content))
    return paragraphs


def split_sentences(text: str) -> list[tuple[int, int, str]]:
    """按中英文句末标点切句，返回 (起始偏移, 结束偏移, 句子文本) 列表。

    末尾无标点的剩余文字作为最后一个句子保留。
    """
    sentences = []
    pattern = re.compile(r'[^。！？.!?]*[。！？.!?]+')
    last_end = 0
    for m in pattern.finditer(text):
        sentences.append((m.start(), m.end(), m.group()))
        last_end = m.end()
    if last_end < len(text) and text[last_end:].strip():
        sentences.append((last_end, len(text), text[last_end:]))
    return sentences


def chunk_text(
    text: str,
    doc_id: str,
    target_chars: int = 500,
    min_chars: int = 80,
    max_chars: int = 1000,
) -> list[dict]:
    """将纯文本切分为 chunk 列表（供 chunk_markdown 调用的兜底切分）。

    Args:
        text:         原始文本
        doc_id:       文档唯一标识符
        target_chars: 每个 chunk 的目标字符数（软上限）
        min_chars:    低于此值视为碎片，合并或丢弃
        max_chars:    单 chunk 硬上限，超过则触发句级二次切分

    Returns:
        chunk 列表，每个 chunk 包含：
            doc_id, chunk_index, char_start, char_end, chunk_text, char_len
    """
    paragraphs = split_paragraphs(text)
    chunks = []
    buf_start = buf_end = None
    chunk_index = 0

    def flush(b_start, b_end):
        nonlocal chunk_index
        if b_start is None:
            return
        chunk_str = text[b_start:b_end]
        if not chunk_str.strip():
            return
        if len(chunk_str.strip()) < min_chars and chunks:
            # 碎片合并到前一 chunk
            prev = chunks[-1]
            prev['char_end'] = b_end
            prev['chunk_text'] = text[prev['char_start']:b_end]
            prev['char_len'] = len(prev['chunk_text'])
            return
        if len(chunk_str.strip()) < min_chars and not chunks:
            return  # 首个 chunk 太短，丢弃
        chunks.append({
            'doc_id': doc_id,
            'chunk_index': chunk_index,
            'char_start': b_start,
            'char_end': b_end,
            'chunk_text': chunk_str,
            'char_len': len(chunk_str),
        })
        chunk_index += 1

    def flush_or_split(b_start, b_end):
        # 提交前检查是否超过 max_chars，超过则先按句子切分再提交。
        if b_start is None:
            return
        chunk_str = text[b_start:b_end]
        if not chunk_str.strip():
            return
        if len(chunk_str) <= max_chars:
            flush(b_start, b_end)
            return
        sentences = split_sentences(chunk_str)
        if not sentences:
            flush(b_start, b_end)
            return
        sub_buf_start = sub_buf_end = None
        for s_start, s_end, _ in sentences:
            abs_s_start = b_start + s_start
            abs_s_end = b_start + s_end
            if sub_buf_start is None:
                sub_buf_start, sub_buf_end = abs_s_start, abs_s_end
                continue
            if (sub_buf_end - sub_buf_start) >= target_chars:
                flush(sub_buf_start, sub_buf_end)
                sub_buf_start, sub_buf_end = abs_s_start, abs_s_end
            else:
                sub_buf_end = abs_s_end
        flush(sub_buf_start, sub_buf_end)

    for p_start, p_end, _seg in paragraphs:
        if buf_start is None:
            buf_start, buf_end = p_start, p_end
            continue
        if (buf_end - buf_start) >= target_chars:
            flush_or_split(buf_start, buf_end)
            buf_start, buf_end = p_start, p_end
        else:
            buf_end = p_end
    flush_or_split(buf_start, buf_end)
    return chunks
