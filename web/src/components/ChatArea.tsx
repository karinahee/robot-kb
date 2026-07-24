'use client';

import { useState } from 'react';
import { Icon } from './Icon';
import { mockMessages, type ChatMessage } from '@/lib/mock-data';

type QueryMode = 'quick' | 'full';

const MODE_LABEL: Record<QueryMode, string> = {
  quick: '速问',
  full: '全搜',
};

/** 引用注脚（悬浮显示来源卡片） */
function CitationSup({
  idx,
  citation,
}: {
  idx: number;
  citation?: { index: number; title: string; chunkText: string };
}) {
  return (
    <sup className="group relative mx-0.5 inline-block">
      <span className="cursor-pointer font-medium text-neutral-400 transition hover:text-neutral-700">
        [{idx}]
      </span>
      {/* 悬浮卡片：注脚下方 */}
      {citation && (
        <span className="pointer-events-none invisible absolute top-full left-1/2 z-50 mt-4 w-72 -translate-x-1/2 rounded-2xl border border-neutral-200 bg-white p-4 text-left opacity-0 shadow-lg transition-opacity duration-150 group-hover:visible group-hover:opacity-100">
          <span className="mb-1.5 block text-xs font-semibold text-neutral-800">
            {citation.title}
          </span>
          <span className="line-clamp-4 block text-xs leading-relaxed text-neutral-500">
            {citation.chunkText}
          </span>
        </span>
      )}
    </sup>
  );
}

/** 回答内容：把 [n] 渲染为上标引用 */
function AnswerContent({ msg }: { msg: ChatMessage }) {
  if (msg.role === 'user') {
    return <p className="text-sm text-neutral-700">{msg.content}</p>;
  }

  const parts = msg.content.split(/(\[\d+\])/g);
  return (
    <div className="text-sm leading-7 text-neutral-700">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        if (m) {
          const idx = parseInt(m[1], 10);
          const citation = msg.citations?.find((c) => c.index === idx);
          return <CitationSup key={i} idx={idx} citation={citation} />;
        }
        return <span key={i}>{part}</span>;
      })}
    </div>
  );
}

/** 引用卡片 */
function CitationCards({ msg }: { msg: ChatMessage }) {
  if (!msg.citations?.length) return null;
  return (
    <div className="mt-4">
      {msg.citations.map((c) => (
        <details key={c.index} className="group text-xs">
          <summary className="flex cursor-pointer list-none items-center py-1 leading-none text-neutral-400 transition hover:text-neutral-600 [&::-webkit-details-marker]:hidden">
            <span>[{c.index}] {c.title}</span>
          </summary>
          <div className="mb-1.5 ml-4 rounded-xl bg-neutral-50 px-4 py-3 leading-relaxed text-neutral-500">
            {c.chunkText}
          </div>
        </details>
      ))}
    </div>
  );
}

/** 模式切换下拉 */
function ModeSelect({
  mode,
  onChange,
}: {
  mode: QueryMode;
  onChange: (m: QueryMode) => void;
}) {
  const [open, setOpen] = useState(false);

  const select = (m: QueryMode) => {
    onChange(m);
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 rounded-full border border-neutral-200 px-3 py-1.5 text-xs text-neutral-500 transition hover:bg-neutral-50"
      >
        {MODE_LABEL[mode]}
        <Icon
          name="arrow-down"
          size={12}
          className={`transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <>
          {/* 点击外部关闭 */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute bottom-full left-0 z-50 mb-2 w-28 overflow-hidden rounded-xl border border-neutral-200 bg-white p-1 shadow-lg">
            {(Object.keys(MODE_LABEL) as QueryMode[]).map((m) => (
              <button
                key={m}
                onClick={() => select(m)}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition hover:bg-neutral-50 ${
                  m === mode
                    ? 'font-semibold text-neutral-800'
                    : 'text-neutral-500'
                }`}
              >
                {MODE_LABEL[m]}
                {m === mode && (
                  <span className="h-1.5 w-1.5 rounded-full bg-neutral-800" />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/** 设置项 */
interface Settings {
  systemPrompt: string;
  showCitations: boolean;
  autoNote: boolean;
}

/** 开关 */
function Toggle({
  on,
  onChange,
  label,
}: {
  on: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      onClick={() => onChange(!on)}
      className="flex w-full items-center justify-between py-1"
    >
      <span className="text-sm text-neutral-700">{label}</span>
      <span
        className={`flex h-5 w-9 items-center rounded-full px-0.5 transition-colors ${
          on ? 'bg-neutral-800' : 'bg-neutral-200'
        }`}
      >
        <span
          className={`h-4 w-4 rounded-full bg-white shadow transition-transform ${
            on ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </span>
    </button>
  );
}

/** 设置弹窗 */
function SettingsDialog({
  settings,
  onChange,
  onClose,
}: {
  settings: Settings;
  onChange: (s: Settings) => void;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/20"
      onClick={onClose}
    >
      <div
        className="w-[400px] rounded-2xl border border-neutral-200 bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 标题栏 */}
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-neutral-800">设置</h2>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-600"
          >
            <Icon name="close" size={14} />
          </button>
        </div>

        {/* 系统提示词 */}
        <div className="mb-5">
          <label className="mb-2 block text-xs font-medium text-neutral-500">
            系统提示词
          </label>
          <textarea
            value={settings.systemPrompt}
            onChange={(e) =>
              onChange({ ...settings, systemPrompt: e.target.value })
            }
            placeholder="自定义 AI 回答时的角色和行为……"
            rows={4}
            className="w-full resize-none rounded-xl border border-neutral-200 px-3 py-2.5 text-sm text-neutral-700 placeholder-neutral-300 outline-none transition focus:border-neutral-400"
          />
        </div>

        {/* 开关 */}
        <div className="space-y-2">
          <Toggle
            on={settings.showCitations}
            onChange={(v) => onChange({ ...settings, showCitations: v })}
            label="回答展示引用来源注脚"
          />
          <Toggle
            on={settings.autoNote}
            onChange={(v) => onChange({ ...settings, autoNote: v })}
            label="自动沉淀笔记"
          />
        </div>
      </div>
    </div>
  );
}

/** 中间对话区：消息列表 + 输入框 */
export function ChatArea() {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<QueryMode>('quick');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<Settings>({
    systemPrompt: '',
    showCitations: true,
    autoNote: false,
  });

  return (
    <main className="flex h-full min-w-0 flex-1 flex-col bg-white">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-10 py-8">
        <div className="mx-auto max-w-2xl space-y-8">
          {mockMessages.map((msg) => (
            <div
              key={msg.id}
              className={msg.role === 'user' ? 'flex justify-end' : ''}
            >
              {msg.role === 'user' ? (
                <div className="rounded-3xl bg-neutral-100 px-5 py-3 text-sm text-neutral-700">
                  {msg.content}
                </div>
              ) : (
                <div>
                  <AnswerContent msg={msg} />
                  <CitationCards msg={msg} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 输入框 */}
      <div className="px-10 pb-8">
        <div className="mx-auto max-w-2xl">
          <div className="rounded-3xl border border-neutral-200 bg-white transition focus-within:border-neutral-300">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="你可以问我关于知识库的问题"
              rows={2}
              className="w-full resize-none rounded-t-3xl px-5 pt-4 text-sm text-neutral-700 placeholder-neutral-300 outline-none"
            />
            <div className="flex items-center justify-between px-4 pb-3">
              <div className="flex items-center gap-2">
                <ModeSelect mode={mode} onChange={setMode} />
                <button className="flex items-center gap-1 rounded-full border border-neutral-200 px-3 py-1.5 text-xs text-neutral-500 transition hover:bg-neutral-50">
                  @来源
                </button>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setSettingsOpen(true)}
                  className="rounded-full p-2 text-neutral-300 transition hover:bg-neutral-100 hover:text-neutral-500"
                >
                  <Icon name="control" size={16} />
                </button>
                <button
                  className="rounded-full border border-neutral-200 bg-neutral-50 p-2 text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-600"
                  title="发送"
                >
                  <svg width="15" height="15" viewBox="0 0 256 256" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                    <path d="M117.3 202.662V79.078l-56.461 56.449a10.662 10.662 0 1 1-15.079-15.079l74.662-74.662.807-.73a10.662 10.662 0 0 1 14.272.73l74.675 74.662a10.671 10.671 0 1 1-15.091 15.091l-56.448-56.46v123.584a10.669 10.669 0 0 1-21.338 0z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 设置弹窗 */}
      {settingsOpen && (
        <SettingsDialog
          settings={settings}
          onChange={setSettings}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </main>
  );
}
