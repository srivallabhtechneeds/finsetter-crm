# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FinsetterConsent(models.Model):
    """Auditable consent register.

    Finsetter is SEBI/IRDAI regulated and calls/emails/WhatsApps prospects
    before a policy is sold, so every consent grant/withdrawal needs a
    timestamped, attributable record — this is that record. Every write is
    chatter-logged (mail.thread) so a compliance officer can reconstruct the
    full history for any customer.
    """
    _name = 'finsetter.consent'
    _description = 'Consent Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_obtained desc'
    _rec_name = 'display_name'

    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Related Lead/Opportunity', tracking=True)
    advisor_id = fields.Many2one(
        'res.users', string='Recorded By', default=lambda self: self.env.user, tracking=True)

    consent_type = fields.Selection([
        ('call', 'Outbound Call Consent'),
        ('whatsapp', 'WhatsApp Communication Consent'),
        ('email', 'Email Communication Consent'),
        ('data_processing', 'Data Processing / KYC Consent'),
        ('marketing', 'Marketing Communication Consent'),
    ], required=True, default='call', tracking=True)

    status = fields.Selection([
        ('granted', 'Granted'),
        ('declined', 'Declined'),
        ('withdrawn', 'Withdrawn'),
        ('expired', 'Expired'),
    ], required=True, default='granted', tracking=True)

    channel = fields.Selection([
        ('call', 'Phone Call'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('web_form', 'Website Form'),
        ('in_person', 'In Person'),
    ], required=True, default='call', tracking=True)

    date_obtained = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    valid_until = fields.Date(string='Valid Until', tracking=True,
                               help="Leave empty if consent does not expire.")
    proof_reference = fields.Char(
        string='Proof / Reference', help="Call recording ID, form submission ID, email thread, etc.")
    notes = fields.Text()

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('partner_id', 'consent_type', 'status')
    def _compute_display_name(self):
        type_labels = dict(self._fields['consent_type'].selection)
        status_labels = dict(self._fields['status'].selection)
        for rec in self:
            partner = rec.partner_id.name or 'Unknown'
            rec.display_name = "%s — %s (%s)" % (
                partner,
                type_labels.get(rec.consent_type, ''),
                status_labels.get(rec.status, ''),
            )
