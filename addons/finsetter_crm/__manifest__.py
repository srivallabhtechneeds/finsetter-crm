# -*- coding: utf-8 -*-
{
    'name': 'Finsetter CRM',
    'version': '17.0.2.0.0',
    'category': 'Sales/CRM',
    'summary': 'Full financial-services CRM for Finsetter — leads, products, campaigns, '
               'policies, claims, appointments, calculators, compliance & a customer portal.',
    'description': """
Finsetter CRM
=============
A rich, opinionated CRM layer built on top of Odoo's Sales/CRM app for
**Finsetter Financial Services Pvt. Ltd.** (SEBI Reg. E667968 · IRDAI
Lic. 5854206) — "Your Money. Simplified."

Highlights
----------
* **Lead capture & 360° customer profile** — leads tagged by product line
  across 13 categories (Health, Life/Term, Motor, Home, Travel, NRI, Will
  Writing, Financial Planning, Investment/Mutual Funds, Tax-Saving,
  Retirement/Pension, Estate Planning, Family Financial Planning), with
  age/income/occupation/goals captured at intake and auto-assigned
  round-robin to the right advisor/team.
* **Financial product catalog & lead-product matching** — a real product
  catalog (provider, eligibility, amount range, tenure, commission) with a
  transparent, explainable recommendation engine that scores each lead
  against every product in its category.
* **Campaign management** — target a lead segment, and send a real bulk
  WhatsApp/SMS campaign via Twilio (or email via a mail template), with
  response/conversion/ROI tracking per campaign.
* **Policy, renewal & claims tracking** — every sold policy (insurer, sum
  insured, premium, renewal date) lives on the customer record, with an
  automated 30/15/7/1-day renewal reminder pipeline and full claims
  management (submission through settlement).
* **Appointments with real Google Calendar sync** — book the free
  consultation the website offers; every appointment creates a linked
  Odoo calendar event that syncs to the advisor's Google Calendar once
  connected.
* **7 financial calculators** — Term Insurance, Health Insurance,
  SIP/Investment, Tax Saving, Retirement Planning, Loan/EMI and Compound
  Interest, right on the lead.
* **Documents & compliance** — secure KYC document storage with a
  verification workflow, plus the existing consent register, both fully
  chatter/audit-logged.
* **Customer portal** — customers log in and see their own policies,
  appointments, documents and claims.
* **Role-based access** — Admin, Manager, Financial Advisor, Sales
  Executive and Customer (portal), each scoped to what they should see.
* **Executive dashboard** — a modern, single-screen view of pipeline
  health, renewals due, consent status, SLA and team performance, styled
  after thefinsetter.com's brand (12+ years, 98% claim settlement,
  5,000+ families served).
""",
    'author': 'Finsetter Financial Services',
    'website': 'https://www.thefinsetter.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_automation',
        'mail',
        'crm',
        'contacts',
        'sales_team',
        'resource',
        'calendar',
        'portal',
    ],
    'data': [
        'security/finsetter_crm_security.xml',
        'security/ir.model.access.csv',
        'data/resource_calendar_data.xml',
        'data/product_line_data.xml',
        'data/finsetter_testimonial_data.xml',
        'data/crm_stage_data.xml',
        'data/utm_source_data.xml',
        'data/crm_tag_data.xml',
        'data/crm_team_data.xml',
        'data/mail_activity_type_data.xml',
        'data/mail_template_data.xml',
        'data/finsetter_followup_template_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_automation_data.xml',
        'data/res_company_data.xml',
        'views/crm_lead_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/finsetter_policy_views.xml',
        'views/finsetter_call_log_views.xml',
        'views/finsetter_consent_views.xml',
        'views/finsetter_testimonial_views.xml',
        'views/finsetter_product_line_views.xml',
        'views/finsetter_financial_product_views.xml',
        'views/finsetter_lead_product_match_views.xml',
        'views/finsetter_campaign_views.xml',
        'views/finsetter_claim_views.xml',
        'views/finsetter_appointment_views.xml',
        'views/finsetter_document_views.xml',
        'views/finsetter_followup_views.xml',
        'views/res_config_settings_views.xml',
        'views/finsetter_dashboard_views.xml',
        'views/menu_views.xml',
        'views/web_login_templates.xml',
        'views/portal_templates.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
        'demo/finsetter_financial_product_demo.xml',
        'demo/finsetter_v2_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'finsetter_crm/static/src/js/dashboard.js',
            'finsetter_crm/static/src/xml/dashboard.xml',
            'finsetter_crm/static/src/scss/dashboard.scss',
            'finsetter_crm/static/src/js/calculators.js',
            'finsetter_crm/static/src/xml/calculators.xml',
            'finsetter_crm/static/src/scss/calculators.scss',
            'finsetter_crm/static/src/scss/views.scss',
        ],
        'web.assets_frontend': [
            'finsetter_crm/static/src/scss/login.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
