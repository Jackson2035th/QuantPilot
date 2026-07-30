(() => {
  const chartColors = ["#0f766e", "#2563eb", "#c2410c", "#7c3aed"];

  const readSeries = (source) => {
    if (!source) return null;
    try {
      const series = JSON.parse(source.textContent);
      const isValid = Array.isArray(series) && series.length > 1 && series.every(
        (item) => item && typeof item.label === "string" && Array.isArray(item.points),
      );
      return isValid ? series : null;
    } catch (error) {
      return null;
    }
  };

  const canvas = document.querySelector("[data-comparison-chart]");
  if (!canvas || !window.Chart) return;

  const series = readSeries(document.getElementById(canvas.dataset.comparisonSource));
  if (!series) return;

  const labels = [...new Set(series.flatMap((item) => item.points.map((point) => point.date)))].sort();
  const datasets = series.map((item, index) => {
    const valuesByDate = new Map(item.points.map((point) => [point.date, point.value]));
    const color = chartColors[index];
    return {
      label: item.label,
      data: labels.map((date) => valuesByDate.get(date) ?? null),
      borderColor: color,
      backgroundColor: color,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.2,
      spanGaps: false,
    };
  });

  new window.Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom" } },
      scales: {
        x: { ticks: { maxTicksLimit: 6, maxRotation: 45, minRotation: 45 } },
        y: { ticks: { callback: (value) => `$${Number(value).toLocaleString()}` } },
      },
    },
  });
})();
