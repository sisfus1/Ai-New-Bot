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