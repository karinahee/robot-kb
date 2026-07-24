# 定位：
# 1. 本模块只负责「提取 → 清洗纯文本」
# 2. 切分由上层调用 chunk_text 完成

"""
最后选用 pdfminer.six：
- 纯规则驱动，无需深度学习模型，对比 unstructured 安装简单
- 解决了 pymupdf 提取双栏效果不佳的问题

局限性：
- 数学公式（矢量图形）无法提取，为系统 limitation
- 表格只提取纯文本，不还原结构
- 不做标题识别（pdfminer 提取的文本无可靠结构信息）

依赖：pip install pdfminer.six

"""

import re
import uuid
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


def _clean(raw_text: str) -> str:
    """清洗 pdfminer 原始文本，输出干净的纯文本段落。

    清洗规则：
    1. 过滤 (cid:xx) 公式占位符
    2. 过滤字符间有空格的噪声行（如 arXiv 水印 'l u J'）
    3. 过滤双栏布局产生的词级碎块（单词数 ≤ 2 且无 CJK 字符）
    4. 块内软换行合并为空格
    5. 多余空格压缩
    6. 相邻块合并：末尾无句末标点且非标题 → 与下一块拼接
    """
    # 正则预编译
    sentence_end = re.compile(r'[。.!?！？…」』）)>\]】：:；;]$')
    ends_with_hyphen = re.compile(r'-$')
    has_cjk = re.compile(r'[\u4e00-\u9fff]')
    # 标题特征：罗马数字 / 阿拉伯数字开头的全大写短句（如 "I. INTRODUCTION"）
    is_section_heading = re.compile(
        r'^(?:[IVXLCDM]+\.|[0-9]+(?:\.[0-9]+)*\.?)\s+[A-Z\u4e00-\u9fff]'
    )

    # ── 第一步：按空行切块，逐块预处理 ──────────────────────────────────────
    blocks = re.split(r'\n{2,}', raw_text)
    cleaned = []
    for block in blocks:
        # 去掉 (cid:xx) 占位符
        block = re.sub(r'\(cid:\d+\)', '', block)
        # 块内软换行合并（英文加空格，中文直接拼，连字符断词去掉连字符）
        lines_in_block = block.split('\n')
        merged = ''
        for ln in lines_in_block:
            ln = ln.strip()
            if not ln:
                continue
            if not merged:
                merged = ln
            elif ends_with_hyphen.search(merged):
                merged = merged[:-1] + ln
            elif merged and has_cjk.search(merged[-1]):
                merged = merged + ln
            else:
                merged = merged + ' ' + ln
        merged = re.sub(r' {2,}', ' ', merged).strip()
        if not merged:
            continue

        # 过滤噪声行：每个 token 长度 ≤ 2 且整行长度 < 40（如 'l u J'）
        tokens = merged.split()
        if len(tokens) > 1 and all(len(t) <= 2 for t in tokens) and len(merged) < 40:
            continue

        # 过滤双栏碎块：纯英文、词数 ≤ 2、长度 < 25（双栏排版的列间溢出词）
        if not has_cjk.search(merged) and len(tokens) <= 2 and len(merged) < 25:
            continue

        cleaned.append(merged)

    # ── 第二步：合并被排版截断的段落 ─────────────────────────────────────────
    # 判断一个块是否是"完整段落的结尾"：
    #   - 以句末标点结尾，或
    #   - 是标题行（section heading）
    # 否则视为排版截断，与下一块拼接
    result = []
    buf = ''

    for block in cleaned:
        if not buf:
            buf = block
            continue

        # 当前 buf 是否已经"结束"
        buf_is_complete = (
            sentence_end.search(buf)
            or is_section_heading.match(buf)
        )

        if buf_is_complete:
            result.append(buf)
            buf = block
        else:
            # 未结束，拼接下一块
            if ends_with_hyphen.search(buf):
                buf = buf[:-1] + block
            elif buf and has_cjk.search(buf[-1]):
                buf = buf + block
            else:
                buf = buf + ' ' + block

    if buf:
        result.append(buf)

    return '\n\n'.join(result)


def extract_text(pdf_path: str) -> str:
    """从 PDF 文件提取并清洗纯文本。

    Args:
        pdf_path: PDF 文件路径

    Returns:
        清洗后的纯文本字符串，段落间以双换行分隔
    """
    raw = _raw_text(pdf_path)
    return _clean(raw)


def make_doc_id(filename: str) -> str:
    """从文件名生成 doc_id：pdf_清洗名_随机短码。

    每次上传都是全新文档（不自动覆盖），同名/同内容文档由用户自行管理删除。
    """
    name = filename.lower().replace('.pdf', '')
    clean = re.sub(r'[^a-z0-9]', '_', name)[:50]
    return f'pdf_{clean}_{uuid.uuid4().hex[:6]}'
