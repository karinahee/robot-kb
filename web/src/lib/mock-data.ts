// Mock 数据：静态页面展示用，后续替换为真实 API 数据

export interface SourceDoc {
  docId: string;
  title: string;
  sourceType: 'pdf' | 'web' | 'arxiv' | 'github';
  chunkCount: number;
}

export interface WikiEntry {
  id: string;
  title: string;
  summary: string;
  createdAt: string;
  tags: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: { index: number; title: string; chunkText: string }[];
}

export const mockSources: SourceDoc[] = [
  {
    docId: 'pdf_robocon_2026',
    title: '2026 ROBOCON 仿生足式机器人挑战赛规则',
    sourceType: 'pdf',
    chunkCount: 86,
  },
  {
    docId: 'pdf_learning_agile',
    title: 'Learning Agile Robotic Locomotion Skills by Imitating Animals',
    sourceType: 'pdf',
    chunkCount: 134,
  },
  {
    docId: 'arxiv_2004_00784',
    title: 'Learning bipedal robot locomotion',
    sourceType: 'arxiv',
    chunkCount: 92,
  },
];

export const mockWikiEntries: WikiEntry[] = [
  {
    id: 'wiki-1',
    title: '足式机器人运动控制方法概览',
    summary: '基于学习的运动控制主要分为模仿学习、强化学习与 sim-to-real 迁移三条路线……',
    createdAt: '07-23 15:20',
    tags: ['运动控制'],
  },
  {
    id: 'wiki-2',
    title: 'ROBOCON 障碍赛得分要点',
    summary: '障碍赛按越障数量计分，大斜坡要求两侧沿 3m 长边各行走不少于 1 米……',
    createdAt: '07-23 16:41',
    tags: ['比赛规则'],
  },
];

export const mockMessages: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: '大斜坡越障成功的定义是什么？',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content:
      '根据比赛规则，大斜坡越障成功的定义为：机器人在两侧斜坡上沿 3m 长边方向分别行走的距离不得少于 1 米 [1]。此外，大斜坡的角度在 V2.0 规则中已修改为 11.3° [2]。',
    citations: [
      {
        index: 1,
        title: '2026 ROBOCON 仿生足式机器人挑战赛规则',
        chunkText:
          '6.3 障碍赛表 2 中，对大斜坡越障成功的定义修改为"机器人在两侧斜坡上沿 3m 长边方向分别行走的距离不得少于 1 米"。',
      },
      {
        index: 2,
        title: '2026 ROBOCON 仿生足式机器人挑战赛规则',
        chunkText:
          '3.1 障碍赛场地中，"直角绕杆"的必达区修改为红色虚线圆；"大斜坡"的角度修改为 11.3°。',
      },
    ],
  },
];
