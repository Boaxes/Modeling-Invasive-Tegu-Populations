// Simple line chart: one value per timestep, scaled to fit

export function draw_chart(svg: SVGSVGElement, values: number[]): void {
    const [w, h, pad] = [200, 80, 4];
    const lo = Math.min(...values);
    const hi = Math.max(...values);
    const points = values.map((v, i) => {
        const x = pad + (values.length > 1 ? i / (values.length - 1) : 0) * (w - 2 * pad);
        const y = h - pad - (hi > lo ? (v - lo) / (hi - lo) : 0.5) * (h - 2 * pad);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    svg.innerHTML = `<polyline points="${points.join(" ")}" fill="none" stroke="#3ddc84" stroke-width="2" />`;
}
