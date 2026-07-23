# 统一切分入口（对外接口）
#
# 所有格式（PDF / 网页 / GitHub Markdown / arXiv）均先由各自的 extractor
# 转换为 Markdown 字符串，再统一调用本模块的 chunk_markdown 完成切分。
#
# 策略：
#   优先按 1~3 级标题（# / ## / ###）切 section
#   正文 < min_chars 的 section 过滤掉（空标题节）
#   超长 section 调用 _split.chunk_text 做句级二次细切

import re
from ._split import chunk_text


def chunk_markdown(
    text: str,
    doc_id: str,
    target_chars: int = 500,
    min_chars: int = 80,
    max_chars: int = 1000,
) -> list[dict]:
    """将 Markdown 文本按标题层级切分为 chunk 列表。

    Args:
        text:         Markdown 原始文本
        doc_id:       文档唯一标识符
        target_chars: 超长 section 细切时的目标字符数
        min_chars:    section 正文低于此值则过滤
        max_chars:    单 chunk 硬上限

    Returns:
        chunk 列表，每个 chunk 包含：
            doc_id, chunk_index, char_start, char_end, chunk_text, char_len
    """
    sections = re.split(r'(?m)^(?=#{1,3} )', text)
    all_chunks = []
    search_start = 0

    for section in sections:
        if not section.strip():
            search_start += len(section)
            continue

        lines = section.splitlines()
        body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''

        # 过滤空标题节（只有标题行、无正文）
        if len(body) < min_chars and len(section.strip()) < min_chars:
            search_start += len(section)
            continue

        sec_start = text.find(section, search_start)
        sec_end = sec_start + len(section)
        search_start = sec_end

        if len(section) <= max_chars:
            all_chunks.append({
                'doc_id': doc_id,
                'chunk_index': len(all_chunks),
                'char_start': sec_start,
                'char_end': sec_end,
                'chunk_text': section,
                'char_len': len(section),
            })
        else:
            # 超长 section 细切
            sub_chunks = chunk_text(
                section, doc_id=doc_id,
                target_chars=target_chars,
                min_chars=min_chars,
                max_chars=max_chars,
            )
            for sc in sub_chunks:
                sc['char_start'] += sec_start
                sc['char_end'] += sec_start
                sc['chunk_text'] = text[sc['char_start']:sc['char_end']]
                sc['char_len'] = len(sc['chunk_text'])
                sc['chunk_index'] = len(all_chunks)
                all_chunks.append(sc)

    return all_chunks
