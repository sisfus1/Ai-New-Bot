<<<<<<< HEAD
import os
import uuid
import asyncio # 确保有这个
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware # 【新增】导入跨域中间件
from pydantic import BaseModel
import uvicorn
from fastapi.responses import FileResponse
# (确保你之前已经导入了 os)

# 导入你的服务逻辑
from app.db.database import DatabaseManager
from app.services.llm import LLMService
from app.services.media import MediaService
from moviepy.editor import ColorClip

app = FastAPI(title="Auto-Media-Agent API", version="0.4.0")
# 【新增】配置 CORS，允许前端 5173 端口访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # 允许的请求来源
    allow_credentials=True,
    allow_methods=["*"], # 允许所有 HTTP 方法 (GET, POST 等)
    allow_headers=["*"], # 允许所有请求头
)

# --- 1. 定义数据模型 (Pydantic) ---
class VideoTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

# 模拟一个内存中的任务状态字典（未来会被 Redis + Celery 替代）
TASK_STORE = {}

# --- 2. 核心业务逻辑封装为独立函数 ---
def run_video_generation_pipeline(task_id: str):
    """这是原本 main.py 中的核心逻辑，现在放到后台运行"""
    TASK_STORE[task_id] = "RUNNING"
    print(f"[{task_id}] 🚀 后台任务开始执行...")
    
    try:
        db = DatabaseManager()
        llm = LLMService()
        media = MediaService()

        # 1. 获取数据
        recent_news = db.get_recent_news(limit=5)
        if not recent_news:
            TASK_STORE[task_id] = "FAILED: 数据库为空"
            return
            
        news_for_ai = [f"- {row[0]}: {row[1]}" for row in recent_news]
        
        # 2. AI 分析
        report = asyncio.run(llm.generate_daily_report(news_for_ai))
        if "top_news" not in report:
            TASK_STORE[task_id] = "FAILED: AI 生成报告失败"
            return
            
        # 3. 拼接口播
        script = f"大家好，今天是{report.get('date')}。{report.get('editor_comment')}。"
        for i, item in enumerate(report['top_news']):
            script += f"第{i+1}条：{item['title']}。{item['summary']}。"
        
        # 4. 生成语音与视频
        audio_file = media.generate_audio(script)
        if not audio_file:
            TASK_STORE[task_id] = "FAILED: 语音生成失败"
            return

        bg_image = "background.jpg"
        if not os.path.exists(bg_image):
            ColorClip(size=(1280, 720), color=(10, 20, 60), duration=5).save_frame(bg_image, t=1)

        video_file = media.generate_video(audio_file, bg_image)
        if video_file:
            TASK_STORE[task_id] = f"SUCCESS: {os.path.abspath(video_file)}"
            print(f"[{task_id}] 🎉 视频生成完成！")
        else:
            TASK_STORE[task_id] = "FAILED: 视频合成失败"

    except Exception as e:
        TASK_STORE[task_id] = f"ERROR: {str(e)}"
    finally:
        # 这里应该做一些资源清理，比如 db.close() 等
        pass

# --- 3. API 路由定义 ---
@app.post("/api/tasks/generate_video", response_model=VideoTaskResponse)
async def create_video_task(background_tasks: BackgroundTasks):
    """
    触发视频生成的接口。它会立即返回一个 task_id，而真正的生成过程在后台进行。
    """
    # 生成唯一任务 ID
    task_id = str(uuid.uuid4())
    TASK_STORE[task_id] = "PENDING"
    
    # 将重任务放入 FastAPI 的后台队列中
    background_tasks.add_task(run_video_generation_pipeline, task_id)
    
    return VideoTaskResponse(
        task_id=task_id, 
        status="PENDING", 
        message="视频生成任务已提交后台处理"
    )

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """前端轮询查询任务状态的接口"""
    status = TASK_STORE.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": status}

@app.get("/api/videos/{filename}")
async def get_video(filename: str):
    """专门为前端提供视频流的接口"""
    # 因为我们的视频直接生成在项目根目录下，所以直接查 filename
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="视频文件未找到或已被删除")
    
    # 返回视频文件，FastAPI 会自动处理视频的拖拽缓冲(流式传输)
    return FileResponse(filename, media_type="video/mp4")

if __name__ == "__main__":
    # 启动命令: python api_main.py (或者 uvicorn api_main:app --reload)
    uvicorn.run(app, host="0.0.0.0", port=8000)
=======
import feedparser
import os
import json
import requests
import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 1. 加载环境变量
load_dotenv()

# 2. 配置 DeepSeek 客户端 (注意 /v1 尾缀)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), 
    base_url="https://api.deepseek.com/v1"
)

# 3. 配置 PushPlus
PUSH_TOKEN = os.getenv("PUSHPLUS_TOKEN")

# 4. 资讯源配置 (保留 Hacker News 等高质量源)
RSS_URLS = [
    "https://www.theverge.com/rss/ai/index.xml", 
    "https://news.ycombinator.com/rss",          
    "https://openai.com/blog/rss.xml",           
    "https://dev.to/feed/tag/ai",                
    "https://www.artificialintelligence-news.com/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
]

def fetch_rss_data():
    """阶段一：海量抓取 (ETL - Extract)"""
    print("🌍 正在扫描全球 AI 资讯...")
    raw_items = []
    
    for url in RSS_URLS:
        try:
            # 增加 User-Agent 防止被某些网站拦截
            feed = feedparser.parse(url, agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            # 每个源多抓一点，给 AI 足够的筛选空间
            for entry in feed.entries[:10]: 
                # 简单清洗：必须包含 ai 关键词 (针对 HN 这种综合源)
                if 'ycombinator' in url:
                    keywords = ['ai', 'gpt', 'llm', 'model', 'diffusion', 'cursor', 'windsurf']
                    if not any(k in entry.title.lower() for k in keywords):
                        continue
                
                raw_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.summary[:200] if hasattr(entry, 'summary') else entry.title
                })
        except Exception as e:
            print(f"⚠️ 源读取失败 {url}: {e}")
            
    print(f"📥 共收集到 {len(raw_items)} 条原始资讯，准备发送给 DeepSeek...")
    return raw_items

def analyze_and_structure(raw_items):
    """阶段二：AI 思考与结构化 (ETL - Transform)"""
    if not raw_items:
        return None

    # 构造 Prompt：强制要求返回 JSON 格式
    prompt = f"""
    你是一个 AI 资讯数据库管理员。请分析以下新闻，筛选出**最重要的 10 条**，并**严格输出标准的 JSON 格式**。

    【处理要求】：
    1. **去重与筛选**：优先选择模型发布(DeepSeek/OpenAI/Claude)、大厂动态、GitHub高星项目。
    2. **分类标准**：
       - "🔥头条": 最重大的 1-2 条新闻。
       - "🛠️工具": AI 编程工具、效率工具、开源库。
       - "🎨视觉": 文生图、视频生成、设计类。
       - "📰行业": 商业新闻、政策、观点。
    3. **JSON 结构**：
       返回一个对象，包含 key "news_list"，其值为一个列表。列表中的每个元素包含：
       - "title": 中文标题 (简练有力)
       - "summary": 中文摘要 (30字以内)
       - "category": 上述分类之一
       - "score": 热度打分 (1-10的整数)
       - "link": 原始链接
    
    【输入数据】：
    {str(raw_items)}
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat", # 使用 V3 模型
            messages=[{"role": "user", "content": prompt}],
            response_format={ 'type': 'json_object' }, # 🔥 关键：强制 JSON 模式
            temperature=0.3
        )
        # 将 AI 返回的字符串转换为 Python 字典
        structured_data = json.loads(response.choices[0].message.content)
        return structured_data.get("news_list", [])
    except Exception as e:
        print(f"❌ AI 分析失败: {e}")
        return None

def save_database(news_list):
    """阶段三：存入数据库 (ETL - Load)"""
    if not news_list:
        return
    
    # 构造完整的数据库记录
    db_record = {
        "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "date": datetime.date.today().strftime("%Y-%m-%d"),
        "total": len(news_list),
        "news": news_list
    }

    # 写入 data.json (这就相当于你的后端数据库文件)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(db_record, f, ensure_ascii=False, indent=2)
    
    print(f"💾 数据库已更新: data.json (包含 {len(news_list)} 条记录)")
    return db_record

def push_notification(db_record):
    """阶段四：消息推送 (Notification)"""
    if not PUSH_TOKEN or not db_record:
        return

    # 构造推送内容 (简化版，引导用户看“App”)
    today = db_record['date']
    news = db_record['news']
    
    # 这里我们生成一段 HTML，PushPlus 支持 HTML 渲染
    # 这只是一个“通知”，详细内容以后在前端网页看
    html_content = f"<h3>🤖 AI 日报已更新 ({today})</h3>"
    html_content += "<p>以下是今日精选 Top 5：</p><ul>"
    
    # 只取前 5 条作为摘要
    for item in news[:5]:
        icon = item['category'][:1] # 取 Emoji
        html_content += f"<li>{icon} <b>{item['title']}</b><br><span style='font-size:12px;color:#666'>{item['summary']}</span></li>"
    
    html_content += "</ul>"
    html_content += f"<br><a href='http://www.pushplus.plus/'>👉 点击查看完整图文版 (请配置GitHub Pages)</a>"

    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSH_TOKEN,
        "title": f"AI 日报更新 ({today})",
        "content": html_content,
        "template": "html" # 使用 HTML 模板
    }
    
    try:
        requests.post(url, json=data)
        print("✅ 推送成功！")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

if __name__ == "__main__":
    # 1. 获取原始数据
    raw_data = fetch_rss_data()
    
    # 2. AI 处理并结构化
    structured_news = analyze_and_structure(raw_data)
    
    # 3. 存入本地数据库 (data.json)
    if structured_news:
        record = save_database(structured_news)
        
        # 4. 发送通知
        push_notification(record)
    else:
        print("⚠️ 今日无有效数据，跳过更新。")
>>>>>>> 26174d9a8be5a7448b6af247006c1f895ac549ff
