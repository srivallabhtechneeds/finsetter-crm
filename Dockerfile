# ---------------------------------------------------------------------------
# Finsetter CRM — Odoo image
# Builds on the official Odoo 17 image and bakes in the finsetter_crm addon
# plus its Python dependencies.
# ---------------------------------------------------------------------------
ARG ODOO_VERSION=17.0
FROM odoo:${ODOO_VERSION}

LABEL maintainer="Finsetter Financial Services" \
      description="Finsetter CRM - custom Odoo CRM for lead, policy, consent & renewal management"

USER root

# Extra Python deps used by the finsetter_crm module (none beyond Odoo's
# bundled stack today, kept here so future additions have a single home).
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true

# Bring in the custom addon
COPY ./addons /mnt/extra-addons

# Bring in server config (overridable via volume mount too)
COPY ./config/odoo.conf /etc/odoo/odoo.conf

RUN chown -R odoo:odoo /mnt/extra-addons /etc/odoo && \
    mkdir -p /var/log/odoo && chown -R odoo:odoo /var/log/odoo

USER odoo

EXPOSE 8069 8072
