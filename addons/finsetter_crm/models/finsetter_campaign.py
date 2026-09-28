# -*- coding: utf-8 -*-
import ast

from odoo import api, fields, models


class FinsetterCampaign(models.Model):
    """Spec section 4: Campaign Management — target a segment of leads,
    push a bulk WhatsApp/SMS/email/call-blitz campaign, and track
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
        ('call', 'Call Blitz'),
    ], default='whatsapp', required=True, tracking=True)

    message_template = fields.Text(
        string='Message', help="Use {{name}} — replaced with the recipient's name at send time.")
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
        """Send the campaign now. WhatsApp/SMS go out through Twilio (see
        finsetter_messaging.py); email uses the standard mail template."""
        for camp in self:
            camp.state = 'sending'
            for recipient in camp.recipient_ids.filtered(lambda r: r.state == 'draft'):
                recipient._send(camp)
            camp.state = 'sent'
            camp.message_post(body="Campaign sent to %d recipient(s)." % camp.recipient_count)
        return True

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
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('responded', 'Responded'),
        ('converted', 'Converted'),
        ('failed', 'Failed'),
    ], default='draft')
    send_error = fields.Char()
    sent_date = fields.Datetime()

    @api.depends('partner_id', 'lead_id')
    def _compute_phone(self):
        for rec in self:
            rec.phone = (rec.lead_id.mobile or rec.lead_id.phone
                         or rec.partner_id.mobile or rec.partner_id.phone or '')

    def _send(self, campaign):
        self.ensure_one()
        recipient_name = self.partner_id.name or self.lead_id.contact_name or self.lead_id.name or 'there'
        body = (campaign.message_template or '').replace('{{name}}', recipient_name)
        if campaign.channel in ('whatsapp', 'sms'):
            ok, info = self._finsetter_send_message(self.phone, body, channel=campaign.channel)
            if ok:
                self.write({'state': 'sent', 'sent_date': fields.Datetime.now(), 'send_error': False})
            else:
                self.write({'state': 'failed', 'send_error': info})
        elif campaign.channel == 'email' and self.partner_id.email:
            if campaign.email_template_id:
                campaign.email_template_id.send_mail(
                    self.lead_id.id or self.partner_id.id, force_send=True)
            self.write({'state': 'sent', 'sent_date': fields.Datetime.now()})
        else:
            # Call Blitz: no automatic send — logged so advisors have a
            # worklist; they log the outcome via finsetter.call.log.
            self.write({'state': 'sent', 'sent_date': fields.Datetime.now()})
        return True

    def action_mark_responded(self):
        self.write({'state': 'responded'})

    def action_mark_converted(self):
        self.write({'state': 'converted'})
