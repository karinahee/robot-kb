# Robot-KB Streamlit 测试界面
#
# 功能：
#   侧边栏：速问/全搜模式切换、添加来源（PDF/URL/GitHub/arXiv）、文档列表、勾选批量删除
#   主区域：@文档限定范围、单轮问答带引用

import os
import re
import json
import html
import time
import uuid
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Robot-KB',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ── 常量 ──────────────────────────────────────────────────────────────────────
_CHAT_MODEL   = os.environ.get('CHAT_MODEL', 'deepseek-ai/DeepSeek-V3')
_CHAT_URL     = 'https://api.siliconflow.cn/v1/chat/completions'
_API_KEY      = os.environ.get('SILICONFLOW_API_KEY', '')


# ── LLM 调用 ──────────────────────────────────────────────────────────────────

def _chat(messages: list[dict], temperature: float = 0.3) -> str:
    """调 DeepSeek Chat API，返回文本内容。"""
    headers = {
        'Authorization': f'Bearer {_API_KEY}',
        'Content-Type':  'application/json',
    }
    payload = {
        'model':       _CHAT_MODEL,
        'messages':    messages,
        'temperature': temperature,
    }
    resp = requests.post(_CHAT_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']


def generate_sub_queries(query: str) -> list[str]:
    """用 LLM 将用户问题改写为 2~3 个检索子查询。"""
    prompt = (
        '你是一个检索查询改写助手。'
        '将用户问题改写为2~3个不同角度的搜索子问题，用于检索知识库。'
        '直接输出JSON格式：{"queries": ["...", "..."]}，不要输出其他内容。'
    )
    try:
        raw = _chat([
            {'role': 'system', 'content': prompt},
            {'role': 'user',   'content': query},
        ])
        data = json.loads(raw)
        queries = data.get('queries', [])
        return [q.strip() for q in queries if q.strip()][:3]
    except Exception:
        return []  # 失败时降级为仅用原始 query


def generate_answer(query: str, chunks: list[dict]) -> str:
    """用 LLM 基于检索结果生成带引用标注的回答。"""
    context_parts = []
    for i, c in enumerate(chunks, 1):
        context_parts.append(
            f'[{i}] 来源：{c["title"]}（{c["source_type"]}）\n{c["chunk_text"]}'
        )
    context = '\n\n'.join(context_parts)

    system = (
        '你是一个专业的机器人领域知识助手，根据以下参考资料回答用户问题。'
        '回答时用 [1][2] 等标注引用来源，仅引用参考资料中的内容，'
        '不要编造参考资料中没有的信息。'
        '如果参考资料无法回答问题，请明确说明。\n\n'
        f'参考资料：\n{context}'
    )
    return _chat([
        {'role': 'system', 'content': system},
        {'role': 'user',   'content': query},
    ])


# ── 入库回调 ──────────────────────────────────────────────────────────────────

def _progress_cb(stage: str, progress: float) -> None:
    bar = st.session_state.get('progress_bar')
    label = st.session_state.get('progress_label')
    if bar:
        bar.progress(progress)
    if label:
        label.text(stage)


# ── 入库处理 ──────────────────────────────────────────────────────────────────

def _do_ingest(source_type: str, **kwargs) -> tuple[bool, str]:
    """统一入库入口，返回 (success, message)。"""
    from ingestion.pipeline import (
        ingest_pdf_upload, ingest_web, ingest_arxiv, ingest_github,
    )
    try:
        if source_type == 'pdf':
            doc_id = ingest_pdf_upload(
                file_bytes=kwargs['file_bytes'],
                filename=kwargs['filename'],
                title=kwargs['title'],
                on_progress=_progress_cb,
            )
        elif source_type == 'web':
            doc_id = ingest_web(
                url=kwargs['url'],
                title=kwargs['title'],
                on_progress=_progress_cb,
            )
        elif source_type == 'arxiv':
            doc_id = ingest_arxiv(
                url=kwargs['url'],
                title=kwargs['title'],
                on_progress=_progress_cb,
            )
        elif source_type == 'github':
            doc_id = ingest_github(
                url=kwargs['url'],
                title=kwargs['title'],
                on_progress=_progress_cb,
            )
        else:
            return False, f'未知来源类型：{source_type}'
        return True, doc_id
    except Exception as e:
        return False, str(e)


# ── 引用渲染 ──────────────────────────────────────────────────────────────────

def _render_answer_with_citations(answer: str, chunks: list[dict]) -> str:
    """将回答中的 [n] 替换为可点击的 HTML 上标，返回 HTML 字符串。"""
    def _replace(m):
        n = int(m.group(1))
        if 1 <= n <= len(chunks):
            c = chunks[n - 1]
            title = html.escape(c.get('title', ''))
            return (
                f'<sup style="color:#1a73e8; cursor:pointer; '
                f'font-size:0.75em;" '
                f'title="{title}">[{n}]</sup>'
            )
        return m.group(0)

    return re.sub(r'\[(\d+)\]', _replace, html.escape(answer))


def _render_citation_cards(chunks: list[dict]) -> None:
    """在回答下方展示引用来源卡片。"""
    st.markdown('**引用来源**')
    for i, c in enumerate(chunks, 1):
        score = c.get('rerank_score', c.get('similarity', 0))
        title = c.get('title', '')
        stype = c.get('source_type', '')
        label = f'[{i}] {title} · {stype} · score: {score:.3f}'

        st.markdown(f'**{label}**')
        # 高亮整个 chunk 文本
        chunk_text = html.escape(c.get('chunk_text', ''))
        st.markdown(
            f'<div style="background:#fff9c4; padding:10px; '
            f'border-radius:6px; border-left:4px solid #f9a825; '
            f'font-size:0.88em; line-height:1.6; '
            f'white-space:pre-wrap;">{chunk_text}</div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        col1.caption(f'文档 ID：{c.get("doc_id", "")}')
        col2.caption(f'Chunk #{c.get("chunk_index", "")}')


# ── 侧边栏 ────────────────────────────────────────────────────────────────────

def _sidebar() -> None:
    """渲染侧边栏；勾选仅用于批量删除，检索始终为全库。"""
    from ingestion.store import list_documents, delete_document

    with st.sidebar:
        # 调宽侧边栏（仅展开态生效）+ 红色文字按钮样式 + 内容置顶
        st.markdown(
            '<style>'
            '[data-testid="stSidebar"][aria-expanded="true"] {'
            '  width: 340px;'
            '}'
            '[data-testid="stSidebar"][aria-expanded="false"] {'
            '  width: 0; min-width: 0;'
            '}'
            '[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {'
            '  padding-top: 0.5rem;'
            '}'
            'button[kind="tertiary"] {color: #d32f2f; padding: 0;}'
            '</style>',
            unsafe_allow_html=True,
        )

        # ── 检索模式（速问/全搜，置顶）───────────────────────────────────
        st.segmented_control(
            '检索模式',
            options=['quick', 'full'],
            format_func=lambda x: {'quick': '速问', 'full': '全搜'}[x],
            default='quick',
            key='search_mode',
            label_visibility='collapsed',
        )
        st.divider()

        # ── 添加来源 ────────────────────────────────────────────────────
        st.subheader('添加来源')
        source_type = st.selectbox(
            '来源类型',
            ['pdf', 'web', 'arxiv', 'github'],
            format_func=lambda x: {
                'pdf':    'PDF 文件',
                'web':    '网页 URL',
                'arxiv':  'arXiv 链接',
                'github': 'GitHub 仓库',
            }[x],
            label_visibility='collapsed',
        )

        with st.form('ingest_form', clear_on_submit=True):
            title = st.text_input('文档标题（可选）')

            if source_type == 'pdf':
                uploaded = st.file_uploader('上传 PDF', type=['pdf'])
                url_val  = ''
            else:
                uploaded = None
                placeholder = {
                    'web':    'https://example.com/page',
                    'arxiv':  'https://arxiv.org/abs/2004.00784',
                    'github': 'https://github.com/owner/repo',
                }[source_type]
                url_val = st.text_input('URL', placeholder=placeholder)

            submitted = st.form_submit_button('入库', use_container_width=True)

        if submitted:
            progress_label = st.empty()
            progress_bar   = st.progress(0)
            st.session_state['progress_bar']   = progress_bar
            st.session_state['progress_label'] = progress_label

            if source_type == 'pdf' and uploaded is None:
                st.error('请上传 PDF 文件')
            elif source_type != 'pdf' and not url_val.strip():
                st.error('请输入 URL')
            else:
                kwargs = {'title': title or ''}
                if source_type == 'pdf':
                    kwargs['file_bytes'] = uploaded.read()
                    kwargs['filename']   = uploaded.name
                else:
                    kwargs['url'] = url_val.strip()

                success, result = _do_ingest(source_type, **kwargs)
                progress_bar.empty()
                progress_label.empty()

                if success:
                    st.success(f'入库成功：{result}')
                    st.rerun()
                else:
                    st.error(f'入库失败：{result}')

        st.divider()

        # ── 文档列表 ──────────────────────────────────────────────────────
        try:
            docs = list_documents()
        except Exception as e:
            st.error(f'读取文档列表失败：{e}')
            return

        if not docs:
            st.subheader('文档库')
            st.caption('暂无文档，请先添加来源。')
            return

        # 当前勾选的文档（checkbox 状态存于 session_state）
        selected_ids = [
            d['doc_id'] for d in docs
            if st.session_state.get(f'chk_{d["doc_id"]}')
        ]

        # 标题行：勾选后右侧出现红色「删除」，点击批量删除
        head1, head2 = st.columns([3, 1])
        with head1:
            st.subheader('文档库')
        with head2:
            if selected_ids and st.button('删除', type='tertiary', help='删除勾选的文档'):
                for doc_id in selected_ids:
                    delete_document(doc_id)
                    st.session_state.pop(f'chk_{doc_id}', None)
                st.rerun()

        for doc in docs:
            doc_id = doc['doc_id']
            status = doc.get('status', '')
            badge  = {'ready': '', 'processing': '（入库中）', 'failed': '（失败）'}.get(status, '')
            st.checkbox(
                f'{doc["title"] or doc_id}{badge}',
                value=False,
                key=f'chk_{doc_id}',
            )


# ── 对话区 ────────────────────────────────────────────────────────────────────

def _chat_area() -> None:
    from retrieval.search import retrieve

    st.title('Robot-KB')
    st.caption('机器人运控知识库问答系统')

    # 历史消息（单轮，每次刷新清空）
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
    # 会话标识（同一浏览器会话内的问答归为一组）
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = str(uuid.uuid4())

    # 渲染历史
    for msg in st.session_state['messages']:
        with st.chat_message(msg['role']):
            if msg['role'] == 'assistant':
                st.markdown(msg['content'], unsafe_allow_html=True)
                if 'chunks' in msg:
                    _render_citation_cards(msg['chunks'])
            else:
                st.markdown(msg['content'])

    # ── @文档（输入框上方右侧）────────────────────────────────────────────
    from ingestion.store import list_documents
    docs = list_documents()
    # 从 checkbox 状态派生已选定的文档 id
    mention_ids = [
        d['doc_id'] for d in docs
        if st.session_state.get(f'mention_{d["doc_id"]}')
    ]

    _, doc_col = st.columns([6, 1])
    with doc_col:
        pop_label = '@文档' + (f'（{len(mention_ids)}）' if mention_ids else '')
        with st.popover(pop_label, use_container_width=True):
            if not docs:
                st.caption('文档库为空，请先在左侧添加来源。')
            for d in docs:
                st.checkbox(
                    d['title'] or d['doc_id'],
                    value=d['doc_id'] in mention_ids,
                    key=f'mention_{d["doc_id"]}',
                )
    if mention_ids:
        titles = [
            d['title'] or d['doc_id'] for d in docs
            if d['doc_id'] in mention_ids
        ]
        st.caption('已限定范围：' + '、'.join(titles))

    # 输入
    query = st.chat_input('输入问题...')
    if not query:
        return

    # 用户消息
    st.session_state['messages'].append({'role': 'user', 'content': query})
    with st.chat_message('user'):
        st.markdown(query)

    with st.chat_message('assistant'):
        t0 = time.time()
        with st.spinner('检索中...'):
            # 1. 生成子查询（仅全搜模式启用 query 改写，模式来自侧边栏）
            mode = st.session_state.get('search_mode', 'quick')
            sub_queries = generate_sub_queries(query) if mode == 'full' else []

            # 2. 检索（@文档选中时限定文档范围）
            try:
                chunks = retrieve(
                    query=query,
                    sub_queries=sub_queries,
                    top_k=5,
                    filter_doc_ids=mention_ids or None,
                )
            except Exception as e:
                st.error(f'检索失败：{e}')
                return

        if not chunks:
            st.warning('知识库中没有找到相关内容，请先添加来源。')
            return

        with st.spinner('生成回答...'):
            # 3. 生成回答
            try:
                answer = generate_answer(query, chunks)
            except Exception as e:
                st.error(f'生成回答失败：{e}')
                return

        latency_ms = int((time.time() - t0) * 1000)

        # 4. 落库（评测用，失败不影响问答主流程）
        try:
            from ingestion.store import insert_qa_log, insert_qa_chunks
            # 从回答里解析被引用的 chunk 序号（[n] 且 n 在召回范围内）
            cited = {
                int(m.group(1))
                for m in re.finditer(r'\[(\d+)\]', answer)
                if 1 <= int(m.group(1)) <= len(chunks)
            }
            qa_id = insert_qa_log(
                env='test',
                session_id=st.session_state['session_id'],
                query=query,
                answer=answer,
                mode=mode,
                sub_queries=sub_queries,
                filter_doc_ids=mention_ids or None,
                model=_CHAT_MODEL,
                top_k=5,
                latency_ms=latency_ms,
            )
            insert_qa_chunks(qa_id, chunks, cited)
        except Exception as e:
            st.caption(f'（问答记录写入失败：{e}）')

        # 5. 渲染回答（带引用上标）
        answer_html = _render_answer_with_citations(answer, chunks)
        st.markdown(answer_html, unsafe_allow_html=True)

        # 6. 引用卡片
        _render_citation_cards(chunks)

        # 7. 显示子查询（调试用）
        if sub_queries:
            st.caption('检索子查询（调试）')
            for q in sub_queries:
                st.caption(f'· {q}')

    # 保存到历史
    st.session_state['messages'].append({
        'role':    'assistant',
        'content': answer_html,
        'chunks':  chunks,
    })


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    _sidebar()
    _chat_area()


if __name__ == '__main__':
    main()
