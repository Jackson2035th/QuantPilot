document.querySelectorAll(".landing-mobile-menu a").forEach((link) => {
  link.addEventListener("click", () => {
    link.closest("details").removeAttribute("open");
  });
});

(() => {
  const path = document.getElementById("landingCurvePath");
  const lead = document.getElementById("landingCurveLead");
  const future = document.getElementById("landingCurveFuture");
  if (!path || !lead || !future) return;

  const parsePathPoints = (element) => {
    const coordinateValues = element.getAttribute("d").match(/-?\d+(?:\.\d+)?/g).map(Number);
    const points = [];
    for (let index = 0; index < coordinateValues.length; index += 2) {
      points.push({ x: coordinateValues[index], y: coordinateValues[index + 1] });
    }
    return points;
  };

  const serializePath = (points) => points
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x} ${point.y}`)
    .join(" ");

  const densityMultiplier = 2;
  const trendScale = 1.45;
  const volatilityScale = 1.55;
  const entryPointCount = 28;
  const extensionPointCount = 40;
  const solidEndX = 1235;

  const createEntryPoints = (firstPoint) => {
    const entryPoints = [];
    for (let index = 0; index < entryPointCount; index += 1) {
      const progress = index / entryPointCount;
      const x = -18 + (firstPoint.x + 18) * progress;
      const baselineY = 326 + (firstPoint.y - 326) * progress;
      const entrySwing = Math.sin(progress * Math.PI * 4.5) * 3.2
        + Math.sin(progress * Math.PI * 9) * 1.1;
      entryPoints.push({ x, y: baselineY + entrySwing });
    }
    return entryPoints;
  };

  const extendFutureCurve = (points) => {
    const extendedPoints = [...points];
    const lastPoint = points[points.length - 1];
    for (let index = 1; index <= extensionPointCount; index += 1) {
      const progress = index / extensionPointCount;
      const x = lastPoint.x + (1460 - lastPoint.x) * progress;
      const baselineY = lastPoint.y + (120 - lastPoint.y) * progress;
      const extensionSwing = Math.sin(progress * Math.PI * 4) * 2.4
        + Math.sin(progress * Math.PI * 9) * 0.9;
      extendedPoints.push({ x, y: baselineY + extensionSwing });
    }
    return extendedPoints;
  };

  // Amplify the original path without replacing its deliberate peaks and drawdowns.
  const reshapeCurve = (
    points,
    outputStartY,
    currentTrendScale,
    currentVolatilityScale,
    phase = 0,
  ) => {
    const firstPoint = points[0];
    const lastPoint = points[points.length - 1];
    return points.map((point, index) => {
      const progress = index / (points.length - 1);
      const baselineY = firstPoint.y + (lastPoint.y - firstPoint.y) * progress;
      const deviation = point.y - baselineY;
      const irregularity = Math.sin(Math.PI * progress) * (
        Math.sin((index + phase) * 1.87) * 1.8
        + Math.sin((index + phase) * 0.43) * 1.1
      );
      return {
        x: point.x,
        y: outputStartY
          + (lastPoint.y - firstPoint.y) * currentTrendScale * progress
          + deviation * currentVolatilityScale
          + irregularity,
      };
    });
  };

  // Add intermediate volatility nodes while preserving every original endpoint.
  const densifyCurve = (points) => {
    const densePoints = [points[0]];
    for (let index = 0; index < points.length - 1; index += 1) {
      const segmentStart = points[index];
      const segmentEnd = points[index + 1];
      for (let step = 1; step <= densityMultiplier; step += 1) {
        const progress = step / densityMultiplier;
        const midpointSwing = step === densityMultiplier ? 0 : (
          Math.sin((index + 1) * 2.11) * 2.2
          + Math.sin((index + 1) * 0.71) * 1.1
        );
        densePoints.push({
          x: segmentStart.x + (segmentEnd.x - segmentStart.x) * progress,
          y: segmentStart.y
            + (segmentEnd.y - segmentStart.y) * progress
            + Math.sin(Math.PI * progress) * midpointSwing,
        });
      }
    }
    return densePoints;
  };

  const parsedCurvePoints = parsePathPoints(path);
  const baseCurvePoints = [...createEntryPoints(parsedCurvePoints[0]), ...parsedCurvePoints];
  const baseFuturePoints = extendFutureCurve(parsePathPoints(future));
  const shapedCurvePoints = reshapeCurve(
    baseCurvePoints,
    baseCurvePoints[0].y,
    trendScale,
    volatilityScale,
  );
  const shapedFuturePoints = reshapeCurve(
    baseFuturePoints,
    shapedCurvePoints[shapedCurvePoints.length - 1].y,
    1,
    1.35,
    baseCurvePoints.length,
  );
  // Split one continuous geometry into the animated solid path and dotted future path.
  const handoffIndex = shapedFuturePoints.findIndex((point) => point.x >= solidEndX);
  const solidCurvePoints = [
    ...shapedCurvePoints,
    ...shapedFuturePoints.slice(1, handoffIndex + 1),
  ];
  const curvePoints = densifyCurve(solidCurvePoints);
  const remainingFuturePoints = shapedFuturePoints.slice(handoffIndex);
  future.setAttribute("d", serializePath(remainingFuturePoints));

  const delay = 350;
  const duration = 8000;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Derive both the visible path and lead point from one interpolation to prevent drift.
  const renderProgress = (progress) => {
    const curvePosition = progress * (curvePoints.length - 1);
    const segmentIndex = Math.min(Math.floor(curvePosition), curvePoints.length - 2);
    const segmentProgress = curvePosition - segmentIndex;
    const segmentStart = curvePoints[segmentIndex];
    const segmentEnd = curvePoints[segmentIndex + 1];
    const point = {
      x: segmentStart.x + (segmentEnd.x - segmentStart.x) * segmentProgress,
      y: segmentStart.y + (segmentEnd.y - segmentStart.y) * segmentProgress,
    };
    const visiblePoints = curvePoints.slice(0, segmentIndex + 1);
    visiblePoints.push(point);
    path.setAttribute("d", serializePath(visiblePoints));
    lead.setAttribute("transform", `translate(${point.x} ${point.y})`);
  };

  if (reduceMotion) {
    renderProgress(1);
    future.classList.add("is-visible");
    return;
  }

  renderProgress(0);
  let startedAt;
  const animateCurve = (timestamp) => {
    if (startedAt === undefined) startedAt = timestamp;
    const progress = Math.max(0, Math.min(1, (timestamp - startedAt - delay) / duration));
    renderProgress(progress);
    if (progress < 1) {
      window.requestAnimationFrame(animateCurve);
    } else {
      future.classList.add("is-visible");
    }
  };
  window.requestAnimationFrame(animateCurve);
})();
