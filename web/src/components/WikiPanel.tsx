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

/** 右侧 Wiki 面板：Wiki 条目卡片列表 + 添加按钮 */
export function WikiPanel() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);

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

  return (
    <aside className="flex h-full w-[320px] shrink-0 flex-col border-l border-neutral-200 bg-white">
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
    </aside>
  );
}
