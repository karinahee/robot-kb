# Robot-KB

机器人领域知识库 RAG 系统。支持 PDF / 网页 / arXiv / GitHub 多源入库，向量检索 + Rerank + LLM 生成回答。

## 环境要求

- Python 3.10+
- Node.js 18+（仅前端需要）

## 快速开始

### 1. 下载代码

```bash
git clone https://github.com/karinahee/robot-kb.git
cd robot-kb
```

### 2. 创建虚拟环境并安装依赖

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 并重命名为 `.env`，填入你自己的密钥：

```bash
cp .env.example .env
```

需要配置的内容：

| 变量 | 说明 | 获取地址 |
|------|------|----------|
| `SILICONFLOW_API_KEY` | SiliconFlow API 密钥（Embedding / Rerank / Chat 都走这里） | https://cloud.siliconflow.cn |
| `SUPABASE_URL` | Supabase 项目 URL | Supabase 项目 Settings → API |
| `SUPABASE_SERVICE_KEY` | Supabase service_role 密钥 | 同上 |
| `PostgreSQL` | Supabase Session Pooler 连接串 | Supabase 项目 Settings → Database → Connection string |

### 4. 初始化数据库

```bash
python scripts/setup_db.py
```

### 5. 启动 Streamlit

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501

## 前端（Next.js，可选）

前端是独立的高颜值界面，位于 `web/` 目录，目前为静态 UI（暂未接后端 API）：

```bash
cd web
npm install
npm run dev
```

浏览器打开 http://localhost:3000 

## 目录结构

```
robot-kb/
├── app.py                # Streamlit 测试界面（RAG 链路入口）
├── ingestion/            # 入库链路：提取 → 切分 → 向量化 → 写库
│   ├── extractors/       #   pdf / web / arxiv / github 提取器
│   ├── chunkers/         #   切分与校验
│   ├── embedding.py      #   SiliconFlow 向量化
│   ├── store.py          #   Supabase 读写
│   └── pipeline.py       #   入库编排
├── retrieval/            # 检索：多查询扩展 + Rerank
├── scripts/setup_db.py   # 数据库初始化脚本
├── web/                  # Next.js 前端（静态 UI）
├── experience_data/      # 实验用 PDF 数据
└── experience_record/    # 实验记录 notebook
```

## 常见问题

**换电脑/换系统怎么迁移？**
代码直接从 GitHub 克隆即可，按上面步骤重新装依赖。`.env` 不在仓库里，需要单独拷贝或按 `.env.example` 重新填写。数据都在 Supabase 云端，不受影响。

**`pip install` 报错？**
确认 Python 版本 ≥ 3.10，且已激活虚拟环境（终端前缀有 `(.venv)`）。
