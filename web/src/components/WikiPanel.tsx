'use client';

import { useState } from 'react';
import { Icon } from './Icon';
import { mockWikiEntries } from '@/lib/mock-data';

/** 二次确认弹窗 */
function ConfirmDialog({
  count,
  onConfirm,
  onCancel,
}: {
  count: number;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/20"
      onClick={onCancel}
    >
      <div
        className="w-72 rounded-2xl border border-neutral-200 bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="mb-1.5 text-sm font-semibold text-neutral-800">确认删除</p>
        <p className="mb-5 text-xs text-neutral-500">
          将删除 {count} 条笔记，此操作不可撤销。
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-lg border border-neutral-200 px-4 py-1.5 text-xs text-neutral-500 transition hover:bg-neutral-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg border border-red-400 px-4 py-1.5 text-xs font-medium text-red-500 transition hover:bg-red-50"
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
}

/** 文本样式选项 */
type TextStyle = 'body' | 'h1' | 'h2' | 'h3';

const TEXT_STYLES: { value: TextStyle; label: string }[] = [
  { value: 'body', label: '正文' },
  { value: 'h1', label: '标题 1' },
  { value: 'h2', label: '标题 2' },
  { value: 'h3', label: '标题 3' },
];

/** 格式工具按钮 */
const FORMAT_TOOLS = [
  { key: 'bold', icon: 'b', title: '加粗' },
  { key: 'underline', icon: 'u', title: '下划线' },
  { key: 'italic', icon: 'i', title: '斜体' },
  { key: 'ol', icon: 'list', title: '有序列表' },
  { key: 'ul', icon: 'list1', title: '无序列表' },
] as const;

/** 笔记编辑器 */
function NoteEditor({
  initialTitle = '',
  onSave,
  onClose,
}: {
  initialTitle?: string;
  onSave: (title: string, body: string) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(initialTitle);
  const [body, setBody] = useState('');
  const [textStyle, setTextStyle] = useState<TextStyle>('body');
  const [styleOpen, setStyleOpen] = useState(false);
  const [activeFormats, setActiveFormats] = useState<Set<string>>(new Set());

  const toggleFormat = (key: string) => {
    setActiveFormats((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const currentStyle = TEXT_STYLES.find((s) => s.value === textStyle)!;

  return (
    <>
      {/* 标题栏：左侧笔记标题｜右侧保存胶囊 + 关闭 */}
      <div className="flex items-center justify-between gap-2 px-4 pt-5 pb-3">
        <span className="truncate text-sm font-semibold text-neutral-800">
          {title.trim() || '新建笔记'}
        </span>
        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={() => onSave(title, body)}
            className="rounded-full bg-neutral-800 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-neutral-700"
          >
            保存
          </button>
          <button
            onClick={onClose}
            className="rounded-full p-1.5 text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700"
            title="关闭"
          >
            <Icon name="close" size={14} />
          </button>
        </div>
      </div>

      {/* 工具区 */}
      <div className="flex items-center gap-1 px-4 pb-3">
        {/* 文本样式选择 */}
        <div className="relative">
          <button
            onClick={() => setStyleOpen(!styleOpen)}
            className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs text-neutral-600 transition hover:bg-neutral-100"
          >
            {currentStyle.label}
            <Icon
              name="arrow-down"
              size={10}
              className={`transition-transform ${styleOpen ? 'rotate-180' : ''}`}
            />
          </button>
          {styleOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setStyleOpen(false)}
              />
              <div className="absolute top-full left-0 z-50 mt-1 w-24 overflow-hidden rounded-xl border border-neutral-200 bg-white p-1 shadow-lg">
                {TEXT_STYLES.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => {
                      setTextStyle(s.value);
                      setStyleOpen(false);
                    }}
                    className={`flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs transition hover:bg-neutral-50 ${
                      s.value === textStyle
                        ? 'font-semibold text-neutral-800'
                        : 'text-neutral-500'
                    }`}
                  >
                    {s.label}
                    {s.value === textStyle && (
                      <span className="h-1.5 w-1.5 rounded-full bg-neutral-800" />
                    )}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* 竖分隔线 */}
        <div className="mx-1 h-4 w-px bg-neutral-200" />

        {/* 格式按钮 */}
        {FORMAT_TOOLS.map((tool) => (
          <button
            key={tool.key}
            onClick={() => toggleFormat(tool.key)}
            title={tool.title}
            className={`rounded-lg p-1.5 transition ${
              activeFormats.has(tool.key)
                ? 'bg-neutral-200'
                : 'hover:bg-neutral-100'
            }`}
          >
            <Icon name={tool.icon} size={14} />
          </button>
        ))}
      </div>

      {/* 分割线 */}
      <div className="border-b border-neutral-200" />

      {/* 编辑区：笔记标题 + 正文 */}
      <div className="flex flex-1 flex-col overflow-y-auto px-4 py-4">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="笔记标题"
          className="mb-3 w-full text-base font-bold text-neutral-800 placeholder-neutral-300 outline-none"
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="开始记录…"
          className="w-full flex-1 resize-none text-sm leading-6 text-neutral-700 placeholder-neutral-300 outline-none"
        />
      </div>
    </>
  );
}

/** 右侧 Wiki 面板：Wiki 条目卡片列表 + 添加按钮 */
export function WikiPanel() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [view, setView] = useState<'list' | 'edit'>('list');
  const [editingTitle, setEditingTitle] = useState('');

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleDelete = () => {
    // TODO: 实际删除逻辑
    setSelected(new Set());
    setConfirmOpen(false);
  };

  const handleSave = () => {
    // TODO: 实际保存逻辑（title, body 由 NoteEditor 内部管理，后续接入 API）
    setView('list');
  };

  return (
    <aside className="flex h-full w-[320px] shrink-0 flex-col border-l border-neutral-200 bg-white">
      {view === 'list' ? (
        <>
          {/* 标题栏：最左侧收起｜加号 + wiki（紧贴） */}
          <div className="flex items-center justify-between px-5 pt-5 pb-3">
            <button
              className="rounded-full p-1 text-neutral-300 transition hover:bg-neutral-100 hover:text-neutral-500"
              title="收起面板"
            >
              <Icon name="expand-nav" size={16} />
            </button>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => {
                  setEditingTitle('');
                  setView('edit');
                }}
                className="rounded-full p-1 text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700"
                title="新建 Wiki"
              >
                <Icon name="create-kb" size={14} />
              </button>
              <span className="text-sm font-semibold text-neutral-800">笔记</span>
            </div>
          </div>

          {/* Wiki 卡片列表 */}
          <div className="relative flex-1 overflow-y-auto px-4 pb-5">
            {mockWikiEntries.map((entry) => {
              const isSelected = selected.has(entry.id);
              return (
                <div
                  key={entry.id}
                  onClick={() => {
                    setEditingTitle(entry.title);
                    setView('edit');
                  }}
                  className="group relative mb-3 cursor-pointer rounded-2xl border border-neutral-200 bg-white p-4 transition hover:border-neutral-300"
                >
                  {/* 右上角勾选圆圈（hover 或已选中时显示） */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle(entry.id);
                    }}
                    className={`absolute top-3 right-3 flex h-3.5 w-3.5 items-center justify-center rounded-full border transition
                      ${isSelected
                        ? 'border-transparent bg-neutral-400'
                        : 'border-neutral-300 bg-transparent opacity-0 group-hover:opacity-100'
                      }`}
                  >
                    {isSelected && (
                      <svg width="7" height="7" viewBox="0 0 10 10" fill="none">
                        <path d="M2 5l2.5 2.5L8 3" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </button>

                  <h3 className="mb-1.5 pr-6 text-sm font-semibold text-neutral-800">
                    {entry.title}
                  </h3>
                  <p className="mb-2 line-clamp-2 text-xs leading-relaxed text-neutral-600">
                    {entry.summary}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-neutral-400">
                    <span>{entry.createdAt}</span>
                    {entry.tags.map((tag) => (
                      <span key={tag}># {tag}</span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 有选中项时显示删除按钮（右下角） */}
          {selected.size > 0 && (
            <div className="flex justify-end px-4 pb-4">
              <button
                onClick={() => setConfirmOpen(true)}
                className="rounded-lg border border-red-400 px-4 py-1.5 text-xs font-medium text-red-500 transition hover:bg-red-50"
              >
                删除 ({selected.size})
              </button>
            </div>
          )}

          {/* 二次确认弹窗 */}
          {confirmOpen && (
            <ConfirmDialog
              count={selected.size}
              onConfirm={handleDelete}
              onCancel={() => setConfirmOpen(false)}
            />
          )}
        </>
      ) : (
        <NoteEditor
          initialTitle={editingTitle}
          onSave={handleSave}
          onClose={() => setView('list')}
        />
      )}
    </aside>
  );
}
