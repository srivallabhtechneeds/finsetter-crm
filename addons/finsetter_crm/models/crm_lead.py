# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Published on thefinsetter.com/contact.html: "Response target: within 4
# business hours." Used to compute each lead's first-response SLA deadline
# against the company's actual working calendar (see resource_calendar_data.xml).
SLA_RESPONSE_HOURS = 4


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    product_line_id = fields.Many2one(
        'finsetter.policy.product.line', string='Product Line', tracking=True,
        help="Which Finsetter product this lead is interested in "
             "(Health, Life, Motor, Home, Travel, NRI, Will Writing, Financial Planning).")
    product_line_website_url = fields.Char(
        string='Service Page', related='product_line_id.website_url', readonly=True)
    product_line_talking_point = fields.Char(
        string='Talking Point', related='product_line_id.marketing_note', readonly=True)

    call_consent_status = fields.Selection([
        ('unknown', 'Not Captured'),
        ('granted', 'Granted'),
        ('declined', 'Declined'),
        ('withdrawn', 'Withdrawn'),
    ], string='Call Consent', default='unknown', tracking=True)

    channel_whatsapp = fields.Boolean(string='WhatsApp', tracking=True)
    channel_sms = fields.Boolean(string='SMS', tracking=True)
    channel_email = fields.Boolean(string='Email Channel', tracking=True)
    channel_ai_call = fields.Boolean(
        string='AI Call', tracking=True,
        help='Preferred channel only. An AI calling provider must be integrated separately.')

    lead_relationship = fields.Selection([
        ('new', 'New Prospect'),
        ('existing', 'Existing Customer'),
    ], string='Lead Relationship', required=True, default='new', tracking=True)
    lead_status = fields.Selection([
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('interested', 'Interested'),
        ('quote_sent', 'Quote Sent'),
        ('converted', 'Converted'),
        ('lost', 'Lost'),
    ], string='Lead Status', default='new', required=True, tracking=True)
    existing_followup_type = fields.Selection([
        ('renewal', 'Policy Renewal'),
        ('upgrade', 'Product Upgrade'),
        ('general', 'General Follow-up'),
    ], string='Follow-up Reason', default='general')
    existing_followup_date = fields.Date(
        string='Follow-up Date', required=True,
        default=lambda self: fields.Date.context_today(self))

    preferred_language = fields.Selection([
        ('en', 'English'),
        ('te', 'Telugu'),
        ('both', 'Bilingual (Telugu & English)'),
    ], default='both')

    is_nri = fields.Boolean(string='NRI Lead', tracking=True)

    # --- Customer 360 / lead-capture fields (spec section 1) ---
    finsetter_age = fields.Integer(string='Age')
    finsetter_annual_income = fields.Monetary(
        string='Annual Income', currency_field='company_currency')
    finsetter_occupation = fields.Char(string='Occupation')
    health_status = fields.Selection([
        ('not_assessed', 'Not Assessed'),
        ('healthy', 'Healthy'),
        ('unhealthy', 'Unhealthy'),
    ], string='Health Condition', required=True, default='not_assessed', tracking=True)
    health_problem = fields.Text(string='Health Problem')
    finsetter_financial_goals = fields.Text(
        string='Financial Goals', help="E.g. child's education, retirement, wealth protection.")
    finsetter_requirements = fields.Text(
        string='Requirements / Notes', help="Specific coverage/investment requirements captured at intake.")

    campaign_source_id = fields.Many2one(
        'finsetter.campaign', string='Source Campaign', tracking=True,
        help="The marketing campaign that generated or targeted this lead.")

    product_match_ids = fields.One2many('finsetter.lead.product.match', 'lead_id', string='Product Matches')
    product_match_count = fields.Integer(compute='_compute_finsetter_counts')
    appointment_ids = fields.One2many('finsetter.appointment', 'lead_id', string='Appointments')
    appointment_count = fields.Integer(compute='_compute_finsetter_counts')
    document_ids = fields.One2many('finsetter.document', 'lead_id', string='Documents')
    document_count = fields.Integer(compute='_compute_finsetter_counts')

    consultation_type = fields.Selection([
        ('virtual', 'Virtual'),
        ('in_person', 'In Person'),
        ('phone', 'Phone'),
    ], string='Consultation Mode', default='virtual',
        help="Matches the free 30-45 minute initial consultation offered on thefinsetter.com.")

    sla_deadline = fields.Datetime(
        string='First Response Due',
        help="4 business hours from creation (Finsetter's published response "
             "target), computed against the company's working calendar.")
    sla_status = fields.Selection([
        ('pending', 'Pending'),
        ('met', 'Met'),
        ('breached', 'Breached'),
    ], string='Response SLA', default='pending', tracking=True)

    call_log_ids = fields.One2many('finsetter.call.log', 'lead_id', string='Call Logs')
    call_log_count = fields.Integer(compute='_compute_finsetter_counts')
    consent_ids = fields.One2many('finsetter.consent', 'lead_id', string='Consent Records')
    consent_count = fields.Integer(compute='_compute_finsetter_counts')
    policy_ids = fields.One2many('finsetter.policy', 'lead_id', string='Policies')
    policy_count = fields.Integer(compute='_compute_finsetter_counts')

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        for lead in leads:
            if not lead.sla_deadline:
                calendar = lead.company_id.resource_calendar_id or self.env.company.resource_calendar_id
                deadline = fields.Datetime.now()
                if calendar:
                    deadline = calendar.plan_hours(SLA_RESPONSE_HOURS, fields.Datetime.now(), compute_leaves=True)
                lead.sla_deadline = deadline
        return leads

    def _mark_sla_met(self):
        """Called when the first customer-facing contact (a logged call) is
        recorded against a lead still awaiting its first response."""
        pending = self.filtered(lambda l: l.sla_status == 'pending')
        if pending:
            pending.write({'sla_status': 'met'})

    def _compute_finsetter_counts(self):
        for lead in self:
            lead.call_log_count = len(lead.call_log_ids)
            lead.consent_count = len(lead.consent_ids)
            lead.policy_count = len(lead.policy_ids)
            lead.product_match_count = len(lead.product_match_ids)
            lead.appointment_count = len(lead.appointment_ids)
            lead.document_count = len(lead.document_ids)

    def action_view_calls(self):
        self.ensure_one()
        return {
            'name': 'Call Logs',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.call.log',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_view_consent(self):
        self.ensure_one()
        return {
            'name': 'Consent Records',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.consent',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_view_policies(self):
        self.ensure_one()
        return {
            'name': 'Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.policy',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_log_call(self):
        self.ensure_one()
        return {
            'name': 'Log Call',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.call.log',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_product_line_id': self.product_line_id.id,
            },
        }

    def action_view_product_matches(self):
        self.ensure_one()
        return {
            'name': 'Product Matches',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.lead.product.match',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'name': 'Appointments',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.appointment',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': 'Documents',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.document',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_open_calculators(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'finsetter_crm_calculators',
            'name': 'Financial Calculators',
            'target': 'new',
            'context': {'default_lead_id': self.id},
        }

    def action_find_matching_products(self):
        """'Find Matching Products' button on the lead form — runs the
        recommendation engine (finsetter.lead.product.match) for this lead
        and opens whatever it found."""
        self.ensure_one()
        self.env['finsetter.lead.product.match'].action_generate_matches(self.ids)
        return self.action_view_product_matches()

    def action_schedule_existing_followup(self):
        self.ensure_one()
        reason = dict(self._fields['existing_followup_type'].selection).get(
            self.existing_followup_type, 'General Follow-up')
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            date_deadline=self.existing_followup_date,
            summary='%s: %s' % (reason, self.name),
            note='Follow up with this existing customer about %s.' % reason.lower(),
            user_id=self.user_id.id or self.env.uid,
        )
        return True

    @api.model
    def _cron_assign_leads_round_robin(self):
        """Scheduled action: assign any new/unassigned lead to the next
        member of the team matching its product line, in round-robin order.
        Falls back to the team's default assignment if no product-line team
        is configured. Called by ir_cron_data.xml.
        """
        unassigned = self.search([('user_id', '=', False), ('active', '=', True), ('type', '=', 'lead')])
        for lead in unassigned:
            team = False
            if lead.product_line_id:
                team = self.env['crm.team'].search(
                    [('product_line_id', '=', lead.product_line_id.id)], limit=1)
            if not team:
                team = lead.team_id
            if not team or not team.member_ids:
                continue

            members = team.member_ids
            last_partner = team.last_assigned_partner_id
            if last_partner and last_partner in members:
                idx = list(members.ids).index(last_partner.id)
                next_user = members[(idx + 1) % len(members)]
            else:
                next_user = members[0]

            lead.write({'user_id': next_user.id, 'team_id': team.id})
            team.write({'last_assigned_partner_id': next_user.id})
            lead.message_post(
                body="Auto-assigned to %s (round-robin, %s team)." % (next_user.name, team.name))
            _logger.info("Finsetter CRM: lead %s auto-assigned to %s", lead.id, next_user.name)

    @api.model
    def _cron_check_response_sla(self):
        """Scheduled action: flag leads that blew past Finsetter's published
        4-business-hour first-response promise and raise a high-priority
        activity for the owner. Called by ir_cron_data.xml.
        """
        overdue = self.search([
            ('sla_status', '=', 'pending'),
            ('sla_deadline', '<=', fields.Datetime.now()),
            ('active', '=', True),
        ])
        for lead in overdue:
            lead.write({'sla_status': 'breached'})
            lead.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='OVERDUE: 4-hour response SLA breached',
                note="This lead has gone unanswered past Finsetter's published "
                     "4-business-hour response target. Contact the customer now.",
                user_id=lead.user_id.id or self.env.uid,
            )
            lead.message_post(body="⚠️ 4-hour first-response SLA breached — no call logged in time.")
