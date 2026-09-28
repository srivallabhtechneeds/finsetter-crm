# -*- coding: utf-8 -*-
from odoo import fields, models


class FinsetterFinancialProduct(models.Model):
    """Spec section 2: Financial Products — an individual sellable product,
    distinct from `finsetter.policy.product.line` (the broad category, e.g.
    'Health Insurance'): one category can carry many concrete products
    (different insurers' term plans, different AMCs' funds, etc).
    """
    _name = 'finsetter.financial.product'
    _description = 'Finsetter Financial Product'
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    name = fields.Char(string='Product Name', required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    product_line_id = fields.Many2one(
        'finsetter.policy.product.line', string='Category', required=True, tracking=True,
        help="Term Insurance, Health Insurance, Investment Plans / Mutual Funds, "
             "Tax-Saving Products, Retirement / Pension Plans, Estate Planning, "
             "Family Financial Planning, etc.")
    provider = fields.Char(string='Provider / Insurer / AMC', tracking=True)

    eligibility_criteria = fields.Text(
        string='Eligibility', help="Age band, income, health, residency etc.")
    min_age = fields.Integer(string='Min Age')
    max_age = fields.Integer(string='Max Age')

    amount_type = fields.Selection([
        ('premium', 'Premium'),
        ('investment', 'Investment Amount'),
        ('sum_assured', 'Sum Assured / Cover'),
    ], default='premium', string='Amount Type')
    min_amount = fields.Monetary(string='Min Amount', currency_field='currency_id')
    max_amount = fields.Monetary(string='Max Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    tenure_months_min = fields.Integer(string='Min Tenure (months)')
    tenure_months_max = fields.Integer(string='Max Tenure (months)')

    benefits = fields.Html(string='Key Benefits')
    documents_required = fields.Text(string='Documents Required')

    passport_number = fields.Char(string='Passport Number', tracking=True,
        help="Client's passport number — required for travel insurance and NRI products.")
    passport_issue_date = fields.Date(string='Passport Issue Date')
    passport_expiry_date = fields.Date(string='Passport Expiry Date')
    passport_nationality = fields.Char(string='Passport Nationality')

    commission_rate = fields.Float(string='Commission Rate (%)')
    commission_flat = fields.Monetary(string='Commission (Flat)', currency_field='currency_id')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('discontinued', 'Discontinued'),
    ], default='draft', required=True, tracking=True)

    website_url = fields.Char(string='Service Page')

    match_ids = fields.One2many('finsetter.lead.product.match', 'product_id', string='Lead Matches')
    match_count = fields.Integer(compute='_compute_match_count')

    def _compute_match_count(self):
        for rec in self:
            rec.match_count = len(rec.match_ids)

    def action_view_matches(self):
        self.ensure_one()
        return {
            'name': 'Lead Matches',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.lead.product.match',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }
