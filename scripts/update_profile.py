#!/usr/bin/env python3
"""Daily profile refresh: Bing image of the day + self-generated stats cards."""
import json, os, re, urllib.request, html
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
PROFILE = os.path.join(ROOT, "profile")
USER = os.environ.get("GH_USER", "meetjym")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
UA = {"User-Agent": "Mozilla/5.0 meetjym-profile"}

def get(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def replace_block(text, tag, body):
    pat = re.compile(rf"(<!-- {tag}:START -->)(.*?)(<!-- {tag}:END -->)", re.S)
    return pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)

def bing():
    data = json.loads(get("https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN"))
    img = data["images"][0]
    url = "https://www.bing.com" + img["urlbase"] + "_1920x1080.jpg"
    with open(os.path.join(PROFILE, "bing.jpg"), "wb") as f:
        f.write(get(url))
    title = html.escape(img.get("title") or "")
    cr = html.escape(img.get("copyright") or "")
    d = img.get("enddate", "")
    d = f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else d
    return (f'<p align="center">\n  <img width="100%" src="./profile/bing.jpg" alt="Bing daily wallpaper" />\n</p>\n'
            f'<p align="center"><sub>🖼️ 必应每日一图 Bing Daily · {d} · {title}<br/>{cr}</sub></p>')

def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    return json.loads(get("https://api.github.com/graphql",
        {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}, body))["data"]

CARD = '''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="170" viewBox="0 0 {w} 170">
<style>.t{{font:600 17px 'Segoe UI',Ubuntu,sans-serif;fill:#70a5fd}}.l{{font:400 13px 'Segoe UI',Ubuntu,sans-serif;fill:#a9b1d6}}.v{{font:700 13px 'Segoe UI',Ubuntu,sans-serif;fill:#c0caf5}}</style>
<rect width="{w}" height="170" rx="6" fill="#1a1b27"/>
<text x="20" y="32" class="t">{title}</text>
{rows}
</svg>'''

def stats():
    q = """query($login:String!){user(login:$login){
      contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions contributionCalendar{totalContributions}}
      followers{totalCount}
      repositories(first:100,ownerAffiliations:OWNER,isFork:false){totalCount nodes{stargazerCount
        languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}"""
    u = gql(q, {"login": USER})["user"]
    cc = u["contributionsCollection"]
    repos = u["repositories"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])
    items = [("⭐ Stars", stars), ("📦 Repositories", repos["totalCount"]),
             ("📝 Commits (1y)", cc["totalCommitContributions"]),
             ("🔀 Pull requests (1y)", cc["totalPullRequestContributions"]),
             ("📈 Contributions (1y)", cc["contributionCalendar"]["totalContributions"])]
    rows = "\n".join(f'<text x="20" y="{60+i*22}" class="l">{k}</text><text x="300" y="{60+i*22}" class="v" text-anchor="end">{v}</text>'
                     for i, (k, v) in enumerate(items))
    open(os.path.join(PROFILE, "stats.svg"), "w").write(CARD.format(w=320, title=f"{USER}'s GitHub Stats", rows=rows))
    langs = {}
    for n in repos["nodes"]:
        for e in n["languages"]["edges"]:
            nm = e["node"]["name"]; langs.setdefault(nm, [0, e["node"]["color"] or "#888"]); langs[nm][0] += e["size"]
    top = sorted(langs.items(), key=lambda x: -x[1][0])[:5]
    total = sum(v[0] for _, v in top) or 1
    if not top:
        rows = '<text x="20" y="70" class="l">暂无代码 / No code yet</text>'
    else:
        rows = "\n".join(f'<circle cx="26" cy="{56+i*22}" r="5" fill="{c}"/><text x="38" y="{60+i*22}" class="l">{html.escape(nm)}</text>'
                         f'<text x="260" y="{60+i*22}" class="v" text-anchor="end">{s*100/total:.1f}%</text>'
                         for i, (nm, (s, c)) in enumerate(top))
    open(os.path.join(PROFILE, "top-langs.svg"), "w").write(CARD.format(w=280, title="Top Languages", rows=rows))

def main():
    os.makedirs(PROFILE, exist_ok=True)
    text = open(README, encoding="utf-8").read()
    text = replace_block(text, "BING", bing())
    if TOKEN:
        stats()
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    text = replace_block(text, "UPDATED", f'<p align="center"><sub>🕒 更新于 Updated: {now} (UTC+8)</sub></p>')
    open(README, "w", encoding="utf-8").write(text)

if __name__ == "__main__":
    main()
