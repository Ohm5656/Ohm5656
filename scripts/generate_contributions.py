import hashlib
import json
import math
import os
import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


USERNAME = os.getenv("GITHUB_USERNAME", "Ohm5656")
TOKEN = os.environ["GH_TOKEN"]

GIF_OUTPUT = Path("assets/contribution-meadow.gif")
JSON_OUTPUT = Path("docs/contributions.json")

GIF_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# GitHub Contribution Data
# ─────────────────────────────────────────────

QUERY = """
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
    "query": QUERY,
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
        "User-Agent": "github-activity-garden",
    },
)

with urllib.request.urlopen(request) as response:
    result = json.load(response)

if "errors" in result:
    raise RuntimeError(result["errors"])

calendar = (
    result["data"]["user"]
    ["contributionsCollection"]
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

days.sort(key=lambda item: item["date"])

if not days:
    raise RuntimeError("GitHub returned no contribution data.")


# ─────────────────────────────────────────────
# Save data for interactive GitHub Pages
# ─────────────────────────────────────────────

JSON_OUTPUT.write_text(
    json.dumps(
        {
            "username": USERNAME,
            "total": total,
            "days": days,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


# ─────────────────────────────────────────────
# GIF Configuration
# ─────────────────────────────────────────────

WIDTH = 1080
HEIGHT = 330

LEFT = 40
RIGHT = 40

GROUND_Y = 247

FRAME_COUNT = 18
FRAME_DURATION = 85

max_count = max(day["count"] for day in days)
max_count = max(max_count, 1)

MEADOW_WIDTH = WIDTH - LEFT - RIGHT
spacing = MEADOW_WIDTH / max(len(days) - 1, 1)


# ─────────────────────────────────────────────
# Fonts
# ─────────────────────────────────────────────

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

try:
    title_font = ImageFont.truetype(FONT_BOLD_PATH, 20)
    total_font = ImageFont.truetype(FONT_PATH, 13)
    month_font = ImageFont.truetype(FONT_PATH, 11)
    footer_font = ImageFont.truetype(FONT_PATH, 10)
except OSError:
    title_font = ImageFont.load_default()
    total_font = ImageFont.load_default()
    month_font = ImageFont.load_default()
    footer_font = ImageFont.load_default()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

MONTHS = [
    "Jan", "Feb", "Mar", "Apr",
    "May", "Jun", "Jul", "Aug",
    "Sep", "Oct", "Nov", "Dec",
]


def stable_seed(text: str) -> int:
    digest = hashlib.sha1(text.encode()).hexdigest()
    return int(digest[:8], 16)


def quadratic_points(
    x0,
    y0,
    cx,
    cy,
    x1,
    y1,
    steps=8,
):
    points = []

    for i in range(steps + 1):
        t = i / steps

        x = (
            (1 - t) ** 2 * x0
            + 2 * (1 - t) * t * cx
            + t ** 2 * x1
        )

        y = (
            (1 - t) ** 2 * y0
            + 2 * (1 - t) * t * cy
            + t ** 2 * y1
        )

        points.append((x, y))

    return points


def contribution_strength(count: int) -> float:
    if count <= 0:
        return 0

    return math.log1p(count) / math.log1p(max_count)


def draw_background(draw):
    top = (13, 17, 23)
    bottom = (8, 20, 13)

    for y in range(HEIGHT):
        p = y / HEIGHT

        color = tuple(
            int(top[i] * (1 - p) + bottom[i] * p)
            for i in range(3)
        )

        draw.line(
            [(0, y), (WIDTH, y)],
            fill=color,
        )


def draw_hills(draw):
    back_points = [(0, GROUND_Y + 9)]

    for x in range(0, WIDTH + 10, 10):
        y = (
            GROUND_Y
            + 4
            + math.sin(x * 0.014) * 3
            + math.sin(x * 0.031) * 1.5
        )
        back_points.append((x, y))

    back_points.extend([
        (WIDTH, HEIGHT),
        (0, HEIGHT),
    ])

    draw.polygon(
        back_points,
        fill=(10, 45, 25),
    )

    front_points = [(0, GROUND_Y + 18)]

    for x in range(0, WIDTH + 10, 10):
        y = (
            GROUND_Y
            + 15
            + math.sin(x * 0.009 + 1.4) * 4
        )
        front_points.append((x, y))

    front_points.extend([
        (WIDTH, HEIGHT),
        (0, HEIGHT),
    ])

    draw.polygon(
        front_points,
        fill=(7, 30, 18),
    )


def draw_flower(draw, x, y, scale=1.0):
    radius = max(1, int(2 * scale))

    petal = (255, 226, 115)
    center = (255, 174, 66)

    for dx, dy in [
        (-radius, 0),
        (radius, 0),
        (0, -radius),
        (0, radius),
    ]:
        draw.ellipse(
            (
                x + dx - radius,
                y + dy - radius,
                x + dx + radius,
                y + dy + radius,
            ),
            fill=petal,
        )

    draw.ellipse(
        (
            x - radius,
            y - radius,
            x + radius,
            y + radius,
        ),
        fill=center,
    )


# ─────────────────────────────────────────────
# Month positions
# ─────────────────────────────────────────────

month_positions = []
seen_months = set()

for index, day in enumerate(days):
    year, month, day_number = map(
        int,
        day["date"].split("-"),
    )

    key = (year, month)

    if key in seen_months:
        continue

    seen_months.add(key)

    x = LEFT + index * spacing

    month_positions.append(
        (x, MONTHS[month - 1])
    )


# ─────────────────────────────────────────────
# Generate animation frames
# ─────────────────────────────────────────────

frames = []

for frame_index in range(FRAME_COUNT):
    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        "#0d1117",
    )

    draw = ImageDraw.Draw(image)

    draw_background(draw)
    draw_hills(draw)

    # Header
    draw.text(
        (40, 34),
        "Contribution Meadow",
        font=title_font,
        fill=(240, 246, 252),
    )

    draw.text(
        (WIDTH - 40, 36),
        f"{total:,} contributions",
        font=total_font,
        fill=(57, 211, 83),
        anchor="ra",
    )

    global_wind = math.sin(
        frame_index / FRAME_COUNT * math.tau
    )

    for index, day in enumerate(days):
        count = day["count"]
        strength = contribution_strength(count)

        x = LEFT + index * spacing

        rng = random.Random(
            stable_seed(day["date"])
        )

        if count == 0:
            height = rng.uniform(3, 7)
            blade_count = 1
            color = (25, 55, 36)
        else:
            height = (
                11
                + strength * 76
                + rng.uniform(-5, 7)
            )

            if count >= 8:
                blade_count = 5
            elif count >= 5:
                blade_count = 4
            elif count >= 2:
                blade_count = 3
            else:
                blade_count = 2

            # GitHub greens with slight natural variation
            greens = [
                (57, 211, 83),
                (46, 190, 77),
                (72, 210, 110),
                (117, 223, 140),
                (37, 167, 70),
            ]

            color = greens[
                rng.randrange(len(greens))
            ]

        for blade in range(blade_count):
            blade_rng = random.Random(
                stable_seed(
                    f"{day['date']}-{blade}"
                )
            )

            offset_x = blade_rng.uniform(
                -2.2,
                2.2,
            )

            blade_height = height * blade_rng.uniform(
                0.68,
                1.08,
            )

            phase = blade_rng.uniform(
                0,
                math.tau,
            )

            individual_wind = math.sin(
                frame_index
                / FRAME_COUNT
                * math.tau
                + phase
            )

            sway_amount = (
                1.5
                + strength * 5
            )

            sway = (
                global_wind * sway_amount
                + individual_wind * 2.3
            )

            natural_lean = blade_rng.uniform(
                -3.5,
                3.5,
            )

            base_x = x + offset_x
            base_y = GROUND_Y

            tip_x = (
                base_x
                + natural_lean
                + sway
            )

            tip_y = (
                base_y
                - blade_height
            )

            control_x = (
                base_x
                + natural_lean * 0.45
                + sway * 0.25
            )

            control_y = (
                base_y
                - blade_height * 0.52
            )

            curve = quadratic_points(
                base_x,
                base_y,
                control_x,
                control_y,
                tip_x,
                tip_y,
            )

            width = 2 if strength > 0.35 else 1

            draw.line(
                curve,
                fill=color,
                width=width,
                joint="curve",
            )

            # Small leaf on taller blades
            if (
                count > 0
                and blade_height > 34
                and blade_rng.random() > 0.45
            ):
                leaf_y = (
                    base_y
                    - blade_height * 0.55
                )

                leaf_x = (
                    base_x
                    + sway * 0.15
                )

                direction = (
                    -1
                    if blade_rng.random() < 0.5
                    else 1
                )

                draw.line(
                    [
                        (leaf_x, leaf_y),
                        (
                            leaf_x
                            + direction
                            * blade_rng.uniform(3, 6),
                            leaf_y
                            - blade_rng.uniform(2, 5),
                        ),
                    ],
                    fill=color,
                    width=1,
                )

        # Flower on high-activity days
        if strength > 0.82:
            flower_rng = random.Random(
                stable_seed(
                    f"flower-{day['date']}"
                )
            )

            if flower_rng.random() > 0.35:
                flower_y = (
                    GROUND_Y
                    - height
                    - 4
                )

                flower_x = (
                    x
                    + global_wind
                    * (2 + strength * 2)
                )

                draw_flower(
                    draw,
                    flower_x,
                    flower_y,
                    0.8 + strength * 0.35,
                )

    # Ground line
    draw.line(
        [
            (25, GROUND_Y + 1),
            (WIDTH - 25, GROUND_Y + 1),
        ],
        fill=(35, 134, 54),
        width=2,
    )

    # Months
    for x, label in month_positions:
        draw.text(
            (x, 283),
            label,
            font=month_font,
            fill=(139, 148, 158),
            anchor="ma",
        )

    draw.text(
        (WIDTH / 2, 312),
        "GitHub activity · last year · click to explore",
        font=footer_font,
        fill=(72, 79, 88),
        anchor="ma",
    )

    frames.append(image)


# ─────────────────────────────────────────────
# Save GIF
# ─────────────────────────────────────────────

frames[0].save(
    GIF_OUTPUT,
    save_all=True,
    append_images=frames[1:],
    duration=FRAME_DURATION,
    loop=0,
    optimize=True,
)

print("Generated:", GIF_OUTPUT)
print("Generated:", JSON_OUTPUT)
print("Contribution days:", len(days))
print("Total contributions:", total)
