# SiliconFlow Embedding 封装
#
# 对外接口：
#   embed(texts) → list[list[float]]
#
# 策略：
#   - 自动分批，每批最多 EMBEDDING_BATCH_SIZE 条（默认 32）
#   - 网络错误 / 5xx / 429 自动重试 3 次，指数退避
#   - 4xx 输入错误不重试，直接抛出
#   - 返回向量数量与输入数量严格一致，维度校验为 EMBEDDING_DIMENSION

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

_API_KEY    = os.environ.get('SILICONFLOW_API_KEY', '')
_MODEL      = os.environ.get('EMBEDDING_MODEL', 'Qwen/Qwen3-Embedding-0.6B')
_DIMENSION  = int(os.environ.get('EMBEDDING_DIMENSION', '1024'))
_BATCH_SIZE = int(os.environ.get('EMBEDDING_BATCH_SIZE', '32'))
_URL        = 'https://api.siliconflow.cn/v1/embeddings'
_RETRIES    = 3

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """调用 SiliconFlow API 获取一批文本的向量。"""
    headers = {
        'Authorization': f'Bearer {_API_KEY}',
        'Content-Type':  'application/json',
    }
    payload = {
        'model':           _MODEL,
        'input':           texts,
        'encoding_format': 'float',
    }

    last_exc: Exception | None = None
    for attempt in range(_RETRIES):
        try:
            resp = requests.post(_URL, headers=headers, json=payload, timeout=30)

            # 4xx 不重试
            if resp.status_code not in _RETRYABLE_STATUS:
                resp.raise_for_status()

            # 可重试错误
            retry_after = int(resp.headers.get('Retry-After', 2 ** attempt))
            if attempt < _RETRIES - 1:
                time.sleep(retry_after)
                continue
            resp.raise_for_status()

        except requests.exceptions.Timeout as e:
            last_exc = e
            if attempt < _RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < _RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise

        # 成功
        data = resp.json().get('data', [])
        if len(data) != len(texts):
            raise ValueError(
                f'返回向量数量({len(data)})与输入文本数量({len(texts)})不一致'
            )
        vectors = [item['embedding'] for item in data]
        for v in vectors:
            if len(v) != _DIMENSION:
                raise ValueError(
                    f'向量维度({len(v)})与 EMBEDDING_DIMENSION({_DIMENSION})不一致'
                )
        return vectors

    raise RuntimeError(f'embedding 请求失败（重试 {_RETRIES} 次）: {last_exc}')


def embed(texts: list[str]) -> list[list[float]]:
    """批量获取文本向量。

    Args:
        texts: 待向量化的文本列表，空字符串会被跳过

    Returns:
        与输入顺序一致的向量列表，每个向量长度为 EMBEDDING_DIMENSION
    """
    if not texts:
        return []

    # 过滤空字符串，记录原始索引
    indexed = [(i, t) for i, t in enumerate(texts) if t.strip()]
    if not indexed:
        return []

    results: list[list[float] | None] = [None] * len(texts)

    # 分批
    for start in range(0, len(indexed), _BATCH_SIZE):
        batch = indexed[start:start + _BATCH_SIZE]
        batch_texts = [t for _, t in batch]
        vectors = _embed_batch(batch_texts)
        for (orig_idx, _), vec in zip(batch, vectors):
            results[orig_idx] = vec

    return [v for v in results if v is not None]
