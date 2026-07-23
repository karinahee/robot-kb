# arXiv 论文提取模块
#
# 通过 arXiv API 搜索论文，下载 PDF，
# 提取文本转为 Markdown，统一由 chunk_markdown 切分。
#
# 依赖：
#   pip install arxiv requests
#   以及 pdfminer.six（由 pdf.py 使用）

import os
import requests
import arxiv

from .pdf import extract_to_markdown, make_doc_id
from ..chunkers.chunk import chunk_markdown


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
        md_text = extract_to_markdown(pdf_path)
        chunks = chunk_markdown(
            md_text, doc_id=doc_id,
            target_chars=target_chars,
            min_chars=min_chars,
            max_chars=max_chars,
        )
        all_chunks.extend(chunks)
        print(f'[{arxiv_id}] 切分出 {len(chunks)} 个 chunk')

    return meta_list, all_chunks
