# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FinsetterClaim(models.Model):
    """Spec section 5: Claims management, linked to a sold policy."""
    _name = 'finsetter.claim'
    _description = 'Insurance Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'claim_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    claim_number = fields.Char(tracking=True)
    policy_id = fields.Many2one('finsetter.policy', string='Policy', required=True, tracking=True, ondelete='cascade')
    partner_id = fields.Many2one(related='policy_id.partner_id', store=True, string='Customer')
    advisor_id = fields.Many2one(related='policy_id.advisor_id', store=True, string='Advisor')
    product_line_id = fields.Many2one(related='policy_id.product_line_id', store=True, string='Product Line')

    claim_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    incident_description = fields.Text(string='Incident / Reason for Claim')

    claim_amount = fields.Monetary(string='Claimed Amount', currency_field='currency_id')
    approved_amount = fields.Monetary(string='Approved Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    status = fields.Selection([
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('additional_docs', 'Additional Documents Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('settled', 'Settled'),
    ], default='submitted', required=True, tracking=True)

    settled_date = fields.Date()
    notes = fields.Text()

    @api.depends('policy_id.display_name', 'claim_number')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s%s' % (
                rec.policy_id.display_name or 'Claim',
                (' - #%s' % rec.claim_number) if rec.claim_number else '')

    def action_mark_under_review(self):
        self.write({'status': 'under_review'})

    def action_mark_approved(self):
        self.write({'status': 'approved'})

    def action_mark_settled(self):
        self.write({'status': 'settled', 'settled_date': fields.Date.context_today(self)})

    def action_mark_rejected(self):
        self.write({'status': 'rejected'})
