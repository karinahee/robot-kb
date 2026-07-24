# 网页正文提取模块
#
# 下载 HTML → 转换为 Markdown → 统一由 chunk_markdown 切分。
#
# 已知局限：
#   - 部署了 Anubis / Cloudflare 等反爬保护的网站无法直接抓取
#   - 建议使用无反爬保护的页面（Wikipedia、ROS Wiki、官方文档镜像等）
#
# 依赖：
#   pip install requests beautifulsoup4 lxml

import re
import uuid
import requests
from bs4 import BeautifulSoup, Tag

from ..chunkers.chunk import chunk_markdown


# HTML 标签 → Markdown 转换规则
_HEADING_MAP = {'h1': '#', 'h2': '##', 'h3': '###', 'h4': '####'}


def _elem_to_md(elem: Tag) -> str:
    """把单个 BeautifulSoup 元素转换为对应的 Markdown 片段。"""
    tag = elem.name
    text = elem.get_text(separator=' ', strip=True)
    if not text:
        return ''
    if tag in _HEADING_MAP:
        return f'{_HEADING_MAP[tag]} {text}'
    if tag == 'li':
        return f'- {text}'
    if tag == 'pre':
        return f'```\n{text}\n```'
    return text  # p / 其他块级元素直接返回文本


def extract_to_markdown(url: str) -> str:
    """下载网页并将正文转换为 Markdown 字符串。

    Args:
        url: 网页 URL

    Returns:
        Markdown 格式的正文文本
    """
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding

    soup = BeautifulSoup(resp.text, 'lxml')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()

    content = soup.find('main') or soup.find('article') or soup.find('body')
    if content is None:
        return ''

    parts = []
    for elem in content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'pre']):
        md = _elem_to_md(elem)
        if md:
            parts.append(md)

    return '\n\n'.join(parts)


def make_doc_id(url: str) -> str:
    """从 URL 生成 doc_id：web_清洗名_随机短码。

    每次添加都是全新文档（不自动覆盖），重复 URL 由用户自行管理删除。
    """
    clean = re.sub(r'[^a-z0-9]', '_', url.lower())[:60]
    return f'web_{clean}_{uuid.uuid4().hex[:6]}'


def fetch_and_chunk(
    url: str,
    target_chars: int = 500,
    min_chars: int = 80,
    max_chars: int = 1000,
) -> tuple[str, list[dict], str]:
    """从 URL 一步完成：下载 → 转 Markdown → chunk_markdown 切分。

    Args:
        url: 网页 URL

    Returns:
        (markdown_text, chunks, doc_id)
        doc_id 与 chunks 内使用的一致，调用方不要再自行生成。
    """
    md_text = extract_to_markdown(url)
    doc_id = make_doc_id(url)
    chunks = chunk_markdown(
        md_text, doc_id=doc_id,
        target_chars=target_chars,
        min_chars=min_chars,
        max_chars=max_chars,
    )
    return md_text, chunks, doc_id
