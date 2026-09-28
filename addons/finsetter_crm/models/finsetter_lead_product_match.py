# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FinsetterLeadProductMatch(models.Model):
    """Spec section 3: Lead <-> Product matching. An advisor (or the
    `action_generate_matches` recommendation engine below) links a lead to
    candidate financial products and tracks the customer's response through
    to conversion.
    """
    _name = 'finsetter.lead.product.match'
    _description = 'Lead / Product Match'
    _inherit = ['mail.thread']
    _order = 'score desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name')

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True, ondelete='cascade', tracking=True)
    partner_id = fields.Many2one(related='lead_id.partner_id', string='Customer', store=True)
    product_id = fields.Many2one('finsetter.financial.product', string='Product', required=True, tracking=True)
    product_line_id = fields.Many2one(related='product_id.product_line_id', store=True, string='Category')

    score = fields.Integer(
        string='Match Score', default=0,
        help="0-100 fit score computed from age/budget/category alignment with the product's eligibility.")
    reason = fields.Text(string='Why This Match', help="Auto-generated or advisor rationale.")

    status = fields.Selection([
        ('recommended', 'Recommended'),
        ('interested', 'Interested'),
        ('pending', 'Pending Decision'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted'),
    ], default='recommended', required=True, tracking=True)

    advisor_id = fields.Many2one('res.users', string='Advisor', default=lambda self: self.env.user)

    @api.depends('lead_id.name', 'product_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s -> %s' % (rec.lead_id.name or 'Lead', rec.product_id.name or 'Product')

    def action_mark_interested(self):
        self.write({'status': 'interested'})

    def action_mark_pending(self):
        self.write({'status': 'pending'})

    def action_mark_rejected(self):
        self.write({'status': 'rejected'})

    def action_mark_converted(self):
        self.write({'status': 'converted'})

    @api.model
    def _score_lead_for_product(self, lead, product):
        """Simple, transparent scoring: category + age fit + budget fit.
        Deliberately not a black-box ML model — an advisor (or auditor) can
        read `reason` and see exactly why a product was recommended."""
        score = 40  # base score: any active product in the lead's category
        reasons = []
        if lead.product_line_id and lead.product_line_id == product.product_line_id:
            score += 20
            reasons.append("matches the lead's selected product line")

        age = lead.finsetter_age or 0
        if age and (product.min_age or product.max_age):
            lo, hi = product.min_age or 0, product.max_age or 999
            if lo <= age <= hi:
                score += 20
                reasons.append("customer age %s fits the %s-%s eligibility band" % (age, lo, hi))
            else:
                score -= 30
                reasons.append("customer age %s is outside the %s-%s eligibility band" % (age, lo, hi))

        budget = lead.expected_revenue or lead.finsetter_annual_income or 0
        if budget and (product.min_amount or product.max_amount):
            lo, hi = product.min_amount or 0, product.max_amount or float('inf')
            if lo <= budget <= hi:
                score += 20
                reasons.append("budget aligns with this product's typical amount range")

        return max(0, min(100, score)), '; '.join(reasons) or 'General category match.'

    @api.model
    def action_generate_matches(self, lead_ids):
        """Recommendation engine: for each lead, score every active product
        in its chosen category (or all active products if none chosen) and
        create matches scoring 40+. Called from the lead form's
        'Find Matching Products' button."""
        leads = self.env['crm.lead'].browse(lead_ids)
        Product = self.env['finsetter.financial.product']
        created = self.browse()
        for lead in leads:
            domain = [('status', '=', 'active')]
            if lead.product_line_id:
                domain.append(('product_line_id', '=', lead.product_line_id.id))
            candidates = Product.search(domain)
            existing_products = self.search([('lead_id', '=', lead.id)]).mapped('product_id')
            for product in candidates - existing_products:
                score, reason = self._score_lead_for_product(lead, product)
                if score >= 40:
                    created |= self.create({
                        'lead_id': lead.id,
                        'product_id': product.id,
                        'score': score,
                        'reason': reason,
                    })
        return created
