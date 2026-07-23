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
    lang          text,
    content       text,
    status        text        NOT NULL DEFAULT 'processing',
    error_message text,
    content_hash  text,
    metadata      jsonb       DEFAULT '{}',
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now()
);

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
    source_url  text,
    lang        text
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
        d.source_url,
        d.lang
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
                "WHERE table_schema = 'public' AND table_name IN ('documents', 'chunks')"
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
