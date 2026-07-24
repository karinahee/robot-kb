# 检索模块：多查询扩展 + chunk_id 去重 + Rerank 精排
#
# 对外接口：
#   retrieve(query, sub_queries, top_k, filter_doc_ids)
#
# 流程：
#   1. [原始 query] + sub_queries 批量 embedding
#   2. 每个向量调 search_chunks 召回候选
#   3. 按 chunk_id 去重合并
#   4. SiliconFlow Rerank 精排
#   5. 返回 top_k

import os
import requests
from dotenv import load_dotenv

from ingestion.embedding import embed
from ingestion.store import search_chunks

load_dotenv()

_API_KEY     = os.environ.get('SILICONFLOW_API_KEY', '')
_RERANK_URL  = 'https://api.siliconflow.cn/v1/rerank'
_RERANK_MODEL = os.environ.get('RERANK_MODEL', 'BAAI/bge-reranker-v2-m3')

# 每个子查询召回的候选数
_PER_QUERY_K = 8
# 去重后候选池上限（超过则先按向量分数粗截断再交给 Rerank）
_CANDIDATE_LIMIT = 30


def _rerank(query: str, candidates: list[dict]) -> list[dict]:
    """调 SiliconFlow Rerank API 对候选 chunk 精排。

    Args:
        query:      原始用户查询（不是子查询）
        candidates: 去重后的候选 chunk 列表

    Returns:
        按 relevance_score 降序排列的列表，每条写入 rerank_score 字段
    """
    if not candidates:
        return candidates

    headers = {
        'Authorization': f'Bearer {_API_KEY}',
        'Content-Type':  'application/json',
    }
    payload = {
        'model':     _RERANK_MODEL,
        'query':     query,
        'documents': [c['chunk_text'] for c in candidates],
        'top_n':     len(candidates),
    }

    resp = requests.post(_RERANK_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    results = resp.json().get('results', [])

    # results 每项：{index, relevance_score, document}
    for item in results:
        idx = item['index']
        candidates[idx]['rerank_score'] = item['relevance_score']

    return sorted(candidates, key=lambda c: c.get('rerank_score', 0.0), reverse=True)


def retrieve(
    query: str,
    sub_queries: list[str],
    top_k: int = 5,
    filter_doc_ids: list[str] | None = None,
) -> list[dict]:
    """多查询召回 + 去重 + Rerank，返回精排后的 top_k 条。

    Args:
        query:          用户原始问题
        sub_queries:    LLM 生成的子查询列表（由 app.py 传入，本模块不生成）
        top_k:          最终返回条数
        filter_doc_ids: 限定文档范围，None 表示全库

    Returns:
        精排后的 chunk 列表，每条包含：
        chunk_id, doc_id, chunk_index, chunk_text,
        char_start, char_end, char_len,
        rerank_score, title, source_type, source_url
    """
    # 1. 合并查询列表：原始 query 始终参与，子查询去重去空
    all_queries = [query]
    for q in sub_queries:
        q = q.strip()
        if q and q not in all_queries:
            all_queries.append(q)

    # 2. 批量 embedding（一次 API 调用）
    vectors = embed(all_queries)

    # 3. 每个查询分别召回
    all_candidates: list[dict] = []
    for vec in vectors:
        results = search_chunks(
            query_embedding=vec,
            top_k=_PER_QUERY_K,
            filter_doc_ids=filter_doc_ids,
        )
        all_candidates.extend(results)

    # 4. 按 chunk_id 去重
    seen: set[str] = set()
    candidates: list[dict] = []
    for c in all_candidates:
        cid = str(c.get('chunk_id', ''))
        if cid and cid not in seen:
            seen.add(cid)
            candidates.append(c)

    # 5. 候选池超过上限时，按向量相似度粗截断
    if len(candidates) > _CANDIDATE_LIMIT:
        candidates = sorted(
            candidates,
            key=lambda c: c.get('similarity', 0.0),
            reverse=True,
        )[:_CANDIDATE_LIMIT]

    # 6. Rerank 精排（用原始 query）
    ranked = _rerank(query, candidates)

    return ranked[:top_k]
