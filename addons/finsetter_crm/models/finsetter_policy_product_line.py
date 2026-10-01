# -*- coding: utf-8 -*-
from odoo import fields, models


class FinsetterPolicyProductLine(models.Model):
    """Master data: the product lines Finsetter sells (Health, Life, Motor...).

    Kept as a model (rather than a selection field) so the business can add
    new product lines from Settings without touching code, and so each line
    can carry its own default renewal cadence and color for the dashboard.
    """
    _name = 'finsetter.policy.product.line'
    _description = 'Finsetter Product Line'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Short code, e.g. HEALTH, LIFE, MOTOR")
    sequence = fields.Integer(default=10)
    renewal_cycle_months = fields.Integer(
        string='Default Renewal Cycle (months)', default=12,
        help="Used to suggest the next renewal date when none is set.")
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(default=True)
    icon = fields.Char(help="Font Awesome icon class shown on the dashboard, e.g. fa-heartbeat")
    website_url = fields.Char(
        string='Service Page', help="Link to this product's page on thefinsetter.com — "
                                     "share it with a lead in one click.")
    marketing_note = fields.Char(
        string='Talking Point', help="A ready-to-quote fact for advisors, "
                                      "e.g. '₹1 crore term cover for under ₹1,000/month'.")
    testimonial_ids = fields.One2many('finsetter.testimonial', 'product_line_id', string='Testimonials')

    _code_uniq = models.Constraint('unique(code)', 'Product line code must be unique.')
