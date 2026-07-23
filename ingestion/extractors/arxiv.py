# arXiv 论文提取模块
#
# 支持两种使用方式：
#   1. 关键词搜索（search_arxiv / fetch_and_chunk）
#   2. URL 直接解析（extract_by_url）：用户粘贴 arXiv abs/pdf 链接直接入库
#
# 依赖：
#   pip install arxiv requests
#   以及 pdfminer.six（由 pdf.py 使用）

import os
import re
import tempfile
import requests
import arxiv

from .pdf import extract_text, make_doc_id
from ..chunkers._split import chunk_text


def search_arxiv(query: str, max_results: int = 1) -> list[dict]:
    """通过 arXiv API 搜索论文，返回元信息列表。

    Args:
        query:       搜索关键词
        max_results: 最多返回几篇

    Returns:
        元信息列表，每项包含：
            arxiv_id, title, authors, published, categories, pdf_url
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    results = []
    for result in client.results(search):
        results.append({
            'arxiv_id':   result.entry_id.split('/')[-1],
            'title':      result.title,
            'authors':    [a.name for a in result.authors],
            'published':  str(result.published.date()),
            'categories': result.categories,
            'pdf_url':    result.pdf_url,
        })
    return results


def download_pdf(pdf_url: str, save_path: str) -> str:
    """下载 PDF 文件到本地。

    Args:
        pdf_url:   arXiv PDF 下载地址
        save_path: 本地保存路径

    Returns:
        保存后的文件路径
    """
    if os.path.exists(save_path):
        print(f'文件已存在，跳过下载：{save_path}')
        return save_path
    r = requests.get(pdf_url, timeout=60)
    r.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(r.content)
    print(f'下载完成：{save_path}（{len(r.content):,} 字节）')
    return save_path


def fetch_and_chunk(
    query: str,
    save_dir: str = '.',
    max_results: int = 1,
    target_chars: int = 500,
    min_chars: int = 80,
    max_chars: int = 1000,
) -> tuple[list[dict], list[dict]]:
    """搜索 arXiv → 下载 PDF → 转 Markdown → chunk_markdown 切分，一步完成。

    Args:
        query:       搜索关键词
        save_dir:    PDF 下载保存目录
        max_results: 最多处理几篇

    Returns:
        (meta_list, all_chunks)
        meta_list:  元信息列表
        all_chunks: 所有论文的 chunk 合并列表
    """
    meta_list = search_arxiv(query, max_results=max_results)
    all_chunks = []

    for meta in meta_list:
        arxiv_id = meta['arxiv_id']
        pdf_path = os.path.join(save_dir, f'arxiv_{arxiv_id}.pdf')
        download_pdf(meta['pdf_url'], pdf_path)

        doc_id = f'arxiv_{arxiv_id}'
        text = extract_text(pdf_path)
        chunks = chunk_text(
            text, doc_id=doc_id,
            target_chars=target_chars,
            min_chars=min_chars,
            max_chars=max_chars,
        )
        all_chunks.extend(chunks)
        print(f'[{arxiv_id}] 切分出 {len(chunks)} 个 chunk')

    return meta_list, all_chunks


# ── URL 直接解析（场景 A）──────────────────────────────────────────────────────

_ARXIV_URL_PATTERN = re.compile(
    r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)',
    re.IGNORECASE,
)


def parse_arxiv_url(url: str) -> str:
    """从 arXiv URL 提取 arxiv_id。

    支持格式：
        https://arxiv.org/abs/2004.00784
        https://arxiv.org/pdf/2004.00784
        https://arxiv.org/abs/2004.00784v2

    Returns:
        arxiv_id，如 "2004.00784"

    Raises:
        ValueError: URL 无法解析
    """
    m = _ARXIV_URL_PATTERN.search(url)
    if not m:
        raise ValueError(f'无法解析 arXiv URL：{url}')
    return m.group(1)


def extract_by_url(
    url: str,
    target_chars: int = 500,
    min_chars: int = 80,
    max_chars: int = 1000,
) -> tuple[str, str, list[dict], dict]:
    """从 arXiv URL 一步完成：解析 → 下载 PDF → 提取文本 → 切分。

    Args:
        url:          arXiv abs 或 pdf 链接
        target_chars: chunk 目标字符数
        min_chars:    chunk 最小字符数
        max_chars:    chunk 最大字符数

    Returns:
        (doc_id, content, chunks, meta)
        doc_id:  文档唯一标识
        content: 清洗后的完整文本
        chunks:  切分结果列表
        meta:    元信息 dict（arxiv_id, title, authors, published, pdf_url）
    """
    arxiv_id = parse_arxiv_url(url)
    doc_id = f'arxiv_{arxiv_id.replace(".", "_").replace("/", "_")}'

    # 获取元信息
    client = arxiv.Client()
    search = arxiv.Search(id_list=[arxiv_id])
    results = list(client.results(search))
    if not results:
        raise ValueError(f'arXiv 上找不到论文：{arxiv_id}')

    r = results[0]
    meta = {
        'arxiv_id':   arxiv_id,
        'title':      r.title,
        'authors':    [a.name for a in r.authors],
        'published':  str(r.published.date()),
        'categories': r.categories,
        'pdf_url':    r.pdf_url,
    }

    # 下载 PDF 到临时文件
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        tmp_path = f.name
    try:
        download_pdf(r.pdf_url, tmp_path)
        content = extract_text(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not content.strip():
        raise ValueError('PDF 提取结果为空')

    chunks = chunk_text(
        content, doc_id=doc_id,
        target_chars=target_chars,
        min_chars=min_chars,
        max_chars=max_chars,
    )
    return doc_id, content, chunks, meta
