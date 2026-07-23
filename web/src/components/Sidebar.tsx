'use client';

import { useState } from 'react';
import { Icon } from './Icon';
import { mockSources, type SourceDoc } from '@/lib/mock-data';

const SOURCE_ICON: Record<SourceDoc['sourceType'], string> = {
  pdf: 'pdf',
  web: 'globe',
  arxiv: 'link',
  github: 'control',
};

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
          将删除 {count} 个来源，此操作不可撤销。
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

/** 左侧来源面板：来源列表 + 添加来源按钮 */
export function Sidebar() {
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
    <aside className="flex h-full w-[240px] shrink-0 flex-col border-r border-neutral-200 bg-white">
      {/* 标题栏：source + 加号（紧贴）｜最右侧收起 */}
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold text-neutral-800">来源</span>
          <button
            className="rounded-full p-1 text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700"
            title="添加来源"
          >
            <Icon name="create-kb" size={14} />
          </button>
        </div>
        <button
          className="rounded-full p-1 text-neutral-300 transition hover:bg-neutral-100 hover:text-neutral-500"
          title="收起面板"
        >
          <Icon name="collapse-nav" size={16} />
        </button>
      </div>

      {/* 来源列表 */}
      <div className="relative flex-1 overflow-y-auto px-2.5 pb-5">
        {mockSources.map((doc) => {
          const isSelected = selected.has(doc.docId);
          return (
            <div
              key={doc.docId}
              className="group mb-0.5 flex cursor-pointer items-center gap-2.5 rounded-xl px-2.5 py-2 transition hover:bg-neutral-50"
            >
              <Icon name={SOURCE_ICON[doc.sourceType]} size={16} />
              <span className="flex-1 truncate text-sm text-neutral-600">
                {doc.title}
              </span>
              {/* hover 时显示勾选圆圈，已选中时常驻显示 */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggle(doc.docId);
                }}
                className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border transition
                  ${isSelected
                    ? 'border-transparent bg-neutral-400'
                    : 'border-neutral-300 bg-transparent opacity-0 group-hover:opacity-100'
                  }`}
                title="勾选"
              >
                {isSelected && (
                  <svg width="7" height="7" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2.5 2.5L8 3" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* 有选中项时显示删除按钮（左下角） */}
      {selected.size > 0 && (
        <div className="flex justify-start px-4 pb-4">
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
