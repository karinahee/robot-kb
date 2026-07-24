import { Sidebar } from '@/components/Sidebar';
import { ChatArea } from '@/components/ChatArea';
import { WikiPanel } from '@/components/WikiPanel';
import { Icon } from '@/components/Icon';

export default function Home() {
  return (
    <div className="flex h-screen flex-col bg-white">
      {/* 顶部品牌栏 */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-neutral-200 px-5">
        <div className="flex items-center gap-2">
          <Icon name="exploration" size={22} />
          <h1 className="text-lg font-bold tracking-tight text-neutral-800">Robot-KB</h1>
        </div>
        <div className="flex items-center gap-1">
          <button
            className="rounded-full p-1.5 text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700"
            title="切换语言"
          >
            <Icon name="language" size={16} />
          </button>
          <button
            className="rounded-full p-1.5 text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700"
            title="更多"
          >
            <Icon name="more2" size={16} />
          </button>
        </div>
      </header>

      {/* 三栏主体 */}
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <ChatArea />
        <WikiPanel />
      </div>
    </div>
  );
}
