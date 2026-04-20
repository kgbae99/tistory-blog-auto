import os, re, json, feedparser, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / "config" / ".env")
except ImportError:
    pass

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

KW = ["\uac74\uac15", "\uc758\ub8cc", "\ubcd1\uc6d0", "\uc9c8\ubcd1", "\uce58\ub8cc", "\uc608\ubc29", "\uc218\uc220", "\uc57d", "\uc554", "\ub2f9\ub1e8", "\ud608\uc555", "\uc2ec\uc7a5", "\ub1cc", "\uba74\uc5ed", "\uc601\uc591", "\uc2dd\ub2e8", "\uc6b4\ub3d9", "\ub2e4\uc774\uc5b4\ud2b8", "\uc218\uba74", "\uc2a4\ud2b8\ub808\uc2a4", "\ubc31\uc2e0", "\ube44\ud0c0\ubbfc", "\ub178\uc778", "\uc5b4\ub9b0\uc774", "\uc784\uc2e0", "\ud53c\ubd80", "\ub208", "\uce58\uc544", "\ube44\ub9cc", "\ud1b5\uc99d"]

RSS_SOURCES = [
    ("yna_health", "https://www.yna.co.kr/rss/health.xml"),
    ("docdoc", "https://www.docdocdoc.co.kr/rss/allArticle.xml"),
    ("hkn24", "https://www.hkn24.com/rss/allArticle.xml"),
    ("newsis", "https://newsis.com/RSS/health.xml"),
    ("kormedi", "https://kormedi.com/feed/"),
]

DAY_KO = {"Mon":"\uc6d4","Tue":"\ud654","Wed":"\uc218","Thu":"\ubaa9","Fri":"\uae08","Sat":"\ud1a0","Sun":"\uc77c"}

def get_date_str(dt):
    day = DAY_KO.get(dt.strftime("%a"), "")
    return dt.strftime("%Y\ub144 %m\uc6d4 %d\uc77c (") + day + ")"

def fetch_news(count=7):
    collected = []
    for name, url in RSS_SOURCES:
        if len(collected) >= count: break
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            added = 0
            for e in feed.entries:
                if len(collected) >= count: break
                t = e.get("title","").strip()
                l = e.get("link","")
                if not any(k in t for k in KW): continue
                if any(c["title"]==t for c in collected): continue
                collected.append({"title":t,"link":l,"source":name})
                added += 1
            if feed.entries: print(f"  [OK] {name}: {len(feed.entries)} / +{added}")
            else: print(f"  [NG] {name}: 0")
        except Exception as ex: print(f"  [NG] {name}: {ex}")
    return collected[:count]

def add_comments(news_list):
    titles = "\n".join(f"{i+1}. {n['title']}" for i,n in enumerate(news_list))
    sys_msg = "\uac74\uac15 \ube14\ub85c\uadf8 \uac74\uac15\uc628\ub3c4\uc0ac \uc6b4\uc601\uc790\uc785\ub2c8\ub2e4. \uac01 \ub274\uc2a4\uc5d0 \ub3c5\uc790(30~60\ub300)\uc5d0\uac8c \uce5c\uadfc\ud55c \ud55c\uc904 \ucf54\uba58\ud2b8\ub97c 20~35\uc790\ub85c \uc791\uc131. JSON \ubc30\uc5f4\ub9cc \ucd9c\ub825: [\"comment1\", ...]"
    usr_msg = f"{len(news_list)} \uac1c \ub274\uc2a4\uc5d0 \ucf54\uba58\ud2b8:\n{titles}"
    r = client.chat.completions.create(
        model="gpt-4o", temperature=0.7,
        messages=[{"role":"system","content":sys_msg},{"role":"user","content":usr_msg}]
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$","",r.choices[0].message.content.strip(),flags=re.M)
    comments = json.loads(raw)
    for i,n in enumerate(news_list): n["comment"] = comments[i] if i<len(comments) else ""
    return news_list

def get_font(size):
    for p in ["C:/Windows/Fonts/malgunbd.ttf","C:/Windows/Fonts/malgun.ttf",
              "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
              "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def make_thumbnail(date_str, path):
    W,H = 800,450
    img = Image.new("RGB",(W,H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r=int(10+(5-10)*(y/H)); g=int(42+(21-42)*(y/H)); b=int(74+(58-74)*(y/H))
        draw.line([(0,y),(W,y)],fill=(r,g,b))
    draw.ellipse([580,-80,900,240],outline=(26,106,170),width=3)
    draw.ellipse([600,-60,880,220],outline=(26,90,154),width=2)
    fd,fs,fm,ft = get_font(28),get_font(44),get_font(62),get_font(24)
    draw.text((40,35),  date_str,       font=fd, fill=(125,211,252))
    draw.text((40,100), "\uc624\ub298\uc758",       font=fs, fill=(255,255,255))
    draw.text((40,158), "\uac74\uac15\ub274\uc2a4",      font=fm, fill=(56,189,248))
    draw.rounded_rectangle([40,268,230,308],radius=8,fill=(56,189,248))
    draw.text((52,274), "\uc2a4\ud06c\ub7a9",      font=get_font(34), fill=(10,42,74))
    draw.line([(40,358),(760,358)],fill=(26,90,154),width=1)
    draw.text((40,370),  "\uac74\uac15\uc628\ub3c4\uc0ac",      font=ft, fill=(148,163,184))
    draw.text((510,370), "\uac74\uac15\ud55c \ud558\ub8e8\ub97c \uc704\ud55c \uc815\ubcf4",     font=ft, fill=(100,116,139))
    img.save(path,"JPEG",quality=92)
    print(f"  thumb: {path}")

def build_html(news_list, date_str):
    h = []
    h.append(f'<p style="color:#64748b;font-size:14px;margin-bottom:24px">📅 {date_str} \uc8fc\uc694 \uac74\uac15\ub274\uc2a4\ub97c \ubaa8\uc558\uc2b5\ub2c8\ub2e4.</p>')
    h.append('<div style="background:#f0f9ff;border-left:4px solid #38bdf8;padding:14px 18px;margin-bottom:28px;border-radius:0 8px 8px 0"><strong style="color:#0369a1">\uc624\ub298 \uc774\uac83\ub9cc \ud655\uc778\ud558\uc790!</strong></div>')
    for n in news_list:
        t,l,c,s = n["title"],n["link"],n.get("comment",""),n.get("source","")
        h.append('<div style="margin-bottom:20px;padding:16px 18px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.06)">')
        h.append('<p style="margin:0 0 6px;font-size:15px;font-weight:700;color:#1e293b"><span style="color:#38bdf8;margin-right:6px">&#9679;</span>')
        h.append(f'<a href="{l}" target="_blank" style="color:#1e293b;text-decoration:none">{t}</a>' if l else t)
        h.append("</p>")
        if c: h.append(f'<p style="margin:4px 0 0 20px;font-size:13px;color:#64748b">💬 {c}</p>')
        if s: h.append(f'<p style="margin:4px 0 0 20px;font-size:11px;color:#94a3b8">\ucd9c\ucc98: {s}</p>')
        h.append("</div>")
    h.append('<p style="margin-top:32px;padding:14px;background:#f8fafc;border-radius:8px;font-size:13px;color:#64748b;text-align:center">📌 \uac74\uac15\uc628\ub3c4\uc0ac\ub294 \ub9e4\uc77c \uc544\uce68 \uac74\uac15\ub274\uc2a4\ub97c \ubaa8\uc544 \uc804\ub2ec\ud569\ub2c8\ub2e4.<br>\uc815\ud655\ud55c \ub0b4\uc6a9\uc740 \uac01 \uae30\uc0ac \uc6d0\ubb38\uc744 \ud655\uc778\ud574 \uc8fc\uc138\uc694.</p>')
    return "\n".join(h)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",  default=None)
    parser.add_argument("--count", type=int, default=7)
    parser.add_argument("--outdir",default="health_news_posts")
    # output/posts/YYYY-MM-DD/ 경로 (multi_blog_reserve_upload.py 연동)
    parser.add_argument("--posts-dir", default=r"C:\Users\CleanAdmin\Desktop\claude\blog\output\posts")
    args = parser.parse_args()

    KST = timezone(timedelta(hours=9))
    dt = datetime.strptime(args.date,"%Y%m%d").replace(tzinfo=KST) if args.date else datetime.now(KST)
    date_str  = get_date_str(dt)
    date_file = dt.strftime("%Y%m%d")
    today_folder = dt.strftime("%Y-%m-%d")

    print("="*50)
    print("  \uac74\uac15\uc628\ub3c4\uc0ac | \uc624\ub298\uc758 \uac74\uac15\ub274\uc2a4")
    print(f"  {date_str}")
    print("="*50)

    os.makedirs(args.outdir, exist_ok=True)

    print(f"\n[1] \ub274\uc2a4 \uc218\uc9d1...")
    news = fetch_news(args.count)
    print(f"  -> {len(news)}\uac74")

    print(f"\n[2] GPT \ucf54\uba58\ud2b8...")
    news = add_comments(news)

    print(f"\n[3] \uc378\ub124\uc77c...")
    thumb = os.path.join(args.outdir, f"{date_file}_thumb.jpg")
    make_thumbnail(date_str, thumb)

    print(f"\n[4] \ubcf8\ubb38 \uc0dd\uc131...")
    content = build_html(news, date_str)
    title   = f"{date_str} \uc8fc\uc694 \uac74\uac15\ub274\uc2a4 | \uc624\ub298 \uaf2d \uc54c\uc544\uc57c \ud560 \uac74\uac15 \uc18c\uc2dd"

    # [5] HTML 파일 저장 → output/posts/YYYY-MM-DD/ (업로드 스크립트 연동)
    print(f"\n[5] HTML \uc800\uc7a5 (upload \uc5f0\ub3d9)...")
    html_dir = os.path.join(args.posts_dir, today_folder)
    os.makedirs(html_dir, exist_ok=True)

    # 썸네일을 base64로 인코딩 → upload 스크립트 클립보드 업로드 연동
    import base64
    with open(thumb, "rb") as _f:
        thumb_b64 = base64.b64encode(_f.read()).decode("utf-8")
    thumb_src = f"data:image/jpeg;base64,{thumb_b64}"
    html_full = (
        f'<html><head><meta charset="utf-8"><title>{title}</title></head><body>\n'
        f'<img src="{thumb_src}" alt="\uc624\ub298\uc758 \uac74\uac15\ub274\uc2a4 \uc378\ub124\uc77c" '
        f'style="width:100%;max-width:800px;display:block;margin:0 auto 24px">\n'
        f'{content}\n</body></html>'
    )
    html_path = os.path.join(html_dir, f"{date_file}_health_news.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_full)
    print(f"  -> {html_path}")

    # JSON도 보조 저장
    post = {
        "title":      title,
        "category":   "\uc624\ub298\uc758 \uac74\uac15\ub274\uc2a4",
        "tags":       ["\uac74\uac15\ub274\uc2a4","\uc624\ub298\uc758\uac74\uac15","\uc758\ub8cc\ub274\uc2a4","\uac74\uac15\uc815\ubcf4","\uac74\uac15\uc628\ub3c4\uc0ac"],
        "content":    content,
        "thumbnail":  thumb,
        "html_path":  html_path,
        "news_items": news,
        "generated_at": dt.strftime("%Y-%m-%d %H:%M"),
    }
    jpath = os.path.join(args.outdir, f"{date_file}_health_news.json")
    with open(jpath,"w",encoding="utf-8") as f: json.dump(post,f,ensure_ascii=False,indent=2)

    print(f"\n{'='*50}")
    print(f"  \uc644\ub8cc!")
    print(f"  HTML: {html_path}")
    print(f"  JSON: {jpath}")
    print(f"  \ub274\uc2a4: {len(news)}\uac74")
    for i,n in enumerate(news,1): print(f"  {i}. {n['title']}")
    print(f"\n  \ub2e4\uc74c: multi_blog_reserve_upload.py --blog posts \uc2e4\ud589")

if __name__ == "__main__":
    main()