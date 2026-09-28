# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FinsetterCallLog(models.Model):
    """Structured customer call log.

    Replaces ad-hoc chatter notes with a proper record: outcome, duration,
    consent check, and an automatic follow-up activity when a call needs one.
    Still chatter-enabled so every call is visible on the lead/customer
    timeline.
    """
    _name = 'finsetter.call.log'
    _description = 'Customer Call Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'call_datetime desc'
    _rec_name = 'display_name'

    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity', tracking=True)
    advisor_id = fields.Many2one(
        'res.users', string='Advisor', default=lambda self: self.env.user, tracking=True, required=True)

    call_datetime = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    direction = fields.Selection([
        ('outbound', 'Outbound'),
        ('inbound', 'Inbound'),
    ], default='outbound', required=True, tracking=True)

    duration_minutes = fields.Float(string='Duration (minutes)')

    product_line_id = fields.Many2one('finsetter.policy.product.line', string='Product Line')

    outcome = fields.Selection([
        ('connected', 'Connected — Discussed'),
        ('no_answer', 'No Answer'),
        ('call_back', 'Call Back Requested'),
        ('not_interested', 'Not Interested'),
        ('converted', 'Converted / Policy Interest Confirmed'),
        ('wrong_number', 'Wrong Number'),
    ], required=True, default='connected', tracking=True)

    consent_confirmed = fields.Boolean(
        string='Call Consent Confirmed', default=False,
        help="Tick once the customer has confirmed they consent to be called on this line.")

    notes = fields.Text(string='Call Notes')
    follow_up_needed = fields.Boolean(default=False)
    follow_up_date = fields.Date()

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('partner_id', 'call_datetime', 'outcome')
    def _compute_display_name(self):
        outcome_labels = dict(self._fields['outcome'].selection)
        for rec in self:
            partner = rec.partner_id.name or 'Unknown'
            when = fields.Datetime.to_string(rec.call_datetime) if rec.call_datetime else ''
            rec.display_name = "%s — %s (%s)" % (partner, when, outcome_labels.get(rec.outcome, ''))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.follow_up_needed and rec.follow_up_date:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=rec.follow_up_date,
                    summary='Follow up on call with %s' % (rec.partner_id.name or ''),
                    user_id=rec.advisor_id.id or self.env.user.id,
                )
            if rec.lead_id:
                # First logged call on a lead counts as meeting Finsetter's
                # published 4-business-hour first-response promise.
                rec.lead_id._mark_sla_met()
        return records
