# -*- coding: utf-8 -*-
from html import escape

from odoo import api, fields, models


FOLLOWUP_PURPOSES = [
    ('scheduling', 'Meeting / Call Scheduling'),
    ('upgrade', 'Policy Upgrade'),
    ('renewal', 'Policy Renewal'),
]
FOLLOWUP_CHANNELS = [
    ('email', 'Email'),
    ('sms', 'SMS'),
    ('whatsapp', 'WhatsApp'),
    ('voice', 'Automated Voice Call (TTS)'),
]


class FinsetterFollowupTemplate(models.Model):
    _name = 'finsetter.followup.template'
    _description = 'Finsetter Follow-up Template'
    _order = 'purpose, channel, name'

    name = fields.Char(required=True)
    purpose = fields.Selection(FOLLOWUP_PURPOSES, required=True)
    channel = fields.Selection(FOLLOWUP_CHANNELS, required=True)
    subject = fields.Char()
    body = fields.Text(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('purpose_channel_unique', 'unique(purpose, channel)',
         'Only one active template slot is allowed per purpose and channel.'),
    ]


class FinsetterFollowupLog(models.Model):
    _name = 'finsetter.followup.log'
    _description = 'Finsetter Follow-up Message'
    _inherit = ['mail.thread', 'finsetter.messaging.mixin']
    _order = 'create_date desc'

    name = fields.Char(required=True, tracking=True)
    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='set null', tracking=True)
    policy_id = fields.Many2one('finsetter.policy', string='Policy', ondelete='set null', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    template_id = fields.Many2one('finsetter.followup.template', string='Template')
    purpose = fields.Selection(FOLLOWUP_PURPOSES, required=True, tracking=True)
    channel = fields.Selection(FOLLOWUP_CHANNELS, required=True, tracking=True)
    subject = fields.Char()
    body = fields.Text()
    status = fields.Selection([
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='queued', required=True, tracking=True)
    provider_reference = fields.Char(index=True, copy=False)
    mail_id = fields.Many2one('mail.mail', readonly=True, copy=False, ondelete='set null')
    scheduled_at = fields.Datetime(default=fields.Datetime.now, required=True)
    sent_at = fields.Datetime(readonly=True, copy=False)
    replied_at = fields.Datetime(readonly=True, copy=False)
    error_message = fields.Text(readonly=True, copy=False)
    renewal_cycle_date = fields.Date(index=True, copy=False)
    reminder_day = fields.Integer(copy=False)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('policy_id') and not vals.get('renewal_cycle_date'):
                policy = self.env['finsetter.policy'].browse(vals['policy_id'])
                vals['renewal_cycle_date'] = policy.renewal_date
            if not vals.get('name'):
                vals['name'] = 'Follow-up'
        return super().create(vals_list)

    def _template_values(self):
        self.ensure_one()
        policy = self.policy_id
        partner = self.partner_id
        lead = self.lead_id or (policy.lead_id if policy else self.env['crm.lead'])
        renewal_date = policy.renewal_date if policy else False
        return {
            'customer_name': partner.name or '',
            'policy_number': policy.policy_number or '' if policy else '',
            'renewal_date': fields.Date.to_string(renewal_date) if renewal_date else '',
            'premium': str(policy.renewal_quote_amount or policy.premium_amount) if policy else '',
            'payment_link': policy.payment_link or '' if policy else '',
            'lead_name': lead.name or '',
            'company_name': self.env.company.name or '',
        }

    def _render_template(self, value):
        self.ensure_one()
        rendered = value or ''
        for key, replacement in self._template_values().items():
            rendered = rendered.replace('{%s}' % key, str(replacement))
        return rendered

    def _callback_url(self, path, extra=''):
        params = self.env['ir.config_parameter'].sudo()
        base_url = params.get_param('finsetter_crm.public_webhook_url', '').rstrip('/')
        token = params.get_param('finsetter_crm.webhook_token')
        if not base_url or not token:
            return False
        from urllib.parse import urlencode
        query = {'token': token}
        if extra:
            query.update(dict(item.split('=', 1) for item in extra.split('&')))
        return '%s%s?%s' % (base_url, path, urlencode(query))

    def action_send(self):
        for log in self:
            if log.status not in ('queued', 'failed'):
                continue
            if log.scheduled_at and log.scheduled_at > fields.Datetime.now():
                continue
            template = log.template_id or self.env['finsetter.followup.template'].search([
                ('purpose', '=', log.purpose), ('channel', '=', log.channel), ('active', '=', True)], limit=1)
            if not template:
                log.write({'status': 'failed', 'error_message': 'No active template for this purpose and channel.'})
                continue

            subject = log._render_template(template.subject)
            body = log._render_template(template.body)
            values = {'template_id': template.id, 'subject': subject, 'body': body}
            destination = log.partner_id.email or ''
            reference = False
            if log.channel == 'email':
                if not destination:
                    log.write({'status': 'failed', 'error_message': 'Customer has no email address.'})
                    continue
                mail = self.env['mail.mail'].sudo().create({
                    'subject': subject or log.name,
                    'body_html': '<div>%s</div>' % escape(body).replace('\n', '<br/>'),
                    'email_to': destination,
                    'email_from': self.env.user.email_formatted or self.env.company.email or '',
                    'model': log._name,
                    'res_id': log.id,
                    'auto_delete': False,
                })
                mail.send()
                if mail.state == 'exception':
                    log.write({**values, 'mail_id': mail.id, 'status': 'failed',
                               'error_message': mail.failure_reason or 'Email delivery failed.'})
                    continue
                reference = str(mail.id)
                values['mail_id'] = mail.id
            elif log.channel in ('sms', 'whatsapp'):
                phone = log.partner_id.mobile or log.partner_id.phone
                callback = log._callback_url('/finsetter/twilio/status')
                ok, info = log._finsetter_send_message(
                    phone, body, channel=log.channel, status_callback=callback)
                if not ok:
                    log.write({**values, 'status': 'failed', 'error_message': info})
                    continue
                reference = info
            else:
                phone = log.partner_id.mobile or log.partner_id.phone
                callback = log._callback_url('/finsetter/twilio/status')
                ok, info = log._finsetter_send_voice(phone, body, status_callback=callback)
                if not ok:
                    log.write({**values, 'status': 'failed', 'error_message': info})
                    continue
                reference = info

            log.write({**values, 'status': 'sent', 'sent_at': fields.Datetime.now(),
                       'provider_reference': reference, 'error_message': False})
            log.message_post(body='Sent via %s.' % dict(FOLLOWUP_CHANNELS).get(log.channel, log.channel))
            if log.lead_id:
                log.lead_id.message_post(body='Follow-up sent via %s: %s' % (log.channel, subject or log.name))
        return True

    def action_mark_replied(self):
        self.write({'status': 'replied', 'replied_at': fields.Datetime.now()})
        for log in self:
            if log.policy_id and log.renewal_cycle_date == log.policy_id.renewal_date:
                log.policy_id.followup_stopped = True
                self.search([
                    ('policy_id', '=', log.policy_id.id),
                    ('renewal_cycle_date', '=', log.renewal_cycle_date),
                    ('status', '=', 'queued'),
                ]).write({'status': 'cancelled'})

    def message_update(self, msg_dict, update_vals):
        result = super().message_update(msg_dict, update_vals)
        self.action_mark_replied()
        return result

    def _apply_provider_status(self, provider_status):
        status_map = {
            'queued': 'sent', 'sending': 'sent', 'sent': 'sent', 'accepted': 'sent',
            'delivered': 'delivered', 'read': 'read', 'completed': 'delivered',
            'failed': 'failed', 'undelivered': 'failed', 'busy': 'failed',
            'no-answer': 'failed', 'canceled': 'failed',
        }
        status = status_map.get(provider_status)
        if status and self.status != 'replied':
            self.write({'status': status})

    @api.model
    def _cron_send_renewal_followups(self):
        today = fields.Date.context_today(self)
        cadence = {30: 'email', 15: 'sms', 7: 'whatsapp', 1: 'voice'}
        policies = self.env['finsetter.policy'].search([
            ('state', 'in', ('active', 'renewal_due')),
            ('followup_stopped', '=', False),
            ('renewal_date', '!=', False),
        ])
        for policy in policies:
            days_left = (policy.renewal_date - today).days
            channel = cadence.get(days_left)
            if not channel:
                continue
            exists = self.search_count([
                ('policy_id', '=', policy.id),
                ('renewal_cycle_date', '=', policy.renewal_date),
                ('reminder_day', '=', days_left),
            ])
            if exists:
                continue
            template = self.env['finsetter.followup.template'].search([
                ('purpose', '=', 'renewal'), ('channel', '=', channel), ('active', '=', True)], limit=1)
            lead = policy.lead_id
            log = self.create({
                'name': 'Renewal reminder: %s days' % days_left,
                'lead_id': lead.id,
                'policy_id': policy.id,
                'partner_id': policy.partner_id.id,
                'template_id': template.id,
                'purpose': 'renewal',
                'channel': channel,
                'reminder_day': days_left,
                'user_id': policy.advisor_id.id or self.env.user.id,
            })
            log.action_send()
        return True

    @api.model
    def _cron_send_scheduled_messages(self):
        due_logs = self.search([
            ('status', '=', 'queued'),
            ('scheduled_at', '<=', fields.Datetime.now()),
        ])
        for log in due_logs:
            policy = log.policy_id
            if policy and (policy.followup_stopped or log.renewal_cycle_date != policy.renewal_date):
                log.status = 'cancelled'
                continue
            log.action_send()
        return True