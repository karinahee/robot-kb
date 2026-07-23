import { Sidebar } from '@/components/Sidebar';
import { ChatArea } from '@/components/ChatArea';
import { WikiPanel } from '@/components/WikiPanel';

export default function Home() {
  return (
    <div className="flex h-screen flex-col bg-white">
      {/* 顶部品牌栏 */}
      <header className="flex h-14 shrink-0 items-center border-b border-neutral-200 px-5">
        <h1 className="text-lg font-bold tracking-tight text-neutral-800">Robot-KB</h1>
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
