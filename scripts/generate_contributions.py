import json
import math
import os
import random
import urllib.request
from pathlib import Path


USERNAME = os.getenv("GITHUB_USERNAME", "Ohm5656")
TOKEN = os.environ["GH_TOKEN"]

# ใช้ชื่อเดิม เพื่อไม่ต้องแก้ README / Workflow
OUTPUT = Path("assets/yearly-contributions.svg")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────
# GitHub Contribution Data
# ─────────────────────────────────────

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

payload = json.dumps({
    "query": query,
    "variables": {
        "login": USERNAME
    }
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "github-contribution-meadow",
    },
)

with urllib.request.urlopen(request) as response:
    result = json.load(response)

if "errors" in result:
    raise RuntimeError(result["errors"])

calendar = (
    result["data"]["user"]["contributionsCollection"]
    ["contributionCalendar"]
)

total = calendar["totalContributions"]

days = []

for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        days.append({
            "date": day["date"],
            "count": day["contributionCount"],
            "color": day["color"],
        })

days.sort(key=lambda d: d["date"])

if not days:
    raise RuntimeError("No contribution data returned")


# ─────────────────────────────────────
# SVG Settings
# ─────────────────────────────────────

WIDTH = 1080
HEIGHT = 330

LEFT = 35
RIGHT = 35

GROUND_Y = 250
MEADOW_WIDTH = WIDTH - LEFT - RIGHT

max_count = max(day["count"] for day in days)
max_count = max(max_count, 1)

spacing = MEADOW_WIDTH / max(len(days) - 1, 1)


# ─────────────────────────────────────
# Generate Grass
# ─────────────────────────────────────

grass = []
highlights = []

for i, day in enumerate(days):
    count = day["count"]
    x = LEFT + i * spacing

    # ใช้วันที่เป็น seed → รูปร่างหญ้าเดิมทุกครั้ง
    rng = random.Random(day["date"])

    if count == 0:
        height = rng.uniform(3, 7)
        color = "#21262d"
        opacity = 0.45
        blade_count = 1
    else:
        # log scale กันวันที่ commit เยอะมากจนหญ้าสูงเกิน
        strength = math.log1p(count) / math.log1p(max_count)

        height = 10 + strength * 75
        color = day["color"]
        opacity = 0.95

        if count >= 8:
            blade_count = 4
        elif count >= 4:
            blade_count = 3
        elif count >= 2:
            blade_count = 2
        else:
            blade_count = 1

    for blade in range(blade_count):
        offset = rng.uniform(-1.5, 1.5)
        blade_height = height * rng.uniform(0.70, 1.05)
        lean = rng.uniform(-2.8, 2.8)

        x1 = x + offset
        y1 = GROUND_Y
        x2 = x1 + lean
        y2 = GROUND_Y - blade_height

        grass.append(
            f'''
            <line
                x1="{x1:.2f}"
                y1="{y1:.2f}"
                x2="{x2:.2f}"
                y2="{y2:.2f}"
                stroke="{color}"
                stroke-width="1.7"
                stroke-linecap="round"
                opacity="{opacity}"
            />
            '''
        )

    # วันที่ activity สูงมาก ให้มี glow เล็กน้อย
    if count > 0:
        strength = math.log1p(count) / math.log1p(max_count)

        if strength > 0.78:
            highlights.append(
                f'''
                <circle
                    cx="{x:.2f}"
                    cy="{GROUND_Y - height - 4:.2f}"
                    r="2"
                    fill="{color}"
                    opacity="0.8"
                    filter="url(#glow)"
                />
                '''
            )


# ─────────────────────────────────────
# Month Labels
# ─────────────────────────────────────

months = []
seen_months = set()

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr",
    "May", "Jun", "Jul", "Aug",
    "Sep", "Oct", "Nov", "Dec"
]

for i, day in enumerate(days):
    year, month, date = map(int, day["date"].split("-"))
    key = (year, month)

    if key not in seen_months:
        seen_months.add(key)

        x = LEFT + i * spacing

        months.append(
            f'''
            <text
                x="{x:.2f}"
                y="286"
                fill="#8b949e"
                font-size="11"
                font-family="Arial, sans-serif"
            >
                {MONTH_NAMES[month - 1]}
            </text>
            '''
        )


# ─────────────────────────────────────
# SVG
# ─────────────────────────────────────

svg = f"""
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{WIDTH}"
    height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}"
>

<defs>

    <linearGradient id="background" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#0d1117"/>
        <stop offset="100%" stop-color="#0b120e"/>
    </linearGradient>

    <linearGradient id="groundGlow" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#39d353" stop-opacity="0.18"/>
        <stop offset="100%" stop-color="#39d353" stop-opacity="0"/>
    </linearGradient>

    <filter id="glow">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
    </filter>

</defs>


<!-- Background -->

<rect
    width="100%"
    height="100%"
    rx="14"
    fill="url(#background)"
/>


<!-- Header -->

<text
    x="35"
    y="46"
    fill="#f0f6fc"
    font-size="19"
    font-weight="600"
    font-family="Arial, sans-serif"
>
    Contribution Meadow
</text>


<text
    x="{WIDTH - 35}"
    y="46"
    text-anchor="end"
    fill="#39d353"
    font-size="13"
    font-family="Arial, sans-serif"
>
    {total:,} contributions
</text>


<!-- subtle horizon -->

<rect
    x="0"
    y="{GROUND_Y - 15}"
    width="{WIDTH}"
    height="70"
    fill="url(#groundGlow)"
/>


<!-- grass -->

{''.join(grass)}


<!-- high activity glow -->

{''.join(highlights)}


<!-- Ground -->

<line
    x1="25"
    y1="{GROUND_Y + 1}"
    x2="{WIDTH - 25}"
    y2="{GROUND_Y + 1}"
    stroke="#238636"
    stroke-width="2"
    opacity="0.35"
/>


<!-- Months -->

{''.join(months)}


<!-- Footer -->

<text
    x="{WIDTH / 2}"
    y="313"
    text-anchor="middle"
    fill="#484f58"
    font-size="10"
    font-family="Arial, sans-serif"
>
    GitHub activity · last year
</text>

</svg>
"""

OUTPUT.write_text(svg, encoding="utf-8")

print("Generated:", OUTPUT)
print("Days:", len(days))
print("Total contributions:", total)
