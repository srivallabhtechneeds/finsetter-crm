# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    finsetter_policy_ids = fields.One2many('finsetter.policy', 'partner_id', string='Policies')
    finsetter_policy_count = fields.Integer(compute='_compute_finsetter_counts')
    finsetter_call_log_ids = fields.One2many('finsetter.call.log', 'partner_id', string='Call Logs')
    finsetter_call_count = fields.Integer(compute='_compute_finsetter_counts')
    finsetter_consent_ids = fields.One2many('finsetter.consent', 'partner_id', string='Consent Records')
    finsetter_consent_count = fields.Integer(compute='_compute_finsetter_counts')
    finsetter_claim_ids = fields.One2many('finsetter.claim', 'partner_id', string='Claims')
    finsetter_claim_count = fields.Integer(compute='_compute_finsetter_counts')
    finsetter_appointment_ids = fields.One2many('finsetter.appointment', 'partner_id', string='Appointments')
    finsetter_appointment_count = fields.Integer(compute='_compute_finsetter_counts')
    finsetter_document_ids = fields.One2many('finsetter.document', 'partner_id', string='Documents')
    finsetter_document_count = fields.Integer(compute='_compute_finsetter_counts')

    # Customer 360 (spec section 1) — mirrors the same fields captured on
    # the originating lead so the profile is complete even for customers
    # created directly (e.g. by an advisor, or via the portal).
    finsetter_age = fields.Integer(string='Age')
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    finsetter_annual_income = fields.Monetary(string='Annual Income', currency_field='currency_id')
    finsetter_occupation = fields.Char(string='Occupation')
    finsetter_financial_goals = fields.Text(string='Financial Goals')

    call_consent_status = fields.Selection([
        ('unknown', 'Not Captured'),
        ('granted', 'Granted'),
        ('declined', 'Declined'),
        ('withdrawn', 'Withdrawn'),
    ], string='Call Consent Status', compute='_compute_call_consent_status', store=True)

    def _compute_finsetter_counts(self):
        for partner in self:
            partner.finsetter_policy_count = len(partner.finsetter_policy_ids)
            partner.finsetter_call_count = len(partner.finsetter_call_log_ids)
            partner.finsetter_consent_count = len(partner.finsetter_consent_ids)
            partner.finsetter_claim_count = len(partner.finsetter_claim_ids)
            partner.finsetter_appointment_count = len(partner.finsetter_appointment_ids)
            partner.finsetter_document_count = len(partner.finsetter_document_ids)

    def _compute_call_consent_status(self):
        for partner in self:
            calls = partner.finsetter_consent_ids.filtered(lambda c: c.consent_type == 'call')
            latest = calls.sorted('date_obtained', reverse=True)[:1]
            partner.call_consent_status = latest.status if latest else 'unknown'

    def action_view_finsetter_policies(self):
        self.ensure_one()
        return {
            'name': 'Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.policy',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_finsetter_calls(self):
        self.ensure_one()
        return {
            'name': 'Call Logs',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.call.log',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_finsetter_consent(self):
        self.ensure_one()
        return {
            'name': 'Consent Records',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.consent',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_finsetter_claims(self):
        self.ensure_one()
        return {
            'name': 'Claims',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.claim',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
        }

    def action_view_finsetter_appointments(self):
        self.ensure_one()
        return {
            'name': 'Appointments',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.appointment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_finsetter_documents(self):
        self.ensure_one()
        return {
            'name': 'Documents',
            'type': 'ir.actions.act_window',
            'res_model': 'finsetter.document',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }


class ResCompany(models.Model):
    _inherit = 'res.company'

    finsetter_tagline = fields.Char(string='Brand Tagline')
    finsetter_positioning = fields.Text(string='Brand Positioning')
    finsetter_mission = fields.Text(string='Mission')
    finsetter_vision = fields.Text(string='Vision')
    finsetter_founder = fields.Char(string='Founder')
    finsetter_founder_title = fields.Char(string='Founder Title')
    finsetter_founded_year = fields.Integer(string='Founded Year')
    finsetter_sebi_registration = fields.Char(string='SEBI Registration')
    finsetter_irdai_license = fields.Char(string='IRDAI Licence')
    finsetter_years_experience = fields.Char(string='Experience')
    finsetter_families_served = fields.Char(string='Families Served')
    finsetter_claim_settlement_rate = fields.Char(string='Claim Settlement Rate')
    finsetter_google_rating = fields.Char(string='Google Rating')
    finsetter_google_reviews = fields.Char(string='Google Reviews')
    finsetter_languages = fields.Char(string='Languages')
    finsetter_service_areas = fields.Text(string='Service Areas')
    finsetter_consultation_offer = fields.Text(string='Consultation Offer')
    finsetter_trust_principles = fields.Text(string='Trust Principles')
    finsetter_legal_links = fields.Text(string='Legal Links')
    finsetter_social_links = fields.Text(string='Social Links')
    finsetter_source_url = fields.Char(string='Website Source')
