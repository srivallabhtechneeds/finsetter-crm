# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class FinsetterCustomerPortal(CustomerPortal):
    """Customer self-service portal (spec: "Add customer portal") — lets a
    Finsetter customer log in and see their own policies, appointments,
    documents and claims. Every route here is scoped to the logged-in
    partner via `_document_check_access`, which in turn relies on the
    `ir.rule` "portal" record rules in security/finsetter_crm_security.xml
    (a portal user can never see another customer's records, even by
    guessing an id in the URL).
    """

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        Policy = request.env['finsetter.policy']
        Appointment = request.env['finsetter.appointment']
        Document = request.env['finsetter.document']
        Claim = request.env['finsetter.claim']

        if 'finsetter_policy_count' in counters:
            values['finsetter_policy_count'] = Policy.search_count(self._finsetter_policy_domain(partner)) \
                if Policy.check_access_rights('read', raise_exception=False) else 0
        if 'finsetter_appointment_count' in counters:
            values['finsetter_appointment_count'] = Appointment.search_count(self._finsetter_appointment_domain(partner)) \
                if Appointment.check_access_rights('read', raise_exception=False) else 0
        if 'finsetter_document_count' in counters:
            values['finsetter_document_count'] = Document.search_count(self._finsetter_document_domain(partner)) \
                if Document.check_access_rights('read', raise_exception=False) else 0
        if 'finsetter_claim_count' in counters:
            values['finsetter_claim_count'] = Claim.search_count(self._finsetter_claim_domain(partner)) \
                if Claim.check_access_rights('read', raise_exception=False) else 0
        return values

    # --- domains (the ir.rule record rules enforce the same scoping
    # server-side; these mirror it so counts/lists match) -----------------
    def _finsetter_policy_domain(self, partner):
        return [('partner_id', 'child_of', [partner.commercial_partner_id.id])]

    def _finsetter_appointment_domain(self, partner):
        return [('partner_id', 'child_of', [partner.commercial_partner_id.id])]

    def _finsetter_document_domain(self, partner):
        return [('partner_id', 'child_of', [partner.commercial_partner_id.id])]

    def _finsetter_claim_domain(self, partner):
        return [('partner_id', 'child_of', [partner.commercial_partner_id.id])]

    # --- Policies ----------------------------------------------------------
    @http.route(['/my/policies', '/my/policies/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_policies(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        Policy = request.env['finsetter.policy']
        domain = self._finsetter_policy_domain(partner)
        pager_values = portal_pager(
            url='/my/policies', total=Policy.search_count(domain), page=page, step=self._items_per_page,
        )
        policies = Policy.search(domain, order='renewal_date asc', limit=self._items_per_page, offset=pager_values['offset'])
        values = self._prepare_portal_layout_values()
        values.update({
            'policies': policies.sudo(),
            'page_name': 'finsetter_policy',
            'pager': pager_values,
            'default_url': '/my/policies',
        })
        return request.render('finsetter_crm.portal_my_policies', values)

    @http.route(['/my/policies/<int:policy_id>'], type='http', auth='user', website=True)
    def portal_policy_page(self, policy_id, **kwargs):
        try:
            policy_sudo = self._document_check_access('finsetter.policy', policy_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._get_page_view_values(policy_sudo, None, {'policy': policy_sudo}, False, False, **kwargs)
        return request.render('finsetter_crm.portal_policy_page', values)

    # --- Appointments --------------------------------------------------------
    @http.route(['/my/appointments', '/my/appointments/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_appointments(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        Appointment = request.env['finsetter.appointment']
        domain = self._finsetter_appointment_domain(partner)
        pager_values = portal_pager(
            url='/my/appointments', total=Appointment.search_count(domain), page=page, step=self._items_per_page,
        )
        appointments = Appointment.search(
            domain, order='appointment_datetime desc', limit=self._items_per_page, offset=pager_values['offset'])
        values = self._prepare_portal_layout_values()
        values.update({
            'appointments': appointments.sudo(),
            'page_name': 'finsetter_appointment',
            'pager': pager_values,
            'default_url': '/my/appointments',
        })
        return request.render('finsetter_crm.portal_my_appointments', values)

    # --- Documents -------------------------------------------------------------
    @http.route(['/my/documents', '/my/documents/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_documents(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        Document = request.env['finsetter.document']
        domain = self._finsetter_document_domain(partner)
        pager_values = portal_pager(
            url='/my/documents', total=Document.search_count(domain), page=page, step=self._items_per_page,
        )
        documents = Document.search(
            domain, order='create_date desc', limit=self._items_per_page, offset=pager_values['offset'])
        values = self._prepare_portal_layout_values()
        values.update({
            'documents': documents.sudo(),
            'page_name': 'finsetter_document',
            'pager': pager_values,
            'default_url': '/my/documents',
        })
        return request.render('finsetter_crm.portal_my_documents', values)

    # --- Claims -----------------------------------------------------------------
    @http.route(['/my/claims', '/my/claims/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_claims(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        Claim = request.env['finsetter.claim']
        domain = self._finsetter_claim_domain(partner)
        pager_values = portal_pager(
            url='/my/claims', total=Claim.search_count(domain), page=page, step=self._items_per_page,
        )
        claims = Claim.search(domain, order='claim_date desc', limit=self._items_per_page, offset=pager_values['offset'])
        values = self._prepare_portal_layout_values()
        values.update({
            'claims': claims.sudo(),
            'page_name': 'finsetter_claim',
            'pager': pager_values,
            'default_url': '/my/claims',
        })
        return request.render('finsetter_crm.portal_my_claims', values)
