# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    product_line_id = fields.Many2one(
        'finsetter.policy.product.line', string='Primary Product Line',
        help="Leads for this product line are auto-assigned round-robin to this team's members.")
    last_assigned_partner_id = fields.Many2one(
        'res.users', string='Last Auto-Assigned Advisor',
        help="Internal pointer used by the round-robin lead assignment cron.")
