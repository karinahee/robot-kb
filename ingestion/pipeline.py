# 统一入库编排层
#
# 对外接口：
#   ingest_pdf(path, title, on_progress)
#   ingest_web(url, title, on_progress)
#   ingest_arxiv(url, title, on_progress)
#   ingest_github(url, title, on_progress)
#
# 职责：
#   调用 extractor → chunker → embedding → store
#   管理入库状态（processing / ready / failed）
#   覆盖入库：先删旧 chunks，再写新 chunks
#   通过 on_progress 回调通知 UI 进度

import hashlib
import tempfile
import os
from typing import Callable

from .embedding import embed
from . import store
from .chunkers._split import chunk_text
from .chunkers.chunk import chunk_markdown

ProgressCallback = Callable[[str, float], None]  # (stage, 0.0~1.0)


def _notify(cb: ProgressCallback | None, stage: str, progress: float) -> None:
    if cb:
        cb(stage, progress)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _run_pipeline(
    doc_id: str,
    title: str,
    source_type: str,
    source_url: str,
    content: str,
    chunks: list[dict],
    metadata: dict | None = None,
    on_progress: ProgressCallback | None = None,
) -> None:
    """通用入库流程：upsert document → embed → 删旧 chunks → 写新 chunks。

    Raises:
        Exception: 任何步骤失败都会将 status 置为 failed 后抛出
    """
    try:
        # 1. upsert document（status=processing）
        _notify(on_progress, '写入文档记录', 0.1)
        store.upsert_document(
            doc_id=doc_id,
            title=title,
            source_type=source_type,
            source_url=source_url,
            content=content,
            metadata=metadata or {},
            status='processing',
        )

        # 2. embedding
        _notify(on_progress, f'向量化 {len(chunks)} 个 chunk', 0.3)
        texts = [c['chunk_text'] for c in chunks]
        vectors = embed(texts)
        if len(vectors) != len(chunks):
            raise ValueError(f'向量数量({len(vectors)})与 chunk 数量({len(chunks)})不一致')

        for chunk, vec in zip(chunks, vectors):
            chunk['embedding'] = vec

        # 3. 覆盖入库：先删旧 chunks
        _notify(on_progress, '清理旧数据', 0.7)
        store.delete_chunks_by_doc(doc_id)

        # 4. 写入新 chunks
        _notify(on_progress, '写入 chunks', 0.8)
        store.upsert_chunks(chunks)

        # 5. 标记完成
        _notify(on_progress, '完成', 1.0)
        store.update_document_status(doc_id, 'ready')

    except Exception as e:
        store.update_document_status(doc_id, 'failed', str(e))
        raise


# ── PDF ───────────────────────────────────────────────────────────────────────

def ingest_pdf(
    path: str,
    title: str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """从本地 PDF 文件入库。

    Args:
        path:        PDF 文件路径
        title:       文档标题（用户填写）
        on_progress: 进度回调

    Returns:
        doc_id
    """
    from .extractors.pdf import extract_text, make_doc_id

    _notify(on_progress, '提取 PDF 文本', 0.05)
    content = extract_text(path)
    if not content.strip():
        raise ValueError('PDF 提取结果为空')

    doc_id = make_doc_id(os.path.basename(path))
    filename = os.path.basename(path)

    _notify(on_progress, '切分文本', 0.15)
    chunks = chunk_text(content, doc_id=doc_id)
    if not chunks:
        raise ValueError('切分结果为空，文档内容可能过短')

    _run_pipeline(
        doc_id=doc_id,
        title=title,
        source_type='pdf',
        source_url=filename,
        content=content,
        chunks=chunks,
        metadata={'filename': filename},
        on_progress=on_progress,
    )
    return doc_id


def ingest_pdf_upload(
    file_bytes: bytes,
    filename: str,
    title: str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """从上传的文件字节入库（Streamlit file_uploader 用）。"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(file_bytes)
        tmp_path = f.name
    try:
        return ingest_pdf(tmp_path, title, on_progress)
    finally:
        os.unlink(tmp_path)


# ── Web ───────────────────────────────────────────────────────────────────────

def ingest_web(
    url: str,
    title: str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """从网页 URL 入库。"""
    from .extractors.web import fetch_and_chunk

    _notify(on_progress, '抓取网页', 0.05)
    md_text, chunks, doc_id = fetch_and_chunk(url)
    if not md_text.strip():
        raise ValueError('网页内容为空')

    _run_pipeline(
        doc_id=doc_id,
        title=title,
        source_type='web',
        source_url=url,
        content=md_text,
        chunks=chunks,
        metadata={'url': url},
        on_progress=on_progress,
    )
    return doc_id


# ── arXiv ─────────────────────────────────────────────────────────────────────

def ingest_arxiv(
    url: str,
    title: str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """从 arXiv URL 入库（场景 A：用户粘贴 arXiv 链接）。"""
    from .extractors.arxiv import extract_by_url

    _notify(on_progress, '解析 arXiv 链接', 0.05)
    doc_id, content, chunks, meta = extract_by_url(url)
    if not content.strip():
        raise ValueError('arXiv 论文内容为空')

    _run_pipeline(
        doc_id=doc_id,
        title=title or meta.get('title', doc_id),
        source_type='arxiv',
        source_url=url,
        content=content,
        chunks=chunks,
        metadata=meta,
        on_progress=on_progress,
    )
    return doc_id


# ── GitHub ────────────────────────────────────────────────────────────────────

def ingest_github(
    url: str,
    title: str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """从 GitHub 仓库入库（一个仓库合并为一篇文档）。"""
    from .extractors.github import fetch_and_chunk_repo

    _notify(on_progress, '获取仓库文件列表', 0.05)
    doc_id, content, chunks = fetch_and_chunk_repo(url)
    if not chunks:
        raise ValueError('仓库中没有找到 .md 文件')

    _run_pipeline(
        doc_id=doc_id,
        title=title,
        source_type='github',
        source_url=url,
        content=content,
        chunks=chunks,
        metadata={'repo_url': url},
        on_progress=on_progress,
    )
    return doc_id
