/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, onWillUpdateProps, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

/**
 * Finsetter CRM — thin OWL wrapper around Odoo's bundled Chart.js (v4).
 *
 * Props: `config` — a full Chart.js config ({ type, data, options }).
 * Shared look (fonts, recessive grid, tooltips, thin marks) is applied
 * here so every dashboard chart reads as one system.
 */
export const FS_COLORS = {
    // Validated categorical order (CVD-safe adjacent pairs) — assign in this
    // order, never cycled; anything past slot 8 folds into "Other".
    series: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    // Single-hue ordinal ramp (light -> dark) for ordered stages.
    ramp: ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"],
    other: "#a3a9b3",
    grid: "#eef0f2",
    text: "#526579",
    ink: "#102a43",
    surface: "#ffffff",
};

export function rampColors(count) {
    const ramp = FS_COLORS.ramp;
    if (count <= 1) {
        return [ramp[2]];
    }
    return Array.from({ length: count }, (_, i) => ramp[Math.round((i * (ramp.length - 1)) / (count - 1))]);
}

export function withAlpha(hex, alpha) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

export class FsChart extends Component {
    static template = "finsetter_crm.FsChart";
    static props = {
        config: Object,
        height: { type: Number, optional: true },
        ariaLabel: { type: String, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;
        onWillStart(() => loadBundle("web.chartjs_lib"));
        onMounted(() => this.renderChart(this.props.config));
        onWillUpdateProps((next) => {
            if (next.config !== this.props.config) {
                this.renderChart(next.config);
            }
        });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }

    renderChart(config) {
        const Chart = window.Chart;
        if (this.chart) {
            this.chart.destroy();
        }
        Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
        Chart.defaults.font.size = 12;
        Chart.defaults.color = FS_COLORS.text;
        const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const base = {
            responsive: true,
            maintainAspectRatio: false,
            animation: reduceMotion ? false : { duration: 450, easing: "easeOutCubic" },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: FS_COLORS.ink,
                    titleColor: "#ffffff",
                    bodyColor: "#e2edf3",
                    padding: 10,
                    cornerRadius: 6,
                    boxPadding: 4,
                    usePointStyle: true,
                },
            },
        };
        this.chart = new Chart(this.canvasRef.el, {
            ...config,
            options: deepMerge(base, config.options || {}),
        });
    }
}

function deepMerge(target, source) {
    const out = { ...target };
    for (const [key, value] of Object.entries(source)) {
        out[key] = value && typeof value === "object" && !Array.isArray(value) && typeof target[key] === "object"
            ? deepMerge(target[key], value)
            : value;
    }
    return out;
}
