# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class FinsetterPolicy(models.Model):
    """A sold insurance / financial product held by a customer.

    This is the anchor of the renewal pipeline: `ir_cron_data.xml` scans
    `renewal_date` daily and schedules escalating reminder activities at
    30/15/7/1 days out, matching Finsetter's "we call before you even
    remember" positioning on the website.
    """
    _name = 'finsetter.policy'
    _description = 'Customer Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'renewal_date'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Originating Lead', tracking=True)
    advisor_id = fields.Many2one(
        'res.users', string='Advisor', default=lambda self: self.env.user, tracking=True)

    product_line_id = fields.Many2one(
        'finsetter.policy.product.line', string='Product Line', required=True, tracking=True)

    policy_number = fields.Char(tracking=True)
    insurer_name = fields.Char(string='Insurer / Institution', tracking=True)

    sum_insured = fields.Monetary(string='Sum Insured / Cover Amount', currency_field='currency_id')
    premium_amount = fields.Monetary(string='Premium Amount', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    start_date = fields.Date(default=fields.Date.context_today, tracking=True)
    renewal_date = fields.Date(string='Renewal / Expiry Date', required=True, tracking=True)

    state = fields.Selection([
        ('active', 'Active'),
        ('renewal_due', 'Renewal Due'),
        ('lapsed', 'Lapsed'),
        ('renewed', 'Renewed'),
        ('cancelled', 'Cancelled'),
    ], default='active', required=True, tracking=True)

    days_to_renewal = fields.Integer(
        string='Days to Renewal', compute='_compute_days_to_renewal', store=True)

    consent_id = fields.Many2one(
        'finsetter.consent', string='Related Consent Record',
        help="Data-processing / call consent captured for this policy.")

    notes = fields.Text()

    claim_ids = fields.One2many('finsetter.claim', 'policy_id', string='Claims')
    claim_count = fields.Integer(compute='_compute_claim_count')

    def _compute_claim_count(self):
        for rec in self:
            rec.claim_count = len(rec.claim_ids)

    def action_view_claims(self):
        self.ensure_one()
        return {
            'name': 'Claims',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.claim',
            'view_mode': 'list,form',
            'domain': [('policy_id', '=', self.id)],
            'context': {'default_policy_id': self.id},
        }

    def action_file_claim(self):
        self.ensure_one()
        return {
            'name': 'File Claim',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.claim',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_policy_id': self.id},
        }

    @api.depends('partner_id', 'product_line_id', 'policy_number')
    def _compute_display_name(self):
        for rec in self:
            parts = [rec.partner_id.name or 'New Customer']
            if rec.product_line_id:
                parts.append(rec.product_line_id.name)
            if rec.policy_number:
                parts.append('#%s' % rec.policy_number)
            rec.display_name = ' — '.join(parts)

    @api.depends('renewal_date')
    def _compute_days_to_renewal(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.renewal_date:
                rec.days_to_renewal = (rec.renewal_date - today).days
            else:
                rec.days_to_renewal = 0

    def action_mark_renewed(self):
        """Roll the policy forward by its product line's renewal cycle and
        reopen it as active — used from the renewal reminder activity or the
        policy form's 'Mark Renewed' button."""
        for rec in self:
            months = rec.product_line_id.renewal_cycle_months or 12
            new_date = (rec.renewal_date or fields.Date.context_today(rec)) + relativedelta(months=months)
            rec.write({
                'renewal_date': new_date,
                'start_date': fields.Date.context_today(rec),
                'state': 'active',
            })
            rec.message_post(body="Policy renewed. Next renewal set to %s." % new_date)

    def action_mark_lapsed(self):
        self.write({'state': 'lapsed'})

    @api.model
    def _cron_flag_renewals_due(self):
        """Scheduled action: flag policies entering their renewal window and
        create escalating follow-up activities. Called by ir_cron_data.xml.
        """
        today = fields.Date.context_today(self)
        windows = [30, 15, 7, 1]
        policies = self.search([('state', '=', 'active'), ('renewal_date', '!=', False)])
        for policy in policies:
            delta = (policy.renewal_date - today).days
            if delta < 0:
                policy.write({'state': 'lapsed'})
                policy.message_post(body="Renewal date passed without action — marked as lapsed.")
                continue
            if delta in windows:
                if policy.state != 'renewal_due':
                    policy.write({'state': 'renewal_due'})
                summary = "Renewal due in %d day(s) — %s" % (delta, policy.display_name)
                policy.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=policy.renewal_date,
                    summary=summary,
                    note="Call the customer to renew their %s policy before it lapses." % (
                        policy.product_line_id.name or 'insurance'),
                    user_id=policy.advisor_id.id or self.env.uid,
                )
