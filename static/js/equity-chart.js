(() => {
  const buildTickIndexes = (pointCount, maximumTicks = 6) => {
    const visibleTickCount = Math.min(maximumTicks, pointCount);
    if (visibleTickCount === 1) return [0];
    return Array.from(
      { length: visibleTickCount },
      (_, index) => Math.round(index * (pointCount - 1) / (visibleTickCount - 1)),
    );
  };

  const readPoints = (source) => {
    if (!source) return null;
    try {
      const points = JSON.parse(source.textContent);
      const isValid = Array.isArray(points) && points.length > 0 && points.every(
        (point) => point
          && typeof point.date === "string"
          && Number.isFinite(Number(point.value)),
      );
      return isValid ? points : null;
    } catch (error) {
      return null;
    }
  };

  const showFallback = (canvas) => {
    canvas.hidden = true;
    const fallback = document.getElementById(canvas.dataset.equityFallback);
    if (fallback) fallback.hidden = false;
  };

  const buildOptions = (canvas, tickIndexes) => {
    const isPreview = canvas.dataset.equityVariant === "preview";
    const rotateX = canvas.dataset.equityRotateX === "true";
    const xTicks = rotateX
      ? { autoSkip: false, maxRotation: 45, minRotation: 45 }
      : { autoSkip: false, padding: 8, font: { size: 14, weight: "600" } };

    const options = {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          afterBuildTicks(scale) {
            scale.ticks = tickIndexes.map((value) => ({ value }));
          },
          ticks: xTicks,
        },
      },
    };

    // The dashboard preview stays compact while the detail chart keeps its legend and points.
    if (isPreview) {
      options.layout = { padding: { top: 0, bottom: 12 } };
      options.plugins = { legend: { display: false } };
      options.scales.y = {
        grace: "6%",
        ticks: {
          maxTicksLimit: Number(canvas.dataset.equityYTicks),
          padding: 8,
          font: { size: 14, weight: "600" },
        },
      };
    }
    return options;
  };

  // Templates provide data identifiers and small presentation options; chart logic remains shared.
  document.querySelectorAll("[data-equity-chart]").forEach((canvas) => {
    const source = document.getElementById(canvas.dataset.equitySource);
    const points = readPoints(source);
    if (!window.Chart || !points) {
      showFallback(canvas);
      return;
    }

    const isPreview = canvas.dataset.equityVariant === "preview";
    const dataset = {
      label: canvas.dataset.equityLabel,
      data: points.map((point) => point.value),
      borderColor: "#0f766e",
      backgroundColor: "rgba(15, 118, 110, 0.12)",
      fill: true,
      tension: Number(canvas.dataset.equityTension),
    };
    if (isPreview) {
      dataset.borderWidth = 2;
      dataset.pointRadius = 0;
    }

    new window.Chart(canvas, {
      type: "line",
      data: {
        labels: points.map((point) => point.date),
        datasets: [dataset],
      },
      options: buildOptions(canvas, buildTickIndexes(points.length)),
    });
  });
})();
