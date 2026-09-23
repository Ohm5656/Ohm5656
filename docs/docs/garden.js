(() => {
  const canvas = document.getElementById("garden");
  const tooltip = document.getElementById("tooltip");
  const tooltipDate = document.getElementById("tooltipDate");
  const tooltipCount = document.getElementById("tooltipCount");
  const totalElement = document.getElementById("total");
  const ctx = canvas.getContext("2d");

  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  let data = null;
  let width = 0;
  let height = 0;
  let dpr = 1;

  let hoverIndex = null;
  let selectedIndex = null;
  let pointerX = 0;
  let pointerActive = false;
  let animationId = null;

  const LEFT = 34;
  const RIGHT = 34;

  function hashString(text) {
    let hash = 2166136261;

    for (let i = 0; i < text.length; i++) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }

    return hash >>> 0;
  }

  function seededRandom(seed) {
    let state = seed >>> 0;

    return () => {
      state = Math.imul(1664525, state) + 1013904223;
      state >>>= 0;
      return state / 4294967296;
    };
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function strengthFor(count, maxCount) {
    if (!count) return 0;
    return Math.log1p(count) / Math.log1p(maxCount);
  }

  function fitCanvas() {
    const rect = canvas.getBoundingClientRect();

    width = rect.width;
    height = rect.height;
    dpr = Math.min(window.devicePixelRatio || 1, 2);

    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function drawBackground() {
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, "#0d1117");
    gradient.addColorStop(1, "#07130c");

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
  }

  function drawHills(groundY) {
    ctx.beginPath();
    ctx.moveTo(0, groundY + 5);

    for (let x = 0; x <= width; x += 8) {
      const y =
        groundY +
        4 +
        Math.sin(x * 0.014) * 3 +
        Math.sin(x * 0.031) * 1.5;

      ctx.lineTo(x, y);
    }

    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();

    ctx.fillStyle = "#0a2d19";
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(0, groundY + 17);

    for (let x = 0; x <= width; x += 8) {
      const y = groundY + 15 + Math.sin(x * 0.009 + 1.4) * 4;
      ctx.lineTo(x, y);
    }

    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();

    ctx.fillStyle = "#071e12";
    ctx.fill();
  }

  function drawFlower(x, y, scale) {
    const radius = 2.1 * scale;
    ctx.fillStyle = "#ffe273";

    const petals = [
      [-radius, 0],
      [radius, 0],
      [0, -radius],
      [0, radius],
    ];

    for (const [dx, dy] of petals) {
      ctx.beginPath();
      ctx.arc(x + dx, y + dy, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.fillStyle = "#ffa83d";
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawMonths(days, spacing, groundY) {
    ctx.font = "11px ui-sans-serif, system-ui";
    ctx.fillStyle = "#8b949e";

    const seen = new Set();

    for (let i = 0; i < days.length; i++) {
      const parts = days[i].date.split("-");
      const year = Number(parts[0]);
      const month = Number(parts[1]);
      const key = `${year}-${month}`;

      if (seen.has(key)) continue;
      seen.add(key);

      const date = new Date(Date.UTC(year, month - 1, 1));
      const label = date.toLocaleString("en", {
        month: "short",
        timeZone: "UTC",
      });

      const x = LEFT + i * spacing;
      ctx.fillText(label, x, groundY + 37);
    }
  }

  function drawGarden(timestamp = 0) {
    if (!data) return;

    drawBackground();

    const days = data.days;
    const maxCount = Math.max(1, ...days.map((day) => day.count));
    const groundY = height - 83;

    drawHills(groundY);

    const meadowWidth = width - LEFT - RIGHT;
    const spacing = meadowWidth / Math.max(days.length - 1, 1);
    const time = reducedMotion ? 0 : timestamp * 0.001;

    for (let index = 0; index < days.length; index++) {
      const day = days[index];
      const count = day.count;
      const strength = strengthFor(count, maxCount);
      const x = LEFT + index * spacing;

      const rand = seededRandom(hashString(day.date));

      let grassHeight;
      let blades;

      if (count === 0) {
        grassHeight = 3 + rand() * 4;
        blades = 1;
      } else {
        grassHeight =
          12 +
          strength * Math.min(115, height * 0.34) +
          (rand() - 0.5) * 12;

        if (count >= 8) blades = 5;
        else if (count >= 5) blades = 4;
        else if (count >= 2) blades = 3;
        else blades = 2;
      }

      const distance = pointerActive ? Math.abs(pointerX - x) : 9999;
      const influence = pointerActive
        ? Math.exp(-(distance * distance) / 6500)
        : 0;

      let mouseBend = 0;

      if (pointerActive && influence > 0.01) {
        const direction = x >= pointerX ? 1 : -1;
        mouseBend =
          direction *
          influence *
          (4 + strength * 13);
      }

      for (let blade = 0; blade < blades; blade++) {
        const bladeRand = seededRandom(
          hashString(`${day.date}-${blade}`)
        );

        const offset = (bladeRand() - 0.5) * 5;
        const bladeHeight =
          grassHeight * (0.67 + bladeRand() * 0.42);

        const phase = bladeRand() * Math.PI * 2;
        const naturalLean = (bladeRand() - 0.5) * 8;

        const wind = reducedMotion
          ? 0
          : Math.sin(time * 1.4 + phase + index * 0.04) *
            (1.7 + strength * 5.5);

        const baseX = x + offset;
        const baseY = groundY;
        const tipX = baseX + naturalLean + wind + mouseBend;
        const tipY = baseY - bladeHeight;

        const controlX =
          baseX +
          naturalLean * 0.42 +
          wind * 0.3 +
          mouseBend * 0.38;

        const controlY = baseY - bladeHeight * 0.52;

        ctx.beginPath();
        ctx.moveTo(baseX, baseY);
        ctx.quadraticCurveTo(
          controlX,
          controlY,
          tipX,
          tipY
        );

        if (count === 0) {
          ctx.strokeStyle = "#193522";
          ctx.globalAlpha = 0.55;
        } else {
          const greens = [
            "#39d353",
            "#2ebd4d",
            "#48d26e",
            "#75df8c",
            "#25a746",
          ];

          ctx.strokeStyle =
            greens[Math.floor(bladeRand() * greens.length)];

          ctx.globalAlpha = 0.92;
        }

        ctx.lineWidth = strength > 0.35 ? 1.7 : 1.1;
        ctx.lineCap = "round";
        ctx.stroke();
        ctx.globalAlpha = 1;

        if (
          count > 0 &&
          bladeHeight > 42 &&
          bladeRand() > 0.45
        ) {
          const leafY = baseY - bladeHeight * 0.56;
          const leafX =
            baseX +
            wind * 0.16 +
            mouseBend * 0.2;

          const direction = bladeRand() > 0.5 ? 1 : -1;

          ctx.beginPath();
          ctx.moveTo(leafX, leafY);
          ctx.quadraticCurveTo(
            leafX + direction * 3,
            leafY - 3,
            leafX + direction * 7,
            leafY - 5
          );

          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      if (strength > 0.82) {
        const flowerRand = seededRandom(
          hashString(`flower-${day.date}`)
        );

        if (flowerRand() > 0.35) {
          const wind = reducedMotion
            ? 0
            : Math.sin(time * 1.4 + index * 0.07) * 3;

          drawFlower(
            x + wind + mouseBend,
            groundY - grassHeight - 5,
            0.75 + strength * 0.3
          );
        }
      }

      if (index === selectedIndex || index === hoverIndex) {
        ctx.beginPath();
        ctx.arc(x, groundY + 3, 4, 0, Math.PI * 2);
        ctx.fillStyle = "#39d353";
        ctx.fill();
      }
    }

    ctx.globalAlpha = 1;
    ctx.strokeStyle = "rgba(57,211,83,.32)";
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.moveTo(20, groundY + 1);
    ctx.lineTo(width - 20, groundY + 1);
    ctx.stroke();

    drawMonths(days, spacing, groundY);

    if (!reducedMotion) {
      animationId = requestAnimationFrame(drawGarden);
    }
  }

  function nearestDayIndex(x) {
    if (!data) return null;

    const meadowWidth = width - LEFT - RIGHT;
    const spacing =
      meadowWidth / Math.max(data.days.length - 1, 1);

    const index = Math.round((x - LEFT) / spacing);

    return clamp(index, 0, data.days.length - 1);
  }

  function showTooltip(index) {
    if (index === null || !data) {
      tooltip.hidden = true;
      return;
    }

    const day = data.days[index];
    const date = new Date(`${day.date}T00:00:00Z`);

    tooltipDate.textContent = date.toLocaleDateString("en", {
      day: "numeric",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });

    tooltipCount.textContent =
      `${day.count} contribution${day.count === 1 ? "" : "s"}`;

    const meadowWidth = width - LEFT - RIGHT;
    const spacing =
      meadowWidth / Math.max(data.days.length - 1, 1);

    const x = LEFT + index * spacing;

    tooltip.style.left = `${clamp(x, 80, width - 80)}px`;
    tooltip.style.top = `${height - 110}px`;
    tooltip.hidden = false;
  }

  canvas.addEventListener("pointermove", (event) => {
    const rect = canvas.getBoundingClientRect();

    pointerX = event.clientX - rect.left;
    pointerActive = true;

    hoverIndex = nearestDayIndex(pointerX);
    showTooltip(hoverIndex);

    if (reducedMotion) {
      drawGarden(0);
    }
  });

  canvas.addEventListener("pointerleave", () => {
    pointerActive = false;
    hoverIndex = null;

    if (selectedIndex !== null) {
      showTooltip(selectedIndex);
    } else {
      tooltip.hidden = true;
    }

    if (reducedMotion) {
      drawGarden(0);
    }
  });

  canvas.addEventListener("click", (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;

    selectedIndex = nearestDayIndex(x);
    showTooltip(selectedIndex);

    if (reducedMotion) {
      drawGarden(0);
    }
  });

  window.addEventListener("resize", () => {
    fitCanvas();

    if (reducedMotion) {
      drawGarden(0);
    }
  });

  async function init() {
    try {
      const response = await fetch("./contributions.json");

      if (!response.ok) {
        throw new Error("Could not load contribution data.");
      }

      data = await response.json();

      if (!Array.isArray(data.days)) {
        throw new Error("Invalid contribution data.");
      }

      totalElement.textContent =
        `${Number(data.total || 0).toLocaleString()} contributions`;

      fitCanvas();

      if (reducedMotion) {
        drawGarden(0);
      } else {
        animationId = requestAnimationFrame(drawGarden);
      }
    } catch (error) {
      totalElement.textContent = "Contribution data unavailable";
      console.error(error);
    }
  }

  init();
})();
