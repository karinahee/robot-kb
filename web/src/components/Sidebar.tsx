'use client';

import { useEffect, useState } from 'react';
import { Icon } from './Icon';
import { mockSources, type SourceDoc } from '@/lib/mock-data';

const SOURCE_ICON: Record<SourceDoc['sourceType'], string> = {
  pdf: 'pdf',
  web: 'globe',
  arxiv: 'link',
  github: 'control',
};

const SOURCE_TYPES: { value: SourceDoc['sourceType']; label: string }[] = [
  { value: 'pdf', label: '文件' },
  { value: 'web', label: '网页' },
  { value: 'arxiv', label: 'arXiv' },
  { value: 'github', label: 'GitHub' },
];

/** 入库任务 */
interface IngestTask {
  id: string;
  name: string;
  stage: string;
  progress: number; // 0~100
  status: 'pending' | 'running' | 'failed';
  failAt: number | null; // 模拟失败点，null 表示不会失败
}

/** 根据进度映射阶段描述（与 ingestion/pipeline.py 的阶段一致） */
function stageFor(p: number): string {
  if (p < 15) return '提取文本';
  if (p < 30) return '切分文本';
  if (p < 45) return '写入文档记录';
  if (p < 80) return '向量化 chunk';
  if (p < 100) return '写入 chunks';
  return '完成';
}

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

/** 添加来源表单 */
function AddSourceForm({ onEnqueue }: { onEnqueue: (name: string) => void }) {
  const [sourceType, setSourceType] = useState<SourceDoc['sourceType']>('pdf');
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [fileName, setFileName] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setFileName(file.name);
  };

  const ready = sourceType === 'pdf' ? fileName !== '' : url.trim() !== '';

  const handleSubmit = () => {
    // TODO: 实际上传逻辑
    const name =
      title.trim() ||
      (sourceType === 'pdf' ? fileName : url.trim()) ||
      '未命名来源';
    if (!ready) return;
    onEnqueue(name);
    setTitle('');
    setUrl('');
    setFileName('');
  };

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-4 pt-5 pb-5">
      {/* 来源类型选择 */}
      <div className="mb-5">
        <p className="mb-3 text-xs text-neutral-400">来源类型</p>
        <div className="flex gap-1.5">
          {SOURCE_TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => setSourceType(t.value)}
              className={`flex-1 rounded-lg py-1.5 text-xs font-medium transition ${
                sourceType === t.value
                  ? 'bg-neutral-800 text-white'
                  : 'border border-neutral-200 text-neutral-500 hover:bg-neutral-50'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* 根据类型显示不同输入 */}
      {sourceType === 'pdf' ? (
        <div className="mb-5">
          <p className="mb-3 text-xs text-neutral-400">上传文件</p>
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-neutral-200 px-3 py-3 transition hover:border-neutral-300 hover:bg-neutral-50">
            <span className="flex-1 truncate text-xs text-neutral-400">
              {fileName || '点击选择文件'}
            </span>
            <input
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
            />
          </label>
        </div>
      ) : (
        <div className="mb-5">
          <p className="mb-2 text-xs text-neutral-400">链接 URL</p>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={
              sourceType === 'arxiv'
                ? 'https://arxiv.org/abs/...'
                : sourceType === 'github'
                  ? 'https://github.com/...'
                  : 'https://...'
            }
            className="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-xs text-neutral-700 placeholder-neutral-300 outline-none transition focus:border-neutral-400"
          />
        </div>
      )}

      {/* 标题（可选） */}
      <div className="mb-6">
        <p className="mb-3 text-xs text-neutral-400">标题（可选）</p>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="自定义标题，默认使用文件/页面名称"
          className="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-xs text-neutral-700 placeholder-neutral-300 outline-none transition focus:border-neutral-400"
        />
      </div>

      {/* 加入按钮：未填写时为灰色线框，有内容后为黑色胶囊白字 */}
      <button
        onClick={handleSubmit}
        disabled={!ready}
        className={`w-full rounded-full border py-2 text-xs font-medium transition ${
          ready
            ? 'border-neutral-800 bg-neutral-800 text-white hover:border-neutral-700 hover:bg-neutral-700'
            : 'border-neutral-200 text-neutral-400'
        }`}
      >
        加入
      </button>
    </div>
  );
}

/** 底部入库队列 */
function IngestQueue({
  queue,
  onRetry,
  onRemove,
}: {
  queue: IngestTask[];
  onRetry: (id: string) => void;
  onRemove: (id: string) => void;
}) {
  return (
    <div className="border-t border-neutral-100 px-4 pt-3 pb-4">
      {queue.map((task) => (
        <div key={task.id} className="group mb-3 last:mb-0">
          <div className="flex items-baseline justify-between gap-2">
            <span className="truncate text-xs text-neutral-700">
              {task.name}
            </span>
            {task.status === 'failed' ? (
              <span className="shrink-0 text-xs">
                <span className="text-red-500 group-hover:hidden">失败</span>
                <span className="hidden items-center gap-2 group-hover:inline-flex">
                  <button
                    onClick={() => onRemove(task.id)}
                    className="text-xs text-neutral-400 transition hover:text-neutral-600"
                    title="从队列移除"
                  >
                    取消
                  </button>
                  <button
                    onClick={() => onRetry(task.id)}
                    className="flex items-center gap-1 text-xs text-red-500 transition hover:text-red-600"
                    title="点击重传"
                  >
                    重传
                    <svg width="10" height="10" viewBox="0 0 256 256" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                      <path fillRule="evenodd" d="M127.792 21.328a106.656 106.656 0 0 0-89.36 48.128 106.56 106.56 0 0 0-5.2 8.784 8 8 0 1 0 14.128 7.488 90.56 90.56 0 0 1 16.16-21.84 90.656 90.656 0 0 1 64.272-26.56 90.832 90.832 0 0 1 89.728 76.224l-23.936-13.664a8 8 0 0 0-7.936 13.888l36.928 21.104a7.952 7.952 0 0 0 8.16 0 8 8 0 0 0 3.936-7.024c-.08-58.848-47.904-106.528-106.88-106.528zM21.328 128.16a7.952 7.952 0 0 1 7.232-8.112 7.968 7.968 0 0 1 4.864 1.088l36.928 21.104a8 8 0 1 1-7.936 13.888L38.48 142.464a90.832 90.832 0 0 0 89.728 76.224 90.656 90.656 0 0 0 76-40.944c1.6-2.4 3.072-4.896 4.432-7.456a8 8 0 0 1 14.128 7.488 106.56 106.56 0 0 1-18.976 25.664 106.656 106.656 0 0 1-75.584 31.248c-58.976 0-106.8-47.68-106.88-106.528z" />
                    </svg>
                  </button>
                </span>
              </span>
            ) : (
              <span className="shrink-0 text-xs text-neutral-400">
                {task.stage}
              </span>
            )}
          </div>
          <div className="mt-1.5 h-1 w-full rounded-full bg-neutral-100">
            <div
              className="h-1 rounded-full bg-neutral-800 transition-all duration-200"
              style={{ width: `${task.progress}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/** 左侧来源面板：来源列表 + 添加来源按钮 */
export function Sidebar() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [view, setView] = useState<'list' | 'add'>('list');
  const [queue, setQueue] = useState<IngestTask[]>([]);

  const hasActive = queue.some((t) => t.status !== 'failed');

  // 模拟入库：每次只推进队列中第一个未失败的任务，其余排队等待；
  // 成功后从队列消失，失败则保留并标记红色「失败」
  useEffect(() => {
    if (!hasActive) return;
    const timer = setInterval(() => {
      setQueue((prev) => {
        const idx = prev.findIndex((t) => t.status !== 'failed');
        if (idx === -1) return prev;
        const t = { ...prev[idx] };
        // 模拟失败：到达失败点则标记失败，保留在列表中
        if (t.failAt !== null && t.progress >= t.failAt) {
          t.status = 'failed';
          t.stage = '失败';
          const next = [...prev];
          next[idx] = t;
          return next;
        }
        t.status = 'running';
        t.progress = Math.min(100, t.progress + 2);
        t.stage = stageFor(t.progress);
        const next = [...prev];
        if (t.progress >= 100) {
          next.splice(idx, 1); // 成功：从队列中消失
        } else {
          next[idx] = t;
        }
        return next;
      });
    }, 120);
    return () => clearInterval(timer);
  }, [hasActive]);

  // 模拟：约 35% 的任务会在中途失败
  const randomFailAt = () =>
    Math.random() < 0.35 ? 20 + Math.floor(Math.random() * 60) : null;

  const enqueue = (name: string) => {
    setQueue((prev) => [
      ...prev,
      {
        id: `task-${Date.now()}`,
        name,
        stage: '排队等待中',
        progress: 0,
        status: 'pending',
        failAt: randomFailAt(),
      },
    ]);
  };

  const retry = (id: string) => {
    setQueue((prev) =>
      prev.map((t) =>
        t.id === id
          ? {
              ...t,
              stage: '排队等待中',
              progress: 0,
              status: 'pending',
              failAt: randomFailAt(),
            }
          : t,
      ),
    );
  };

  const removeFailed = (id: string) => {
    setQueue((prev) => prev.filter((t) => t.id !== id));
  };

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
    <aside className="flex h-full w-[260px] shrink-0 flex-col border-r border-neutral-200 bg-white">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        {view === 'list' ? (
          <>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-semibold text-neutral-800">来源</span>
              <button
                onClick={() => setView('add')}
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
          </>
        ) : (
          <>
            <button
              onClick={() => setView('list')}
              className="-ml-1.5 rounded-full p-1.5 text-neutral-800 transition hover:bg-neutral-100"
              title="返回来源列表"
            >
              <svg width="14" height="14" viewBox="0 0 256 256" fill="currentColor" xmlns="http://www.w3.org/2000/svg" className="block">
                <path d="M120.448 45.792a10.672 10.672 0 1 1 15.088 15.088l-56.464 56.448h123.584a10.672 10.672 0 0 1 0 21.344H79.072l56.464 56.448a10.672 10.672 0 1 1-15.088 15.088l-74.656-74.672a10.672 10.672 0 0 1 0-15.072l74.656-74.672z" />
              </svg>
            </button>
            <span className="text-sm font-semibold text-neutral-800">添加来源</span>
          </>
        )}
      </div>

      {/* 分割线：仅添加来源视图 */}
      {view === 'add' && <div className="mt-1 border-b border-neutral-200" />}

      {view === 'list' ? (
        <>
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
        </>
      ) : (
        <AddSourceForm onEnqueue={enqueue} />
      )}

      {/* 入库队列：固定在面板最底部 */}
      {queue.length > 0 && (
        <IngestQueue queue={queue} onRetry={retry} onRemove={removeFailed} />
      )}
    </aside>
  );
}
