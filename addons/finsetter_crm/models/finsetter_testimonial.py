# -*- coding: utf-8 -*-
from odoo import fields, models


class FinsetterTestimonial(models.Model):
    """Real client testimonials published on thefinsetter.com.

    Kept in the CRM so advisors have ready-made, proven proof-points to
    quote on calls (filterable by product line), and so the dashboard can
    surface a featured one — rather than these living only on the website.
    """
    _name = 'finsetter.testimonial'
    _description = 'Client Testimonial'
    _order = 'sequence, id'

    name = fields.Char(string='Customer Name', required=True)
    role_location = fields.Char(string='Role / Location', help='e.g. "IT Professional, Hyderabad"')
    quote = fields.Text(required=True)
    product_line_id = fields.Many2one('finsetter.policy.product.line', string='Related Product Line')
    rating = fields.Selection([
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
    ], default='5')
    source = fields.Selection([
        ('website', 'Website'),
        ('google_review', 'Google Review'),
        ('direct', 'Shared Directly'),
    ], default='website')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
