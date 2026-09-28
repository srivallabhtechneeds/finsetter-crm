# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FinsetterDocument(models.Model):
    """Spec section 8: Documents & Compliance — secure storage + KYC
    verification workflow for customer/lead documents, on top of the
    existing consent register and Odoo's own chatter audit trail."""
    _name = 'finsetter.document'
    _description = 'Finsetter Document / KYC Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Lead')
    policy_id = fields.Many2one('finsetter.policy', string='Related Policy')

    document_type = fields.Selection([
        ('pan', 'PAN Card'),
        ('aadhaar', 'Aadhaar Card'),
        ('passport', 'Passport'),
        ('address_proof', 'Address Proof'),
        ('income_proof', 'Income Proof'),
        ('bank_statement', 'Bank Statement'),
        ('photo', 'Photograph'),
        ('policy_document', 'Policy Document'),
        ('signed_form', 'Signed Application / Proposal Form'),
        ('other', 'Other'),
    ], required=True, tracking=True)

    attachment = fields.Binary(string='File', attachment=True)
    attachment_name = fields.Char(string='File Name')

    verification_status = fields.Selection([
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ], default='pending', required=True, tracking=True)
    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True)
    verified_date = fields.Datetime(readonly=True)
    rejection_reason = fields.Char()
    expiry_date = fields.Date()

    @api.depends('partner_id.name', 'document_type')
    def _compute_display_name(self):
        type_labels = dict(self._fields['document_type'].selection)
        for rec in self:
            rec.display_name = '%s - %s' % (
                rec.partner_id.name or 'Unassigned', type_labels.get(rec.document_type, 'Document'))

    def action_verify(self):
        self.write({
            'verification_status': 'verified',
            'verified_by': self.env.uid,
            'verified_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({'verification_status': 'rejected'})
