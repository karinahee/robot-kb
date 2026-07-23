"""
chunk 校验模块

用 char_start/char_end 从原始文本重新切片，与存储的 chunk_text 逐字比对。
pass=True 才能进入 Embedding，否则说明切分偏移有 bug。

所有格式（PDF / 网页 / Markdown）均先转为 Markdown 字符串，
再由 chunk_markdown 统一切分，char_start/char_end 均为相对于该
Markdown 字符串的偏移，校验方式一致。
"""


def validate_chunks(text: str, chunks: list[dict]) -> dict:
    """
    校验 chunk 列表的 char_start/char_end 是否与 chunk_text 一致。

    Args:
        text:   原始文本（chunk 是从这个文本切出来的）
        chunks: chunk 列表

    Returns:
        {
            'total_chunks':   int,
            'mismatch_count': int,
            'mismatches':     list,   # 有问题的 chunk 摘要
            'pass':           bool,
        }
    """
    mismatches = []
    for c in chunks:
        rebuilt = text[c['char_start']:c['char_end']]
        if rebuilt != c['chunk_text']:
            mismatches.append({
                'chunk_index':    c['chunk_index'],
                'stored_preview': c['chunk_text'][:50],
                'rebuilt_preview': rebuilt[:50],
            })
    return {
        'total_chunks':   len(chunks),
        'mismatch_count': len(mismatches),
        'mismatches':     mismatches,
        'pass':           len(mismatches) == 0,
    }
