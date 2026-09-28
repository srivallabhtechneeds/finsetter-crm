/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Finsetter CRM — Executive Dashboard
 *
 * A single-screen view of pipeline health, renewals due, consent status and
 * team performance, styled after thefinsetter.com's brand. Pure read via
 * the standard ORM service — no custom controller needed.
 */
class FinsetterDashboard extends Component {
    static template = "finsetter_crm.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

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
        ] = await Promise.all([
            this.orm.searchCount("crm.lead", [["type", "=", "opportunity"], ["active", "=", true], ["probability", "<", 100]]),
            this.orm.readGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["active", "=", true], ["probability", "<", 100]],
                ["expected_revenue:sum"],
                []
            ),
            this.orm.readGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["stage_id.is_won", "=", true], ["date_closed", ">=", monthStart]],
                ["expected_revenue:sum"],
                []
            ),
            this.orm.searchCount("finsetter.policy", [
                ["state", "in", ["active", "renewal_due"]],
                ["renewal_date", "<=", in30],
            ]),
            this.orm.searchCount("crm.lead", [["active", "=", true], ["call_consent_status", "=", "unknown"]]),
            this.orm.searchCount("finsetter.call.log", [["call_datetime", ">=", `${toDate(today)} 00:00:00`]]),
            this.orm.searchCount("crm.lead", [["sla_status", "=", "breached"]]),
            this.orm.searchRead(
                "finsetter.policy",
                [["state", "in", ["active", "renewal_due"]], ["renewal_date", "<=", in30]],
                ["display_name", "partner_id", "product_line_id", "renewal_date", "days_to_renewal", "advisor_id", "premium_amount"],
                { order: "renewal_date asc", limit: 8 }
            ),
            this.orm.readGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["active", "=", true]],
                ["expected_revenue:sum"],
                ["product_line_id"]
            ),
            this.orm.readGroup(
                "crm.lead",
                [["type", "=", "opportunity"], ["stage_id.is_won", "=", true], ["date_closed", ">=", monthStart]],
                ["expected_revenue:sum"],
                ["user_id"]
            ),
            this.orm.searchRead(
                "finsetter.testimonial",
                [],
                ["name", "role_location", "quote", "product_line_id"],
                { limit: 20 }
            ),
            this.orm.searchRead(
                "finsetter.policy.product.line",
                [],
                ["name", "icon", "color"],
                { order: "sequence asc" }
            ),
            this.orm.readGroup(
                "finsetter.policy",
                [["state", "in", ["active", "renewal_due"]]],
                ["premium_amount:sum"],
                ["product_line_id"]
            ),
        ]);

        this.state.pipelineCount = pipelineCount;
        this.state.pipelineValue = (pipelineGroups[0] && pipelineGroups[0].expected_revenue) || 0;
        this.state.wonMonthCount = (wonMonthGroups[0] && wonMonthGroups[0].__count) || 0;
        this.state.wonMonthValue = (wonMonthGroups[0] && wonMonthGroups[0].expected_revenue) || 0;
        this.state.renewalsSoonCount = renewalsSoonCount;
        this.state.consentPendingCount = consentPendingCount;
        this.state.callsTodayCount = callsTodayCount;
        this.state.slaBreachedCount = slaBreachedCount;
        this.state.renewals = renewals;

        const donutPalette = ["#2868a8", "#0b7a75", "#e3a62f", "#c55a4e", "#58658b", "#7edbd0", "#a56a1a", "#3f4b5c", "#8a4fd6", "#1f9e73", "#d67ab1", "#4a90d9", "#c9a227"];
        const plColor = {};
        productLineGroups
            .filter((g) => g.product_line_id)
            .forEach((g, idx) => { plColor[g.product_line_id[1]] = donutPalette[idx % donutPalette.length]; });

        const maxPl = Math.max(1, ...productLineGroups.map((g) => g.expected_revenue || 0));
        this.state.productLines = productLineGroups
            .filter((g) => g.product_line_id)
            .map((g) => ({
                name: g.product_line_id[1],
                value: g.expected_revenue || 0,
                count: g.__count,
                pct: Math.round(((g.expected_revenue || 0) / maxPl) * 100),
                color: plColor[g.product_line_id[1]],
            }))
            .sort((a, b) => b.value - a.value);

        // SVG donut: stroke-dasharray/dashoffset segments around a r=40 circle.
        const totalPl = productLineGroups.reduce((sum, g) => sum + (g.expected_revenue || 0), 0) || 1;
        const circumference = 2 * Math.PI * 40;
        let cumulative = 0;
        this.state.donutSegments = productLineGroups
            .filter((g) => g.product_line_id)
            .map((g) => {
                const value = g.expected_revenue || 0;
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
                    count: g.__count,
                    premium: g.premium_amount || 0,
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

        const maxLb = Math.max(1, ...leaderboardGroups.map((g) => g.expected_revenue || 0));
        this.state.leaderboard = leaderboardGroups
            .filter((g) => g.user_id)
            .map((g) => ({
                name: g.user_id[1],
                value: g.expected_revenue || 0,
                count: g.__count,
                pct: Math.round(((g.expected_revenue || 0) / maxLb) * 100),
            }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);

        this.state.testimonial = testimonials.length
            ? testimonials[Math.floor(Math.random() * testimonials.length)]
            : null;

        this.state.loading = false;
    }

    onNewTestimonial() {
        this.openAction("finsetter.testimonial", "form", [], {}, "new");
    }

    formatMoney(v) {
        return this.state.currencySymbol + Math.round(v || 0).toLocaleString("en-IN");
    }

    async openAction(resModel, viewMode, domain, context, target) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: resModel,
            res_model: resModel,
            view_mode: viewMode || "tree,form",
            views: (viewMode || "tree,form").split(",").map((v) => [false, v === "tree" ? "list" : v]),
            domain: domain || [],
            context: context || {},
            target: target || "current",
        });
    }

    onNewLead() {
        this.openAction("crm.lead", "form", [], { default_type: "lead" }, "new");
    }

    onLogCall() {
        this.openAction("finsetter.call.log", "form", [], {}, "new");
    }

    onRecordConsent() {
        this.openAction("finsetter.consent", "form", [], {}, "new");
    }

    onNewPolicy() {
        this.openAction("finsetter.policy", "form", [], {}, "new");
    }

    onOpenProducts() {
        this.openAction("finsetter.financial.product", "list,form", [], {});
    }

    onOpenAppointments() {
        this.openAction("finsetter.appointment", "calendar,list,form", [], {});
    }

    onOpenRenewals() {
        this.openAction("finsetter.policy", "tree,form", [["state", "in", ["active", "renewal_due"]]], {});
    }

    onOpenInsuranceLine(lineId) {
        this.openAction("finsetter.policy", "tree,form", [["product_line_id", "=", lineId]], {});
    }

    onOpenPipeline() {
        this.openAction("crm.lead", "kanban,tree,form", [["type", "=", "opportunity"]], { default_type: "opportunity" });
    }

    onOpenConsentPending() {
        this.openAction("crm.lead", "tree,form", [["call_consent_status", "=", "unknown"]], {});
    }

    onOpenSlaBreaches() {
        this.openAction("crm.lead", "tree,form", [["sla_status", "=", "breached"]], {});
    }

    async onMarkRenewed(policyId, ev) {
        ev.stopPropagation();
        await this.orm.call("finsetter.policy", "action_mark_renewed", [[policyId]]);
        await this.loadData();
    }
}

registry.category("actions").add("finsetter_crm_dashboard", FinsetterDashboard);

export default FinsetterDashboard;
