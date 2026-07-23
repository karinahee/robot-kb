# GitHub / Gitee 仓库 Markdown 提取模块
#
# 两种使用方式：
#   fetch_and_chunk()      每个 .md 文件独立 doc_id（原有，保留）
#   fetch_and_chunk_repo() 整个仓库合并为一篇文档（pipeline 使用）
#
# 依赖：
#   pip install requests

import re
import time
import requests

from ..chunkers.chunk import chunk_markdown


def parse_github_url(url: str) -> tuple[str, str]:
    # 从 GitHub 仓库 URL 解析 owner 和 repo。
    m = re.search(r'github\.com/([^/]+)/([^/]+)', url)
    if not m:
        raise ValueError(f'无法从链接解析 owner/repo：{url}')
    return m.group(1), m.group(2).rstrip('/')


def parse_gitee_url(url: str) -> tuple[str, str]:
    # 从 Gitee 仓库 URL 解析 owner 和 repo。
    m = re.search(r'gitee\.com/([^/]+)/([^/]+)', url)
    if not m:
        raise ValueError(f'无法从链接解析 owner/repo：{url}')
    return m.group(1), m.group(2).rstrip('/')


def fetch_md_files(
    owner: str,
    repo: str,
    platform: str = 'github',
    path: str = '',
) -> list[dict]:
    # 递归遍历 GitHub 或 Gitee 仓库，返回所有 .md 文件的路径和下载地址。
    #
    # Args:
    #     owner:    仓库所有者
    #     repo:     仓库名称
    #     platform: 'github' 或 'gitee'
    #     path:     子目录路径（递归时使用）
    #
    # Returns:
    #     [{'path': ..., 'download_url': ...}, ...]
    if platform == 'github':
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    else:
        api_url = f'https://gitee.com/api/v5/repos/{owner}/{repo}/contents/{path}'

    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    items = resp.json()

    md_files = []
    for item in items:
        if item['type'] == 'file' and item['name'].lower().endswith('.md'):
            if platform == 'github':
                download_url = item['download_url']
            else:
                download_url = f'https://gitee.com/{owner}/{repo}/raw/master/{item["path"]}'
            md_files.append({'path': item['path'], 'download_url': download_url})
        elif item['type'] == 'dir':
            time.sleep(0.3)  # 避免触发 API 限流
            md_files.extend(fetch_md_files(owner, repo, platform, item['path']))

    return md_files


def fetch_and_chunk(
    url: str,
    platform: str = 'github',
    target_chars: int = 500,
    min_chars: int = 80,
    max_chars: int = 1000,
) -> tuple[list[dict], list[dict]]:
    # 从仓库 URL 一步完成：解析 → 获取文件列表 → 下载 → 切分。
    #
    # Args:
    #     url:      GitHub 或 Gitee 仓库链接
    #     platform: 'github' 或 'gitee'
    #
    # Returns:
    #     (md_files, all_chunks)
    #     md_files:   .md 文件信息列表
    #     all_chunks: 所有文件的 chunk 合并列表
    if platform == 'github':
        owner, repo = parse_github_url(url)
    else:
        owner, repo = parse_gitee_url(url)

    print(f'解析结果：owner={owner}, repo={repo}')
    print('正在递归遍历仓库...')
    md_files = fetch_md_files(owner, repo, platform=platform)
    print(f'找到 {len(md_files)} 个 .md 文件')

    all_chunks = []
    for md_file in md_files:
        resp = requests.get(md_file['download_url'], timeout=30)
        md_text = resp.text
        if not md_text.strip():
            continue
        safe_path = md_file['path'].replace('/', '_').replace('.', '_').lower()
        doc_id = f'{platform}_{repo}_{safe_path}'
        chunks = chunk_markdown(
            md_text, doc_id=doc_id,
            target_chars=target_chars,
            min_chars=min_chars,
            max_chars=max_chars,
        )
        all_chunks.extend(chunks)
        print(f'  {md_file["path"]:45s} -> {len(chunks):3d} chunks')

    return md_files, all_chunks


# ── 仓库合并入库（一个仓库 = 一篇文档）─────────────────────────────────────────

def fetch_and_chunk_repo(
    url: str,
    platform: str = 'github',
    target_chars: int = 500,
    min_chars: int = 80,
    max_chars: int = 1000,
) -> tuple[str, str, list[dict]]:
    """将整个仓库的所有 .md 文件合并为一篇文档，统一切分。

    所有 chunks 共用一个仓库级 doc_id。
    每个 chunk 的 metadata 中保留 source_path，用于引用展示。

    Args:
        url:      GitHub 或 Gitee 仓库链接
        platform: 'github' 或 'gitee'

    Returns:
        (doc_id, content, chunks)
        doc_id:  仓库级文档 ID
        content: 所有 .md 文件的合并文本（文件间以分隔符隔开）
        chunks:  切分结果，每条 metadata 含 source_path
    """
    if platform == 'github':
        owner, repo = parse_github_url(url)
    else:
        owner, repo = parse_gitee_url(url)

    doc_id = f'{platform}_{owner}_{repo}'.lower()

    md_files = fetch_md_files(owner, repo, platform=platform)
    if not md_files:
        raise ValueError(f'仓库中没有找到 .md 文件：{url}')

    # 合并所有文件内容，记录每个文件在合并文本中的偏移范围
    parts = []
    file_ranges = []  # [(source_path, file_start, file_end)]
    offset = 0

    for md_file in md_files:
        resp = requests.get(md_file['download_url'], timeout=30)
        resp.raise_for_status()
        md_text = resp.text.strip()
        if not md_text:
            continue

        separator = f'\n\n<!-- file: {md_file["path"]} -->\n\n'
        parts.append(separator + md_text)
        file_start = offset + len(separator)
        file_end = file_start + len(md_text)
        file_ranges.append((md_file['path'], file_start, file_end))
        offset = file_end

    content = ''.join(parts)

    # 对合并文本统一切分
    raw_chunks = chunk_markdown(
        content, doc_id=doc_id,
        target_chars=target_chars,
        min_chars=min_chars,
        max_chars=max_chars,
    )

    # 为每个 chunk 注入 source_path（找到 char_start 属于哪个文件）
    def _find_source_path(char_start: int) -> str:
        for path, f_start, f_end in file_ranges:
            if f_start <= char_start < f_end:
                return path
        return file_ranges[-1][0] if file_ranges else ''

    for chunk in raw_chunks:
        chunk['metadata'] = {'source_path': _find_source_path(chunk['char_start'])}

    return doc_id, content, raw_chunks
