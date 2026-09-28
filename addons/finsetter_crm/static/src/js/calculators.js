/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Finsetter CRM — Financial Calculators (spec section 7).
 *
 * Seven advisor-facing calculators, pure client-side math (no server round
 * trip needed to compute), matching the tools published on
 * thefinsetter.com/calculators.html: Term Insurance, Health Insurance,
 * SIP/Investment, Tax Saving, Retirement Planning, Loan/EMI and Compound
 * Interest. Every formula here is a standard, widely published financial
 * formula (simple/compound interest, EMI, SIP future value, retirement
 * annuity) — results are clearly labelled as estimates, since actual
 * insurance premiums are always finally set by the insurer.
 */
class FinsetterCalculators extends Component {
    static template = "finsetter_crm.Calculators";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            activeTab: "term",
            currencySymbol: "₹",

            term: { age: 30, sumAssured: 10000000, termYears: 20, smoker: false, result: null },
            health: { age: 30, sumInsured: 1000000, familySize: 2, cityTier: "1", result: null },
            sip: { monthlyAmount: 5000, annualReturnPct: 12, years: 15, result: null },
            tax: { investmentAmount: 150000, taxSlabPct: 30, result: null },
            retirement: {
                currentAge: 30, retirementAge: 60, monthlyExpensesToday: 40000,
                inflationPct: 6, preReturnPct: 12, postReturnPct: 7, lifeExpectancyAge: 85,
                result: null,
            },
            loan: { principal: 2000000, annualRatePct: 9, tenureYears: 20, result: null },
            compound: { principal: 100000, annualRatePct: 8, compoundsPerYear: 4, years: 10, result: null },
        });

        // Compute an initial result for every tab so the panel isn't empty.
        this.computeTerm();
        this.computeHealth();
        this.computeSip();
        this.computeTax();
        this.computeRetirement();
        this.computeLoan();
        this.computeCompound();
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    formatMoney(v) {
        if (v === null || v === undefined || isNaN(v)) return "-";
        return this.state.currencySymbol + Math.round(v).toLocaleString("en-IN");
    }

    onFieldChange(section, field, ev, isCheckbox) {
        const raw = isCheckbox ? ev.target.checked : ev.target.value;
        this.state[section][field] = isCheckbox ? raw : (raw === "" ? 0 : Number(raw));
        this["compute" + section.charAt(0).toUpperCase() + section.slice(1)]();
    }

    onSelectChange(section, field, ev) {
        this.state[section][field] = ev.target.value;
        this["compute" + section.charAt(0).toUpperCase() + section.slice(1)]();
    }

    // --- 1. Term Insurance --------------------------------------------
    computeTerm() {
        const s = this.state.term;
        const age = Math.max(18, s.age || 18);
        const rate = Math.max(0.3, 0.5 + (age - 25) * 0.05); // illustrative rate per 1000 sum assured / year
        let annual = (s.sumAssured / 1000) * rate;
        if (s.smoker) annual *= 1.5;
        s.result = { annualPremium: annual, monthlyPremium: annual / 12 };
    }

    // --- 2. Health Insurance -------------------------------------------
    computeHealth() {
        const s = this.state.health;
        const base = (s.sumInsured / 100000) * 800; // illustrative ₹800 / lakh cover baseline
        const ageFactor = 1 + Math.max(0, (s.age || 0) - 30) * 0.02;
        const familyFactor = 1 + Math.max(0, (s.familySize || 1) - 1) * 0.35;
        const cityFactor = s.cityTier === "1" ? 1.15 : s.cityTier === "2" ? 1.0 : 0.9;
        const annual = base * ageFactor * familyFactor * cityFactor;
        s.result = { annualPremium: annual, monthlyPremium: annual / 12 };
    }

    // --- 3. SIP / Investment --------------------------------------------
    computeSip() {
        const s = this.state.sip;
        const r = (s.annualReturnPct || 0) / 100 / 12;
        const n = (s.years || 0) * 12;
        const invested = (s.monthlyAmount || 0) * n;
        let fv;
        if (r === 0) {
            fv = invested;
        } else {
            fv = s.monthlyAmount * ((Math.pow(1 + r, n) - 1) / r) * (1 + r);
        }
        s.result = { investedAmount: invested, futureValue: fv, estimatedReturns: fv - invested };
    }

    // --- 4. Tax Saving (Section 80C style) -------------------------------
    computeTax() {
        const s = this.state.tax;
        const eligible = Math.min(s.investmentAmount || 0, 150000);
        const taxSaved = eligible * ((s.taxSlabPct || 0) / 100);
        s.result = { eligibleAmount: eligible, taxSaved };
    }

    // --- 5. Retirement Planning ------------------------------------------
    computeRetirement() {
        const s = this.state.retirement;
        const yearsToRetirement = Math.max(0, (s.retirementAge || 0) - (s.currentAge || 0));
        const yearsInRetirement = Math.max(1, (s.lifeExpectancyAge || 0) - (s.retirementAge || 0));
        const inflation = (s.inflationPct || 0) / 100;
        const futureMonthlyExpense = (s.monthlyExpensesToday || 0) * Math.pow(1 + inflation, yearsToRetirement);
        const annualExpenseAtRetirement = futureMonthlyExpense * 12;
        const postReturn = (s.postReturnPct || 0) / 100;
        const realReturn = (1 + postReturn) / (1 + inflation) - 1;
        let corpusRequired;
        if (Math.abs(realReturn) < 1e-6) {
            corpusRequired = annualExpenseAtRetirement * yearsInRetirement;
        } else {
            corpusRequired = annualExpenseAtRetirement * (1 - Math.pow(1 + realReturn, -yearsInRetirement)) / realReturn;
        }
        const preReturn = (s.preReturnPct || 0) / 100 / 12;
        const nMonths = yearsToRetirement * 12;
        let requiredMonthlySip = 0;
        if (nMonths > 0) {
            const factor = preReturn === 0 ? nMonths : ((Math.pow(1 + preReturn, nMonths) - 1) / preReturn) * (1 + preReturn);
            requiredMonthlySip = factor > 0 ? corpusRequired / factor : 0;
        }
        s.result = {
            futureMonthlyExpense, corpusRequired, requiredMonthlySip, yearsToRetirement, yearsInRetirement,
        };
    }

    // --- 6. Loan / EMI ----------------------------------------------------
    computeLoan() {
        const s = this.state.loan;
        const r = (s.annualRatePct || 0) / 100 / 12;
        const n = (s.tenureYears || 0) * 12;
        let emi = 0;
        if (n > 0) {
            emi = r === 0 ? s.principal / n : (s.principal * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
        }
        const totalPayment = emi * n;
        s.result = { emi, totalPayment, totalInterest: totalPayment - (s.principal || 0) };
    }

    // --- 7. Compound Interest ---------------------------------------------
    computeCompound() {
        const s = this.state.compound;
        const n = Math.max(1, s.compoundsPerYear || 1);
        const amount = (s.principal || 0) * Math.pow(1 + (s.annualRatePct || 0) / 100 / n, n * (s.years || 0));
        s.result = { maturityAmount: amount, interestEarned: amount - (s.principal || 0) };
    }

    async onSaveToLead() {
        // Optional convenience: post the currently-active tab's result as a
        // chatter note on a lead, if opened from one (context carries
        // default_lead_id). Silently does nothing outside that context.
        const leadId = this.props.action && this.props.action.context && this.props.action.context.default_lead_id;
        if (!leadId) {
            this.notification.add("Open this from a lead's 'Calculators' button to save a result to it.", { type: "warning" });
            return;
        }
        const tab = this.state.activeTab;
        const result = this.state[tab].result || {};
        const lines = Object.entries(result).map(([k, v]) => `${k}: ${typeof v === "number" ? Math.round(v).toLocaleString("en-IN") : v}`);
        await this.orm.call("crm.lead", "message_post", [[leadId]], {
            body: `Finsetter Calculator (${tab}):<br/>` + lines.join("<br/>"),
        });
        this.notification.add("Saved to the lead's activity log.", { type: "success" });
    }
}

registry.category("actions").add("finsetter_crm_calculators", FinsetterCalculators);

export default FinsetterCalculators;
