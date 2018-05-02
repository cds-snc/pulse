from flask import render_template, Response
from pulse import models
from pulse.data import FIELD_MAPPING
import os
import ujson

def register(app):

    @app.route("/data/")
    def data():
        return render_template("data.html")

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/about/")
    def about():
        return render_template("about.html")

    ##
    # Data endpoints.
    # High-level %'s, used to power the donuts.
    @app.route("/data/reports/<report_name>.json")
    def report(report_name):
        response = Response(ujson.dumps(models.Report.latest().get(report_name, {})))
        response.headers['Content-Type'] = 'application/json'
        return response

    # Detailed data per-parent-domain.
    @app.route("/data/domains/<report_name>.<ext>")
    def domain_report(report_name, ext):
        domains = models.Domain.eligible_parents(report_name)
        domains = sorted(domains, key=lambda k: k['domain'])

        if ext == "json":
          response = Response(ujson.dumps({'data': domains}))
          response.headers['Content-Type'] = 'application/json'
        elif ext == "csv":
          response = Response(models.Domain.to_csv(domains, report_name))
          response.headers['Content-Type'] = 'text/csv'
        return response

    # Detailed data per-host for a given report.
    @app.route("/data/hosts/<report_name>.<ext>")
    def hostname_report(report_name, ext):
        domains = models.Domain.eligible(report_name)

        # sort by base domain, but subdomain within them
        domains = sorted(domains, key=lambda k: k['domain'])
        domains = sorted(domains, key=lambda k: k['base_domain'])

        if ext == "json":
          response = Response(ujson.dumps({'data': domains}))
          response.headers['Content-Type'] = 'application/json'
        elif ext == "csv":
          response = Response(models.Domain.to_csv(domains, report_name))
          response.headers['Content-Type'] = 'text/csv'
        return response

    # Detailed data for all subdomains of a given parent domain, for a given report.
    @app.route("/data/hosts/<domain>/<report_name>.<ext>")
    def hostname_report_for_domain(domain, report_name, ext):
        domains = models.Domain.eligible_for_domain(domain, report_name)

        # sort by hostname, but put the parent at the top if it exist
        domains = sorted(domains, key=lambda k: k['domain'])
        domains = sorted(domains, key=lambda k: k['is_parent'], reverse=True)

        if ext == "json":
            response = Response(ujson.dumps({'data': domains}))
            response.headers['Content-Type'] = 'application/json'
        elif ext == "csv":
            response = Response(models.Domain.to_csv(domains, report_name))
            response.headers['Content-Type'] = 'text/csv'
        return response

    @app.route("/data/agencies/<report_name>.json")
    def agency_report(report_name):
        domains = models.Agency.eligible(report_name)
        response = Response(ujson.dumps({'data': domains}))
        response.headers['Content-Type'] = 'application/json'
        return response

    @app.route("/https/domains/")
    def https_domains():
        return render_template("https/domains.html")

    @app.route("/https/agencies/")
    def https_agencies():
        return render_template("https/agencies.html")

    @app.route("/https/guidance/")
    def https_guide():
        return render_template("https/guide.html")

    @app.route("/analytics/domains/")
    def analytics_domains():
        return render_template("analytics/domains.html")

    @app.route("/analytics/agencies/")
    def analytics_agencies():
        return render_template("analytics/agencies.html")

    @app.route("/analytics/guidance/")
    def analytics_guide():
        return render_template("analytics/guide.html")

    hide_cust_sat = (os.getenv("HIDE_CUSTOMER_SATISFACTION", "false").lower() == "true")

    if not hide_cust_sat:
        @app.route("/customer-satisfaction/domains/")
        def customersatisfaction_domains():
            return render_template("customer-satisfaction/domains.html")

        @app.route("/customer-satisfaction/agencies/")
        def customersatisfaction_agencies():
            return render_template("customer-satisfaction/agencies.html")

        @app.route("/customer-satisfaction/guidance/")
        def customersatisfaction_guide():
            return render_template("customer-satisfaction/guide.html")

    @app.route("/agency/<slug>")
    def agency(slug=None):
        agency = models.Agency.find(slug)
        if agency is None:
            pass # TODO: 404

        return render_template("agency.html", agency=agency)

    @app.route("/domain/<hostname>")
    def domain(hostname=None):
        domain = models.Domain.find(hostname)
        if domain is None:
            pass # TODO: 404

        return render_template("domain.html", domain=domain)

    # Sanity-check RSS feed, shows the latest report.
    @app.route("/data/reports/feed/")
    def report_feed():
        return render_template("feed.xml")

    hide_accessibility = (os.getenv("HIDE_ACCESSIBILITY", "false").lower() == "true")

    if not hide_accessibility:
        @app.route("/a11y/domain/<hostname>")
        def a11ydomain(hostname=None):
          return render_template("a11y.html", domain=hostname)

        @app.route("/a11y/domains/")
        def accessibility_domains():
          return render_template("accessibility/domains.html")

        @app.route("/a11y/agencies/")
        def accessibility_agencies():
          return render_template("accessibility/agencies.html")

        @app.route("/a11y/guidance/")
        def accessibility_guide():
          return render_template("accessibility/guide.html")

    @app.errorhandler(404)
    def page_not_found(e):
      return render_template('404.html'), 404
