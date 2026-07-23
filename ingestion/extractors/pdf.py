# 最后选用 pdfminer.six：
# - 纯规则驱动，无需深度学习模型，安装简单
# - 解决了 pymupdf 提取双栏效果不佳的问题
#
# 已知局限：
# - 数学公式（矢量图形）无法提取，为系统 limitation
# - 表格只提取纯文本，不还原结构
#
# 依赖：pip install pdfminer.six
#
# 架构定位：
# - 本模块只负责「提取 → 转 Markdown」
# - 切分统一由上层调用 chunk_markdown 完成

import re
from io import StringIO
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams


def _raw_text(pdf_path: str) -> str:
    """用 pdfminer.six 提取 PDF 原始文本。"""
    output = StringIO()
    with open(pdf_path, 'rb') as f:
        extract_text_to_fp(
            f, output,
            laparams=LAParams(line_margin=0.5, word_margin=0.1),
            output_type='text',
            codec='utf-8',
        )
    return output.getvalue()


def _to_markdown(raw_text: str) -> str:
    """把 pdfminer 输出的原始文本转换为简单 Markdown。

    规则：
    - 连续多个换行 → 段落分隔（空行）
    - 块内断行合并为空格（处理 PDF 软换行）
    - 疑似标题行（短行、首字母大写、无句末标点）→ 加 ## 前缀
    """
    # 按空行切块
    blocks = re.split(r'\n{2,}', raw_text)
    md_parts = []
    for block in blocks:
        # 块内换行合并为空格
        merged = re.sub(r'(?<!\n)\n(?!\n)', ' ', block).strip()
        merged = re.sub(r' {2,}', ' ', merged)
        if not merged:
            continue
        # 疑似标题：长度 < 80、不以句末标点结尾、非纯数字/符号
        is_heading = (
            len(merged) < 80
            and not re.search(r'[。.!?！？]$', merged)
            and re.search(r'[A-Za-z\u4e00-\u9fff]', merged)
        )
        if is_heading:
            md_parts.append(f'## {merged}')
        else:
            md_parts.append(merged)
    return '\n\n'.join(md_parts)


def extract_to_markdown(pdf_path: str) -> str:
    """从 PDF 文件提取文本，转换为 Markdown 字符串。

    Args:
        pdf_path: PDF 文件路径

    Returns:
        Markdown 格式的文本字符串
    """
    raw = _raw_text(pdf_path)
    return _to_markdown(raw)


def make_doc_id(filename: str) -> str:
    """从文件名生成 doc_id，去掉特殊字符，加 pdf_ 前缀。"""
    name = filename.lower().replace('.pdf', '')
    clean = re.sub(r'[^a-z0-9]', '_', name)[:50]
    return f'pdf_{clean}'
