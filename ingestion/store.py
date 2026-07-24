# Supabase 数据读写封装
#
# 对外接口：
#   upsert_document(doc_id, title, source_type, source_url, content, metadata)
#   upsert_chunks(chunks)
#   search_chunks(query_embedding, top_k, filter_doc_ids)
#   list_documents()
#   delete_document(doc_id)
#   insert_qa_log(...) / insert_qa_chunks(...)（评测：问答记录落库）
#
# 所有数据库操作统一走本模块，上层不直接接触 Supabase 客户端。

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_URL = os.environ.get('SUPABASE_URL', '')
_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

# 模块级单例
_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(_URL, _KEY)
    return _client


# ── documents ─────────────────────────────────────────────────────────────────

def upsert_document(
    doc_id: str,
    title: str,
    source_type: str,
    source_url: str,
    content: str,
    metadata: dict | None = None,
    status: str = 'processing',
    error_message: str | None = None,
) -> None:
    """插入或更新 documents 记录（按 doc_id 覆盖）。

    Args:
        doc_id:        文档唯一标识
        title:         文档标题（用户填或自动提取）
        source_type:   pdf / web / github / arxiv
        source_url:    原始来源地址或文件名
        content:       清洗后的完整文本（用于原文定位和高亮）
        metadata:      来源特有字段，如 authors、arxiv_id 等
        status:        processing / ready / failed
        error_message: 失败原因，status=failed 时填写
    """
    row = {
        'doc_id':       doc_id,
        'title':        title,
        'source_type':  source_type,
        'source_url':   source_url,
        'content':      content,
        'metadata':     metadata or {},
        'status':       status,
        'error_message': error_message,
    }
    _get_client().table('documents').upsert(row).execute()


def update_document_status(
    doc_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """更新文档入库状态。"""
    _get_client().table('documents').update({
        'status':        status,
        'error_message': error_message,
    }).eq('doc_id', doc_id).execute()


def list_documents() -> list[dict]:
    """返回所有文档的基本信息（按创建时间倒序）。"""
    resp = (
        _get_client()
        .table('documents')
        .select('doc_id, title, source_type, source_url, status, created_at')
        .order('created_at', desc=True)
        .execute()
    )
    return resp.data or []


def delete_document(doc_id: str) -> None:
    """删除文档，关联 chunks 由数据库 CASCADE 自动删除。"""
    _get_client().table('documents').delete().eq('doc_id', doc_id).execute()


# ── 评测：qa_logs / qa_chunks ─────────────────────────────────────────────────

def insert_qa_log(
    env: str,
    query: str,
    answer: str,
    mode: str,
    sub_queries: list[str],
    filter_doc_ids: list[str] | None,
    model: str,
    top_k: int,
    latency_ms: int,
    session_id: str | None = None,
) -> str:
    """写入一条问答记录（总账），返回 qa_id。"""
    row = {
        'env':            env,
        'session_id':     session_id,
        'query':          query,
        'answer':         answer,
        'mode':           mode,
        'sub_queries':    sub_queries,
        'filter_doc_ids': filter_doc_ids,
        'model':          model,
        'top_k':          top_k,
        'latency_ms':     latency_ms,
    }
    resp = _get_client().table('qa_logs').insert(row).execute()
    return resp.data[0]['id']


def insert_qa_chunks(qa_id: str, chunks: list[dict], cited_indexes: set[int]) -> None:
    """批量写入一次问答的召回明细（明细账）。

    Args:
        qa_id:          对应的 qa_logs.id
        chunks:         召回的 chunk 列表，列表顺序即最终排名
        cited_indexes:  回答中被引用的 chunk 序号集合（1-based）
    """
    rows = [
        {
            'qa_id':        qa_id,
            'chunk_id':     str(c['chunk_id']) if c.get('chunk_id') else None,
            'doc_id':       c.get('doc_id'),
            'title':        c.get('title'),
            'rank':         i,
            'similarity':   c.get('similarity'),
            'rerank_score': c.get('rerank_score'),
            'is_cited':     i in cited_indexes,
        }
        for i, c in enumerate(chunks, 1)
    ]
    if rows:
        _get_client().table('qa_chunks').insert(rows).execute()


# ── chunks ────────────────────────────────────────────────────────────────────

_UPSERT_BATCH = 100


def upsert_chunks(chunks: list[dict]) -> None:
    """批量 upsert chunks，每批 100 条。

    每条 chunk 格式：
    {
        doc_id, chunk_index, chunk_text, embedding,
        char_start, char_end, char_len, metadata(可选)
    }
    按 (doc_id, chunk_index) 唯一约束覆盖。
    """
    if not chunks:
        return

    client = _get_client()
    for start in range(0, len(chunks), _UPSERT_BATCH):
        batch = chunks[start:start + _UPSERT_BATCH]
        client.table('chunks').upsert(batch).execute()


def delete_chunks_by_doc(doc_id: str) -> None:
    """删除指定文档的所有 chunks（覆盖入库前调用）。"""
    _get_client().table('chunks').delete().eq('doc_id', doc_id).execute()


def search_chunks(
    query_embedding: list[float],
    top_k: int = 20,
    filter_doc_ids: list[str] | None = None,
) -> list[dict]:
    """调用 match_chunks RPC 做向量相似度检索。

    Args:
        query_embedding: 查询向量，长度 1024
        top_k:           返回候选数量
        filter_doc_ids:  限定文档范围，None 表示全库

    Returns:
        候选 chunk 列表，每条包含：
        chunk_id, doc_id, chunk_index, chunk_text,
        char_start, char_end, char_len,
        similarity, title, source_type, source_url
    """
    params: dict = {
        'query_embedding': query_embedding,
        'match_count':     top_k,
    }
    if filter_doc_ids:
        params['filter_doc_ids'] = filter_doc_ids

    resp = _get_client().rpc('match_chunks', params).execute()
    return resp.data or []
