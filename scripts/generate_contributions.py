import json
import math
import os
import urllib.request
from collections import OrderedDict
from datetime import date, datetime, time, timezone
from pathlib import Path


USERNAME = os.getenv("GITHUB_USERNAME", "Ohm5656")
TOKEN = os.environ["GH_TOKEN"]

OUTPUT = Path("assets/yearly-contributions.svg")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


def shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = year * 12 + (month - 1) + offset
    return month_index // 12, month_index % 12 + 1


today = datetime.now(timezone.utc).date()

# 12 เดือนปฏิทิน รวมเดือนปัจจุบัน
start_year, start_month = shift_month(today.year, today.month, -11)
start_date = date(start_year, start_month, 1)

from_datetime = datetime.combine(
    start_date,
    time.min,
    tzinfo=timezone.utc,
).isoformat()

to_datetime = datetime.now(timezone.utc).isoformat()


query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
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
        "login": USERNAME,
        "from": from_datetime,
        "to": to_datetime,
    },
}).encode("utf-8")


request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "github-contribution-chart",
    },
)


with urllib.request.urlopen(request) as response:
    result = json.load(response)


if "errors" in result:
    raise RuntimeError(result["errors"])


calendar_data = (
    result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
)


# สร้าง 12 เดือน
monthly = OrderedDict()

for offset in range(12):
    year, month = shift_month(start_year, start_month, offset)
    monthly[(year, month)] = 0


# รวม contribution รายวัน → รายเดือน
for week in calendar_data["weeks"]:
    for day in week["contributionDays"]:
        day_date = date.fromisoformat(day["date"])
        key = (day_date.year, day_date.month)

        if key in monthly:
            monthly[key] += day["contributionCount"]


values = list(monthly.values())

month_names = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

labels = [
    month_names[month - 1]
    for year, month in monthly.keys()
]

total = sum(values)

# SVG dimensions
width = 1058
height = 400

left = 75
right = 45
top = 85
bottom = 70

chart_width = width - left - right
chart_height = height - top - bottom

max_value = max(values) if values else 1

# ปรับแกน Y ให้เป็นเลขสวย
step = max(10, math.ceil(max_value / 4 / 10) * 10)
y_max = max(step * 4, math.ceil(max_value / step) * step)


points = []

for index, value in enumerate(values):
    x = left + index * (chart_width / 11)
    y = top + chart_height - (value / y_max * chart_height)
    points.append((x, y))


line_points = " ".join(
    f"{x:.1f},{y:.1f}"
    for x, y in points
)

area_points = (
    f"{left},{top + chart_height} "
    + line_points
    + f" {left + chart_width},{top + chart_height}"
)


grid_lines = []
grid_labels = []

for index in range(5):
    value = y_max * index / 4
    y = top + chart_height - index * chart_height / 4

    grid_lines.append(
        f'<line x1="{left}" y1="{y:.1f}" '
        f'x2="{left + chart_width}" y2="{y:.1f}" '
        f'stroke="#2d3f63" stroke-width="1" opacity="0.7"/>'
    )

    grid_labels.append(
        f'<text x="{left - 15}" y="{y + 5:.1f}" '
        f'text-anchor="end" fill="#70a5fd" '
        f'font-size="13">{int(value)}</text>'
    )


month_elements = []
point_elements = []

for index, ((x, y), label, value) in enumerate(
    zip(points, labels, values)
):
    month_elements.append(
        f'<text x="{x:.1f}" y="{height - 30}" '
        f'text-anchor="middle" fill="#70a5fd" '
        f'font-size="14">{label}</text>'
    )

    point_elements.append(
        f'''
        <circle cx="{x:.1f}" cy="{y:.1f}" r="6"
                fill="#39d353"
                stroke="#1a1b27"
                stroke-width="3"/>

        <text x="{x:.1f}" y="{y - 14:.1f}"
              text-anchor="middle"
              fill="#c9d1d9"
              font-size="12"
              font-weight="600">{value}</text>
        '''
    )


svg = f"""<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}"
>
    <defs>
        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#39d353" stop-opacity="0.30"/>
            <stop offset="100%" stop-color="#39d353" stop-opacity="0.02"/>
        </linearGradient>

        <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge>
                <feMergeNode in="blur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>

    <rect
        width="100%"
        height="100%"
        rx="10"
        fill="#1a1b27"
    />

    <text
        x="{width / 2}"
        y="38"
        text-anchor="middle"
        fill="#70a5fd"
        font-size="20"
        font-weight="600"
    >
        Contributions — Last 12 Months
    </text>

    <text
        x="{width - 45}"
        y="38"
        text-anchor="end"
        fill="#39d353"
        font-size="14"
    >
        {total} contributions
    </text>

    {''.join(grid_lines)}
    {''.join(grid_labels)}

    <polygon
        points="{area_points}"
        fill="url(#areaGradient)"
    />

    <polyline
        points="{line_points}"
        fill="none"
        stroke="#39d353"
        stroke-width="4"
        stroke-linecap="round"
        stroke-linejoin="round"
        filter="url(#glow)"
    />

    {''.join(point_elements)}
    {''.join(month_elements)}
</svg>
"""


OUTPUT.write_text(svg, encoding="utf-8")

print("Generated:", OUTPUT)
print("Monthly contributions:", values)
print("Total:", total)