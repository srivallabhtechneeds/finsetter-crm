# -*- coding: utf-8 -*-
import ast
from html import escape

from odoo import api, fields, models

WILDIX_COLLABORATION_URL = 'https://neton-pbx.wildixin.com/collaboration/'


class FinsetterCampaign(models.Model):
    """Spec section 4: Campaign Management — target a segment of leads,
    push a bulk WhatsApp/SMS/email campaign or prepare a Wildix call list, and track
    responses/conversions/ROI back against the linked opportunities.
    """
    _name = 'finsetter.campaign'
    _description = 'Finsetter Marketing Campaign'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(required=True, tracking=True)
    product_line_id = fields.Many2one('finsetter.policy.product.line', string='Product Line', tracking=True)
    channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('call', 'Call via Wildix'),
    ], default='whatsapp', required=True, tracking=True)

    message_template = fields.Text(
        string='Message', help="Use {{name}} and {{matched_products}}. Matching approved products are appended if omitted.")
    email_subject = fields.Char(string='Email Subject')
    email_template_id = fields.Many2one('mail.template', string='Email Template')

    target_domain = fields.Char(
        string='Target Filter (domain)', default='[]',
        help='Odoo domain evaluated against crm.lead to build the recipient list, '
             'e.g. [["product_line_id","=",1],["is_nri","=",true]]')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True)
    scheduled_date = fields.Datetime(string='Scheduled Send Time')

    recipient_ids = fields.One2many('finsetter.campaign.recipient', 'campaign_id', string='Recipients')
    recipient_count = fields.Integer(compute='_compute_stats')
    sent_count = fields.Integer(compute='_compute_stats')
    delivered_count = fields.Integer(compute='_compute_stats')
    responded_count = fields.Integer(compute='_compute_stats')
    converted_count = fields.Integer(compute='_compute_stats')
    response_rate = fields.Float(compute='_compute_stats', string='Response Rate (%)')
    conversion_rate = fields.Float(compute='_compute_stats', string='Conversion Rate (%)')

    cost_amount = fields.Monetary(string='Campaign Cost', currency_field='currency_id')
    revenue_amount = fields.Monetary(
        string='Revenue Won (Linked Leads)', compute='_compute_stats', currency_field='currency_id')
    roi = fields.Float(string='ROI (%)', compute='_compute_stats',
                        help="(Revenue - Cost) / Cost * 100, from opportunities won among this campaign's leads.")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('recipient_ids.state', 'recipient_ids.lead_id.expected_revenue',
                 'recipient_ids.lead_id.stage_id.is_won', 'cost_amount')
    def _compute_stats(self):
        for camp in self:
            recs = camp.recipient_ids
            camp.recipient_count = len(recs)
            camp.sent_count = len(recs.filtered(lambda r: r.state in ('sent', 'delivered', 'responded', 'converted')))
            camp.delivered_count = len(recs.filtered(lambda r: r.state in ('delivered', 'responded', 'converted')))
            camp.responded_count = len(recs.filtered(lambda r: r.state in ('responded', 'converted')))
            camp.converted_count = len(recs.filtered(lambda r: r.state == 'converted'))
            won_leads = recs.mapped('lead_id').filtered(lambda l: l.stage_id.is_won)
            revenue = sum(won_leads.mapped('expected_revenue'))
            camp.revenue_amount = revenue
            camp.roi = ((revenue - camp.cost_amount) / camp.cost_amount * 100) if camp.cost_amount else 0.0
            camp.response_rate = (camp.responded_count / camp.sent_count * 100) if camp.sent_count else 0.0
            camp.conversion_rate = (camp.converted_count / camp.sent_count * 100) if camp.sent_count else 0.0

    def action_build_recipients(self):
        """Evaluate `target_domain` against crm.lead and (re)build the
        recipient list, skipping leads already on it."""
        for camp in self:
            try:
                domain = ast.literal_eval(camp.target_domain or '[]')
            except (ValueError, SyntaxError):
                domain = []
            leads = self.env['crm.lead'].search(domain)
            existing = camp.recipient_ids.mapped('lead_id')
            to_add = leads - existing
            self.env['finsetter.campaign.recipient'].create([
                {'campaign_id': camp.id, 'lead_id': lead.id, 'partner_id': lead.partner_id.id}
                for lead in to_add
            ])
        return True

    def action_send(self):
        """Send messages or prepare a consent-checked Wildix call worklist."""
        wildix_action = False
        for camp in self:
            camp.state = 'sending'
            for recipient in camp.recipient_ids.filtered(lambda r: r.state == 'draft'):
                recipient._send(camp)
            camp.state = 'sent'
            if camp.channel == 'call':
                camp.message_post(body="Wildix call worklist prepared for %d recipient(s)." % camp.recipient_count)
                wildix_action = camp.action_open_wildix()
            else:
                camp.message_post(body="Campaign sent to %d recipient(s)." % camp.recipient_count)
        return wildix_action or True

    def action_open_wildix(self):
        return {
            'type': 'ir.actions.act_url',
            'url': WILDIX_COLLABORATION_URL,
            'target': 'new',
        }

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FinsetterCampaignRecipient(models.Model):
    _name = 'finsetter.campaign.recipient'
    _description = 'Campaign Recipient'
    _inherit = ['finsetter.messaging.mixin']
    _rec_name = 'partner_id'

    campaign_id = fields.Many2one('finsetter.campaign', required=True, ondelete='cascade')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    partner_id = fields.Many2one('res.partner', string='Contact')
    phone = fields.Char(compute='_compute_phone', store=True)

    state = fields.Selection([
        ('draft', 'Not Sent'),
        ('call_pending', 'Call Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('responded', 'Responded'),
        ('converted', 'Converted'),
        ('failed', 'Failed'),
    ], default='draft')
    send_error = fields.Char()
    sent_date = fields.Datetime()
    provider_reference = fields.Char(copy=False)

    @api.depends('partner_id', 'lead_id')
    def _compute_phone(self):
        for rec in self:
            rec.phone = (rec.lead_id.mobile or rec.lead_id.phone
                         or rec.partner_id.mobile or rec.partner_id.phone or '')

    def _send(self, campaign):
        self.ensure_one()
        recipient_name = self.partner_id.name or self.lead_id.contact_name or self.lead_id.name or 'there'
        product_details = self._matched_product_details(campaign)
        if not product_details and (campaign.product_line_id or '{{matched_products}}' in (campaign.message_template or '')):
            self.write({'state': 'failed', 'send_error': 'No active matched products are available for this lead.'})
            return True
        body = (campaign.message_template or '').replace('{{name}}', recipient_name)
        if '{{matched_products}}' in body:
            body = body.replace('{{matched_products}}', product_details)
        elif product_details:
            body = '%s\n\nRecommended options:\n%s' % (body, product_details) if body else product_details
        if campaign.channel in ('whatsapp', 'sms'):
            ok, info = self._finsetter_send_message(self.phone, body, channel=campaign.channel)
            if ok:
                self.write({'state': 'sent', 'sent_date': fields.Datetime.now(),
                            'send_error': False, 'provider_reference': info})
            else:
                self.write({'state': 'failed', 'send_error': info})
        elif campaign.channel == 'email':
            if not self.partner_id.email:
                self.write({'state': 'failed', 'send_error': 'No email address on file.'})
            elif campaign.email_template_id:
                mail_id = campaign.email_template_id.send_mail(
                    self.lead_id.id or self.partner_id.id, force_send=False)
                mail = self.env['mail.mail'].sudo().browse(mail_id)
                if body:
                    mail.body_html = '%s<hr/><div>%s</div>' % (
                        mail.body_html or '', escape(body).replace('\n', '<br/>'))
                mail.send()
                if mail.state == 'exception':
                    self.write({'state': 'failed', 'send_error': mail.failure_reason or 'Email delivery failed.'})
                else:
                    self.write({'state': 'sent', 'sent_date': fields.Datetime.now(),
                                'send_error': False, 'provider_reference': str(mail.id)})
            elif body:
                mail = self.env['mail.mail'].sudo().create({
                    'subject': campaign.email_subject or campaign.name,
                    'body_html': '<div>%s</div>' % escape(body).replace('\n', '<br/>'),
                    'email_to': self.partner_id.email,
                    'email_from': self.env.user.email_formatted or self.env.company.email or '',
                    'model': self._name,
                    'res_id': self.id,
                    'auto_delete': False,
                })
                mail.send()
                if mail.state == 'exception':
                    self.write({'state': 'failed', 'send_error': mail.failure_reason or 'Email delivery failed.'})
                else:
                    self.write({'state': 'sent', 'sent_date': fields.Datetime.now(),
                                'send_error': False, 'provider_reference': str(mail.id)})
            else:
                self.write({'state': 'failed', 'send_error': 'Add a message or select an email template.'})
        elif campaign.channel == 'call':
            if not self.lead_id or self.lead_id.call_consent_status != 'granted':
                self.write({'state': 'failed', 'send_error': 'Outbound call skipped: lead call consent is not granted.'})
            elif not self.phone:
                self.write({'state': 'failed', 'send_error': 'Outbound call skipped: no phone number is on file.'})
            else:
                self.write({
                    'state': 'call_pending',
                    'send_error': False,
                    'provider_reference': 'wildix-manual-call',
                })
        else:
            self.write({'state': 'failed', 'send_error': 'Unsupported campaign channel.'})
        return True

    def _matched_product_details(self, campaign):
        self.ensure_one()
        if not self.lead_id:
            return ''

        Match = self.env['finsetter.lead.product.match']
        domain = [
            ('lead_id', '=', self.lead_id.id),
            ('status', 'in', ('recommended', 'interested', 'pending')),
            ('product_id.status', '=', 'active'),
        ]
        if campaign.product_line_id:
            domain.append(('product_line_id', '=', campaign.product_line_id.id))
        matches = Match.search(domain, order='score desc, id desc', limit=3)
        if not matches:
            Match.action_generate_matches([self.lead_id.id])
            matches = Match.search(domain, order='score desc, id desc', limit=3)

        lines = []
        for match in matches:
            product = match.product_id
            details = [product.name]
            if product.provider:
                details.append('Provider: %s' % product.provider)
            if product.eligibility_criteria:
                details.append('Eligibility: %s' % product.eligibility_criteria)
            if product.min_amount or product.max_amount:
                amount_type = dict(product._fields['amount_type'].selection).get(product.amount_type, 'Amount')
                currency = product.currency_id.symbol or product.currency_id.name
                low = '%s %s' % (currency, product.min_amount) if product.min_amount else 'No minimum'
                high = '%s %s' % (currency, product.max_amount) if product.max_amount else 'No maximum'
                details.append('%s range: %s to %s' % (amount_type, low, high))
            if product.website_url:
                details.append('Details: %s' % product.website_url)
            lines.append(' - '.join(details))
        return '\n'.join(lines)

    def action_open_wildix(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': WILDIX_COLLABORATION_URL,
            'target': 'new',
        }

    def action_mark_responded(self):
        self.write({'state': 'responded'})

    def action_mark_converted(self):
        self.write({'state': 'converted'})
