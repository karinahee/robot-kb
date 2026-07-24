# Supabase 数据库初始化脚本
#
# 用法：
#   python scripts/setup_db.py
#
# 从 .env 读取 PostgreSQL 连接字符串，执行建表 SQL。
# 幂等：使用 IF NOT EXISTS / CREATE OR REPLACE，可安全重复运行。

import os
import sys
import psycopg2
from dotenv import load_dotenv

# 项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

DB_URL = os.environ.get('PostgreSQL', '')

SQL = """
-- 开启 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- documents 表
CREATE TABLE IF NOT EXISTS documents (
    doc_id        text        PRIMARY KEY,
    source_type   text        NOT NULL,
    title         text,
    source_url    text,
    content       text,
    status        text        NOT NULL DEFAULT 'processing',
    error_message text,
    content_hash  text,
    metadata      jsonb       DEFAULT '{}',
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now()
);

-- 旧库迁移：删除 lang 列（match_chunks 依赖它，先删函数再删列）
DROP FUNCTION IF EXISTS match_chunks(vector, integer, text[]);
ALTER TABLE IF EXISTS documents DROP COLUMN IF EXISTS lang;

-- chunks 表
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id     uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id       text         NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index  int          NOT NULL,
    chunk_text   text         NOT NULL,
    embedding    vector(1024),
    char_start   int,
    char_end     int,
    char_len     int,
    metadata     jsonb        DEFAULT '{}',
    created_at   timestamptz  DEFAULT now(),
    UNIQUE (doc_id, chunk_index)
);

-- 向量检索 RPC 函数
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding  vector(1024),
    match_count      int     DEFAULT 20,
    filter_doc_ids   text[]  DEFAULT NULL
)
RETURNS TABLE (
    chunk_id    uuid,
    doc_id      text,
    chunk_index int,
    chunk_text  text,
    char_start  int,
    char_end    int,
    char_len    int,
    similarity  float,
    title       text,
    source_type text,
    source_url  text
)
LANGUAGE sql STABLE AS $$
    SELECT
        c.chunk_id,
        c.doc_id,
        c.chunk_index,
        c.chunk_text,
        c.char_start,
        c.char_end,
        c.char_len,
        1 - (c.embedding <=> query_embedding) AS similarity,
        d.title,
        d.source_type,
        d.source_url
    FROM chunks c
    JOIN documents d ON d.doc_id = c.doc_id
    WHERE
        (filter_doc_ids IS NULL OR c.doc_id = ANY(filter_doc_ids))
        AND c.embedding IS NOT NULL
        AND d.status = 'ready'
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- updated_at 自动更新触发器
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS documents_updated_at ON documents;
CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ── 评测：对话记录 ────────────────────────────────────────────────────────────

-- qa_logs 对话主表（一次问答一行）
CREATE TABLE IF NOT EXISTS qa_logs (
    id             uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    env            text         NOT NULL DEFAULT 'test',  -- test / prod
    session_id     text,
    query          text         NOT NULL,
    answer         text,
    mode           text,                                   -- quick / full
    sub_queries    jsonb        DEFAULT '[]',
    filter_doc_ids text[],
    model          text,
    top_k          int,
    latency_ms     int,
    created_at     timestamptz  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS qa_logs_env_created_idx ON qa_logs (env, created_at DESC);

-- qa_chunks 召回明细表（每次问答召回的每个 chunk 一行）
CREATE TABLE IF NOT EXISTS qa_chunks (
    id           uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    qa_id        uuid         NOT NULL REFERENCES qa_logs(id) ON DELETE CASCADE,
    chunk_id     uuid,
    doc_id       text,
    title        text,                                   -- 冗余，防文档被删后丢失
    rank         int,                                    -- 最终排名（1-based）
    similarity   float,                                  -- 向量粗排分
    rerank_score float,                                  -- 精排分
    is_cited     bool         DEFAULT false,             -- 回答是否引用 [n]
    relevance    int,                                    -- 人工标注：NULL 未标 / 0 不相关 / 1 相关 / 2 强相关
    created_at   timestamptz  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS qa_chunks_qa_id_idx ON qa_chunks (qa_id);

-- 分环境视图
CREATE OR REPLACE VIEW v_test_qa AS SELECT * FROM qa_logs WHERE env = 'test';
CREATE OR REPLACE VIEW v_prod_qa AS SELECT * FROM qa_logs WHERE env = 'prod';
"""


def main() -> None:
    if not DB_URL:
        print('错误：.env 中未找到 PostgreSQL 连接字符串')
        sys.exit(1)

    print('连接数据库...')
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            print('执行建表 SQL...')
            cur.execute(SQL)
            print('验证表结构...')
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name IN ('documents', 'chunks', 'qa_logs', 'qa_chunks')"
            )
            tables = [row[0] for row in cur.fetchall()]
            print(f'已创建表：{tables}')
            cur.execute(
                "SELECT routine_name FROM information_schema.routines "
                "WHERE routine_schema = 'public' AND routine_name = 'match_chunks'"
            )
            fn = cur.fetchone()
            print(f'RPC 函数：{fn[0] if fn else "未找到"}')
        print('初始化完成。')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
