/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FsChart, FS_COLORS, rampColors, withAlpha } from "./fs_chart";

const LEAD_STATUSES = [
    ["new", "New"],
    ["contacted", "Contacted"],
    ["interested", "Interested"],
    ["quote_sent", "Quote Sent"],
    ["converted", "Converted"],
    ["lost", "Lost"],
];
const AGE_BANDS = [["Under 30", 0, 29], ["30–39", 30, 39], ["40–49", 40, 49], ["50–59", 50, 59], ["60+", 60, 200]];
const SLA_ROWS = [
    ["met", "Met", "fa-check-circle", "#0ca30c"],
    ["pending", "Pending", "fa-clock-o", "#fab219"],
    ["breached", "Breached", "fa-exclamation-triangle", "#d03b3b"],
];

/** Draws each bar's total at its tip (bars: right end, columns: on the cap). */
const barValueLabels = {
    id: "fsBarValues",
    afterDatasetsDraw(chart, _args, opts) {
        if (!opts || !opts.enabled) {
            return;
        }
        const { ctx } = chart;
        const horizontal = chart.options.indexAxis === "y";
        const metas = chart.data.datasets.map((_ds, i) => chart.getDatasetMeta(i));
        ctx.save();
        ctx.font = `600 11px ${window.Chart.defaults.font.family}`;
        ctx.fillStyle = FS_COLORS.ink;
        chart.data.labels.forEach((_label, j) => {
            // Stacked charts label the total at the end of the stack.
            const total = chart.data.datasets.reduce((sum, ds) => sum + (ds.data[j] || 0), 0);
            if (!total) {
                return;
            }
            const text = opts.format ? opts.format(total, j) : String(total);
            if (horizontal) {
                const end = Math.max(...metas.map((m) => m.data[j].x));
                ctx.textAlign = "left";
                ctx.textBaseline = "middle";
                ctx.fillText(text, end + 6, metas[0].data[j].y);
            } else {
                const top = Math.min(...metas.map((m) => m.data[j].y));
                ctx.textAlign = "center";
                ctx.textBaseline = "bottom";
                ctx.fillText(text, metas[0].data[j].x, top - 4);
            }
        });
        ctx.restore();
    },
};

/**
 * Finsetter CRM — Executive Dashboard
 *
 * A single-screen view of pipeline health, renewals due, consent status and
 * team performance, styled after thefinsetter.com's brand. Pure read via
 * the standard ORM service — no custom controller needed.
 */
class FinsetterDashboard extends Component {
    static template = "finsetter_crm.Dashboard";
    static components = { FsChart };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            pipelineCount: 0,
            pipelineValue: 0,
            wonMonthCount: 0,
            wonMonthValue: 0,
            renewalsSoonCount: 0,
            consentPendingCount: 0,
            callsTodayCount: 0,
            slaBreachedCount: 0,
            renewals: [],
            productLines: [],
            donutSegments: [],
            insurances: [],
            leaderboard: [],
            testimonial: null,
            currencySymbol: "₹",
            busyPolicyId: null,
            charts: null,
        });

        onWillStart(async () => this.loadData());
    }

    async loadData() {
        const today = new Date();
        const y = today.getFullYear(), m = today.getMonth(), d = today.getDate();
        const pad = (n) => String(n).padStart(2, "0");
        const toDate = (dt) => `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`;
        const monthStart = toDate(new Date(y, m, 1));
        const in30 = toDate(new Date(y, m, d + 30));

        // Each query falls back to an empty result on failure (e.g. a role
        // without read access to one model), so one panel can never take
        // the whole dashboard down.
        const safe = (promise, fallback) => promise.catch(() => fallback);

        const [
            pipelineCount,
            pipelineGroups,
            wonMonthGroups,
            renewalsSoonCount,
            consentPendingCount,
            callsTodayCount,
            slaBreachedCount,
            renewals,
            productLineGroups,
            leaderboardGroups,
            testimonials,
            productLineCatalog,
            policyByLineGroups,
            analyticsLeads,
            stages,
        ] = await Promise.all([
            safe(this.orm.searchCount("crm.lead", [["type", "=", "opportunity"], ["active", "=", true], ["probability", "<", 100]]), 0),
            safe(this.orm.formattedReadGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["active", "=", true], ["probability", "<", 100]],
                [],
                ["expected_revenue:sum", "__count"]
            ), []),
            safe(this.orm.formattedReadGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["stage_id.is_won", "=", true], ["date_closed", ">=", monthStart]],
                [],
                ["expected_revenue:sum", "__count"]
            ), []),
            safe(this.orm.searchCount("finsetter.policy", [
                ["state", "in", ["active", "renewal_due"]],
                ["renewal_date", "<=", in30],
            ]), 0),
            safe(this.orm.searchCount("crm.lead", [["active", "=", true], ["call_consent_status", "=", "unknown"]]), 0),
            safe(this.orm.searchCount("finsetter.call.log", [["call_datetime", ">=", `${toDate(today)} 00:00:00`]]), 0),
            safe(this.orm.searchCount("crm.lead", [["sla_status", "=", "breached"]]), 0),
            safe(this.orm.searchRead(
                "finsetter.policy",
                [["state", "in", ["active", "renewal_due"]], ["renewal_date", "<=", in30]],
                ["display_name", "partner_id", "product_line_id", "renewal_date", "days_to_renewal", "advisor_id", "premium_amount"],
                { order: "renewal_date asc", limit: 8 }
            ), []),
            safe(this.orm.formattedReadGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["active", "=", true]],
                ["product_line_id"],
                ["expected_revenue:sum", "__count"]
            ), []),
            safe(this.orm.formattedReadGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["stage_id.is_won", "=", true], ["date_closed", ">=", monthStart]],
                ["user_id"],
                ["expected_revenue:sum", "__count"]
            ), []),
            safe(this.orm.searchRead(
                "finsetter.testimonial",
                [],
                ["name", "role_location", "quote", "product_line_id"],
                { limit: 20 }
            ), []),
            safe(this.orm.searchRead(
                "finsetter.policy.product.line",
                [],
                ["name", "icon", "color"],
                { order: "sequence asc" }
            ), []),
            safe(this.orm.formattedReadGroup(
                "finsetter.policy",
                [["state", "in", ["active", "renewal_due"]]],
                ["product_line_id"],
                ["premium_amount:sum", "__count"]
            ), []),
            // Lead analytics: one read (including lost/archived leads) powers
            // every chart in the analytics section.
            safe(this.orm.searchRead(
                "crm.lead",
                [],
                ["create_date", "date_closed", "type", "active", "stage_id", "lead_status", "source_id",
                 "product_line_id", "lead_relationship", "finsetter_age", "sla_status", "expected_revenue",
                 "channel_whatsapp", "channel_sms", "channel_email", "channel_ai_call"],
                { limit: 5000, context: { active_test: false } }
            ), []),
            safe(this.orm.searchRead("crm.stage", [], ["name", "sequence", "is_won"], { order: "sequence asc, id asc" }), []),
        ]);

        this.state.pipelineCount = pipelineCount;
        this.state.pipelineValue = (pipelineGroups[0] && pipelineGroups[0]["expected_revenue:sum"]) || 0;
                this.state.wonMonthCount = (wonMonthGroups[0] && wonMonthGroups[0].__count) || 0;
        this.state.wonMonthValue = (wonMonthGroups[0] && wonMonthGroups[0]["expected_revenue:sum"]) || 0;
        this.state.renewalsSoonCount = renewalsSoonCount;
        this.state.consentPendingCount = consentPendingCount;
        this.state.callsTodayCount = callsTodayCount;
        this.state.slaBreachedCount = slaBreachedCount;
        this.state.renewals = renewals;

        // Icon tints for the insurance cards (decorative, not data).
        const donutPalette = ["#2868a8", "#0b7a75", "#e3a62f", "#c55a4e", "#58658b", "#7edbd0", "#a56a1a", "#3f4b5c", "#8a4fd6", "#1f9e73", "#d67ab1", "#4a90d9", "#c9a227"];
        // Data colours: validated categorical slots in fixed order by value;
        // past the 7th line everything shares the neutral "Other" colour.
        const plColor = {};
        [...productLineGroups]
            .filter((g) => g.product_line_id)
            .sort((a, b) => (b["expected_revenue:sum"] || 0) - (a["expected_revenue:sum"] || 0))
            .forEach((g, idx) => {
                plColor[g.product_line_id[1]] = idx < 7 ? FS_COLORS.series[idx] : FS_COLORS.other;
            });

        const maxPl = Math.max(1, ...productLineGroups.map((g) => g["expected_revenue:sum"] || 0));
        this.state.productLines = productLineGroups
            .filter((g) => g.product_line_id)
            .map((g) => ({
                name: g.product_line_id[1],
                value: g["expected_revenue:sum"] || 0,
                count: g.__count || 0,
                pct: Math.round(((g["expected_revenue:sum"] || 0) / maxPl) * 100),
                color: plColor[g.product_line_id[1]],
            }))
            .sort((a, b) => b.value - a.value);

        // SVG donut: stroke-dasharray/dashoffset segments around a r=40 circle.
        const totalPl = productLineGroups.reduce((sum, g) => sum + (g["expected_revenue:sum"] || 0), 0) || 1;
        const circumference = 2 * Math.PI * 40;
        let cumulative = 0;
        this.state.donutSegments = productLineGroups
            .filter((g) => g.product_line_id)
            .map((g) => {
                const value = g["expected_revenue:sum"] || 0;
                const pct = value / totalPl;
                const length = pct * circumference;
                const seg = {
                    name: g.product_line_id[1],
                    value,
                    pct: Math.round(pct * 100),
                    color: plColor[g.product_line_id[1]],
                    dasharray: `${length.toFixed(2)} ${(circumference - length).toFixed(2)}`,
                    dashoffset: (-cumulative).toFixed(2),
                };
                cumulative += length;
                return seg;
            })
            .sort((a, b) => b.value - a.value);

        // Insurances panel: every product-line category, with its active/renewal-due
        // policy count and premium, so the dashboard shows the full book at a glance.
        const policyByLineMap = {};
        policyByLineGroups.forEach((g) => {
            if (g.product_line_id) {
                policyByLineMap[g.product_line_id[0]] = {
                    count: g.__count || 0,
                    premium: g["premium_amount:sum"] || 0,
                };
            }
        });
        // Note: product-line `color` on the model is a numeric Odoo kanban
        // color index (0-11), not a CSS color — so we assign real hex
        // colors from our own brand palette here instead, cycling by index.
        this.state.insurances = productLineCatalog.map((line, idx) => ({
            id: line.id,
            name: line.name,
            icon: line.icon || "fa-shield",
            color: donutPalette[idx % donutPalette.length],
            count: (policyByLineMap[line.id] && policyByLineMap[line.id].count) || 0,
            premium: (policyByLineMap[line.id] && policyByLineMap[line.id].premium) || 0,
        }));

        const maxLb = Math.max(1, ...leaderboardGroups.map((g) => g["expected_revenue:sum"] || 0));
        this.state.leaderboard = leaderboardGroups
            .filter((g) => g.user_id)
            .map((g) => ({
                name: g.user_id[1],
                value: g["expected_revenue:sum"] || 0,
                count: g.__count || 0,
                pct: Math.round(((g["expected_revenue:sum"] || 0) / maxLb) * 100),
            }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);

        this.state.charts = this.buildCharts(analyticsLeads, stages);

        this.state.testimonial = testimonials.length
            ? testimonials[Math.floor(Math.random() * testimonials.length)]
            : null;

        this.state.loading = false;
    }

    buildCharts(leads, stages) {
        const S = FS_COLORS.series;
        const gridScale = (extra = {}) => ({
            grid: { color: FS_COLORS.grid, drawTicks: false },
            border: { display: false },
            ticks: { padding: 8, precision: 0 },
            beginAtZero: true,
            ...extra,
        });
        const noGrid = (extra = {}) => ({ grid: { display: false }, border: { display: false }, ...extra });
        // Category labels on horizontal bars: ellipsis past 24 chars (full name stays in the tooltip).
        const shortLabels = (extra = {}) => noGrid({
            ticks: {
                callback(value) {
                    const label = this.getLabelForValue(value);
                    return label.length > 24 ? `${label.slice(0, 23)}…` : label;
                },
            },
            ...extra,
        });
        const barStyle = { maxBarThickness: 24, borderRadius: 4, borderSkipped: "start" };
        const legendTop = (pointStyle) => ({
            display: true, position: "top", align: "end",
            labels: { usePointStyle: true, pointStyle, boxWidth: 8, boxHeight: 8, color: FS_COLORS.ink },
        });

        const months = [];
        const now = new Date();
        for (let i = 5; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            months.push({
                key: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
                label: d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" }) + (i === 0 ? " · MTD" : ""),
            });
        }
        const monthIndex = Object.fromEntries(months.map((m, i) => [m.key, i]));
        const wonStageIds = new Set(stages.filter((s) => s.is_won).map((s) => s.id));
        const isWon = (l) => l.active && l.stage_id && wonStageIds.has(l.stage_id[0]);

        // 1. Lead inflow vs deals won, per month (line + area wash)
        const created = months.map(() => 0);
        const won = months.map(() => 0);
        for (const l of leads) {
            const ci = monthIndex[(l.create_date || "").slice(0, 7)];
            if (ci !== undefined) {
                created[ci]++;
            }
            const wi = monthIndex[(l.date_closed || "").slice(0, 7)];
            if (wi !== undefined && isWon(l)) {
                won[wi]++;
            }
        }
        const line = (label, data, color, fill) => ({
            label, data, fill,
            borderColor: color,
            backgroundColor: withAlpha(color, 0.1),
            borderWidth: 2,
            tension: 0.3,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: color,
            pointBorderColor: FS_COLORS.surface,
            pointBorderWidth: 2,
            pointHitRadius: 12,
        });
        const trend = {
            type: "line",
            data: {
                labels: months.map((m) => m.label),
                datasets: [line("New leads", created, S[0], true), line("Deals won", won, S[1], false)],
            },
            options: {
                interaction: { mode: "index", intersect: false },
                plugins: { legend: legendTop("circle") },
                scales: { y: gridScale(), x: noGrid() },
            },
        };

        // 2. Lead status mix (doughnut + HTML legend with counts)
        const statusCounts = LEAD_STATUSES.map(([key]) => leads.filter((l) => l.lead_status === key).length);
        const statusTotal = statusCounts.reduce((a, b) => a + b, 0);
        const pctOf = (n) => Math.round((n / (statusTotal || 1)) * 100);
        const status = {
            type: "doughnut",
            data: {
                labels: LEAD_STATUSES.map(([, label]) => label),
                datasets: [{
                    data: statusCounts,
                    backgroundColor: S.slice(0, LEAD_STATUSES.length),
                    borderColor: FS_COLORS.surface,
                    borderWidth: 2,
                    hoverOffset: 4,
                }],
            },
            options: {
                cutout: "70%",
                plugins: {
                    tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed} (${pctOf(ctx.parsed)}%)` } },
                },
            },
        };
        const statusLegend = LEAD_STATUSES.map(([key, label], i) => ({
            key, label, color: S[i], count: statusCounts[i], pct: pctOf(statusCounts[i]),
        }));

        // 3. Pipeline funnel: open opportunities per stage (ordinal blue ramp)
        const openOpps = leads.filter((l) => l.active && l.type === "opportunity" && !isWon(l));
        const funnelStages = stages
            .filter((s) => !s.is_won)
            .map((s) => {
                const inStage = openOpps.filter((l) => l.stage_id && l.stage_id[0] === s.id);
                return { name: s.name, count: inStage.length, value: inStage.reduce((a, l) => a + (l.expected_revenue || 0), 0) };
            })
            .filter((s) => s.count);
        const funnel = {
            type: "bar",
            data: {
                labels: funnelStages.map((s) => s.name),
                datasets: [{ label: "Open deals", data: funnelStages.map((s) => s.count), backgroundColor: rampColors(funnelStages.length), ...barStyle }],
            },
            plugins: [barValueLabels],
            options: {
                indexAxis: "y",
                layout: { padding: { right: 28 } },
                plugins: {
                    fsBarValues: { enabled: true },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${ctx.parsed.x} deals · ${this.formatCompactMoney(funnelStages[ctx.dataIndex].value)} pipeline`,
                        },
                    },
                },
                scales: { x: gridScale(), y: shortLabels() },
            },
        };

        // 4. Leads by source (top 7 + Other)
        const bySource = {};
        for (const l of leads) {
            const name = l.source_id ? l.source_id[1] : "Not specified";
            bySource[name] = (bySource[name] || 0) + 1;
        }
        let sourceRows = Object.entries(bySource).sort((a, b) => b[1] - a[1]);
        if (sourceRows.length > 8) {
            const rest = sourceRows.slice(7).reduce((a, [, n]) => a + n, 0);
            sourceRows = [...sourceRows.slice(0, 7), ["Other sources", rest]];
        }
        const sources = {
            type: "bar",
            data: {
                labels: sourceRows.map(([name]) => name),
                datasets: [{ label: "Leads", data: sourceRows.map(([, n]) => n), backgroundColor: S[0], ...barStyle }],
            },
            plugins: [barValueLabels],
            options: {
                indexAxis: "y",
                layout: { padding: { right: 24 } },
                plugins: { fsBarValues: { enabled: true } },
                scales: { x: gridScale(), y: shortLabels() },
            },
        };

        // 5. Product line demand, new prospects vs existing customers (stacked)
        const byLine = {};
        for (const l of leads) {
            if (!l.product_line_id) {
                continue;
            }
            const name = l.product_line_id[1];
            byLine[name] = byLine[name] || { name, fresh: 0, existing: 0 };
            byLine[name][l.lead_relationship === "existing" ? "existing" : "fresh"]++;
        }
        const lineRows = Object.values(byLine).sort((a, b) => b.fresh + b.existing - (a.fresh + a.existing)).slice(0, 8);
        const tipRadius = { topLeft: 0, bottomLeft: 0, topRight: 4, bottomRight: 4 };
        const hasExisting = (ctx) => lineRows[ctx.dataIndex] && lineRows[ctx.dataIndex].existing > 0;
        const productDemand = {
            type: "bar",
            data: {
                labels: lineRows.map((r) => r.name),
                datasets: [
                    {
                        label: "New prospects",
                        data: lineRows.map((r) => r.fresh),
                        backgroundColor: S[0],
                        maxBarThickness: 24,
                        borderSkipped: false,
                        // 2px surface gap before the next segment; rounded only when it is the tip.
                        borderColor: FS_COLORS.surface,
                        borderWidth: (ctx) => (hasExisting(ctx) ? { top: 0, bottom: 0, left: 0, right: 2 } : 0),
                        borderRadius: (ctx) => (hasExisting(ctx) ? 0 : tipRadius),
                    },
                    {
                        label: "Existing customers",
                        data: lineRows.map((r) => r.existing),
                        backgroundColor: S[1],
                        maxBarThickness: 24,
                        borderSkipped: false,
                        borderRadius: tipRadius,
                    },
                ],
            },
            plugins: [barValueLabels],
            options: {
                indexAxis: "y",
                layout: { padding: { right: 24 } },
                interaction: { mode: "index", intersect: false },
                plugins: { fsBarValues: { enabled: true }, legend: legendTop("rectRounded") },
                scales: { x: gridScale({ stacked: true }), y: shortLabels({ stacked: true }) },
            },
        };

        // 6. Customer age distribution (column histogram)
        const ageCounts = AGE_BANDS.map(([, lo, hi]) =>
            leads.filter((l) => l.finsetter_age > 0 && l.finsetter_age >= lo && l.finsetter_age <= hi).length);
        const ages = {
            type: "bar",
            data: {
                labels: AGE_BANDS.map(([label]) => label),
                datasets: [{ label: "Customers", data: ageCounts, backgroundColor: S[0], ...barStyle }],
            },
            plugins: [barValueLabels],
            options: {
                layout: { padding: { top: 18 } },
                plugins: { fsBarValues: { enabled: true } },
                scales: { y: gridScale(), x: noGrid() },
            },
        };

        // 7. Preferred contact channels
        const channelDefs = [["WhatsApp", "channel_whatsapp"], ["Email", "channel_email"], ["SMS", "channel_sms"], ["AI Call", "channel_ai_call"]];
        const channelCounts = channelDefs.map(([, f]) => leads.filter((l) => l.active && l[f]).length);
        const channels = {
            type: "bar",
            data: {
                labels: channelDefs.map(([label]) => label),
                datasets: [{ label: "Leads opting in", data: channelCounts, backgroundColor: S[0], ...barStyle }],
            },
            plugins: [barValueLabels],
            options: {
                indexAxis: "y",
                layout: { padding: { right: 24 } },
                plugins: { fsBarValues: { enabled: true } },
                scales: { x: gridScale(), y: shortLabels() },
            },
        };

        // 8. First-response SLA (status meter rows: icon + label + count)
        const activeLeads = leads.filter((l) => l.active && l.lead_status !== "lost");
        const slaTotal = activeLeads.length || 1;
        const sla = SLA_ROWS.map(([key, label, icon, color]) => {
            const count = activeLeads.filter((l) => l.sla_status === key).length;
            return { key, label, icon, color, count, pct: Math.round((count / slaTotal) * 100) };
        });

        return {
            trend, status, statusLegend, statusTotal, funnel, sources, productDemand, ages, channels, sla,
            funnelHeight: Math.max(170, funnelStages.length * 40 + 30),
            sourceHeight: Math.max(200, sourceRows.length * 34 + 30),
            productHeight: Math.max(220, lineRows.length * 36 + 60),
        };
    }

    formatCompactMoney(v) {
        const n = v || 0;
        if (n >= 1e7) {
            return `${this.state.currencySymbol}${(n / 1e7).toFixed(2)} Cr`;
        }
        if (n >= 1e5) {
            return `${this.state.currencySymbol}${(n / 1e5).toFixed(1)} L`;
        }
        return this.formatMoney(n);
    }

    formatMoney(v) {
        return this.state.currencySymbol + Math.round(v || 0).toLocaleString("en-IN");
    }

    formatDate(value) {
        if (!value) {
            return "";
        }
        const [y, m, d] = value.split("-").map(Number);
        return new Date(y, m - 1, d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
    }

    async openAction(name, resModel, viewMode, domain, context, target) {
        const isDialog = target === "new";
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                name,
                res_model: resModel,
                views: viewMode.split(",").map((v) => [false, v === "tree" ? "list" : v]),
                domain: domain || [],
                context: context || {},
                target: target || "current",
            },
            // Quick-create dialogs refresh the KPIs once closed, so a new
            // lead/call/policy shows up without a manual page reload.
            isDialog ? { onClose: () => this.loadData() } : {}
        );
    }

    onNewLead() {
        this.openAction("New Lead", "crm.lead", "form", [], { default_type: "lead" }, "new");
    }

    onLogCall() {
        this.openAction("Log Call", "finsetter.call.log", "form", [], {}, "new");
    }

    onRecordConsent() {
        this.openAction("Record Consent", "finsetter.consent", "form", [], {}, "new");
    }

    onNewPolicy() {
        this.openAction("New Policy", "finsetter.policy", "form", [], {}, "new");
    }

    onNewTestimonial() {
        this.openAction("New Testimonial", "finsetter.testimonial", "form", [], {}, "new");
    }

    onOpenProducts() {
        this.openAction("Financial Products", "finsetter.financial.product", "list,form");
    }

    onOpenAppointments() {
        this.openAction("Appointments", "finsetter.appointment", "calendar,list,form");
    }

    onOpenRenewals() {
        this.openAction("Renewals", "finsetter.policy", "tree,form", [["state", "in", ["active", "renewal_due"]]]);
    }

    onOpenInsuranceLine(line) {
        this.openAction(line.name, "finsetter.policy", "tree,form", [["product_line_id", "=", line.id]]);
    }

    onOpenPipeline() {
        this.openAction("Pipeline", "crm.lead", "kanban,tree,form", [["type", "=", "opportunity"]], { default_type: "opportunity" });
    }

    onOpenWon() {
        this.openAction("Won Deals", "crm.lead", "tree,kanban,form", [["type", "=", "opportunity"], ["stage_id.is_won", "=", true]]);
    }

    onOpenCalls() {
        this.openAction("Call Logs", "finsetter.call.log", "tree,form");
    }

    onOpenConsentPending() {
        this.openAction("Consent Not Captured", "crm.lead", "tree,form", [["call_consent_status", "=", "unknown"]]);
    }

    onOpenSlaBreaches() {
        this.openAction("SLA Breaches", "crm.lead", "tree,form", [["sla_status", "=", "breached"]]);
    }

    async onMarkRenewed(policyId, ev) {
        ev.stopPropagation();
        if (this.state.busyPolicyId) {
            return;
        }
        this.state.busyPolicyId = policyId;
        try {
            await this.orm.call("finsetter.policy", "action_mark_renewed", [[policyId]]);
            this.notification.add("Policy marked as renewed.", { type: "success" });
            await this.loadData();
        } finally {
            this.state.busyPolicyId = null;
        }
    }
}

registry.category("actions").add("finsetter_crm_dashboard", FinsetterDashboard);

export default FinsetterDashboard;
