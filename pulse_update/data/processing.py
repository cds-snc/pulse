###
#
# Given, in the data/output/parents/results directory:
#
# * pshtt.csv - domain-scan, based on pshtt
# * sslyze.csv - domain-scan, based on sslyze.
#
# And, in the data/output/subdomains directory:
#
# * gather/results/gathered.csv - all gathered .gov hostnames
# * scan/results/pshtt.csv - pshtt scan for all hostnames
# * scan/results/sslyze.csv - sslyze scan for live/TLS hostnames
#
###

import errno
import logging
import csv
import json
import yaml
import os
import glob
import slugify
import datetime
import subprocess
from shutil import copyfile

# Import all the constants from data/env.py.
from data.env import *
from data import logger
from data import models

from statistics import mean


LOGGER = logger.get_logger(__name__)

this_dir = os.path.dirname(__file__)

# domains.csv is downloaded and live-cached during the scan
PARENT_RESULTS = os.path.join(PARENTS_DATA, "./results")
PARENT_CACHE = os.path.join(PARENTS_DATA, "./cache")
PARENT_DOMAINS_CSV = os.path.join(PARENT_CACHE, "domains.csv")

# Base directory for scanned subdomain data.
SUBDOMAIN_DATA_AGENCIES = os.path.join(SUBDOMAIN_DATA, "./organizations")
SUBDOMAIN_DOMAINS_CSV = os.path.join(SUBDOMAIN_DATA_GATHERED, "results", "gathered.csv")

###
# Main task flow.

# Read in data from domains.csv, and scan data from domain-scan.
# All database operations are made in the run() method.
#
# This method blows away the database and rebuilds it from the given data.
def run(date: str, connection_string: str):
    if date is None:
        date = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")

    # Read in domains and organizations from domains.csv.
    # Returns dicts of values ready for saving as Domain and Agency objects.
    #
    # Also returns gathered subdomains, which need more filtering to be useful.
    domains, organizations, gathered_subdomains = load_domain_data()

    # Read in domain-scan CSV data.
    parent_scan_data = load_parent_scan_data(domains)
    subdomains, subdomain_scan_data = load_subdomain_scan_data(
        domains, parent_scan_data, gathered_subdomains
    )

    # Capture manual exclusions and pull out some high-level data from pshtt.
    for domain_name in parent_scan_data.keys():
        # Pull out a few pshtt.csv fields as general domain-level metadata.
        pshtt = parent_scan_data[domain_name].get("pshtt", None)
        if pshtt is None:
            # generally means scan was on different domains.csv, but
            # invalid domains can hit this.
            LOGGER.warning("[%s] No pshtt data for domain!" % domain_name)

            # Remove the domain from further consideration.
            # Destructive, so have this done last.
            del domains[domain_name]
        else:
            # LOGGER.info("[%s] Updating with pshtt metadata." % domain_name)
            domains[domain_name]["live"] = boolean_for(pshtt["Live"])
            domains[domain_name]["redirect"] = boolean_for(pshtt["Redirect"])
            domains[domain_name]["canonical"] = pshtt["Canonical URL"]

    # Prepare subdomains the same way
    for subdomain_name in subdomain_scan_data.keys():
        pshtt = subdomain_scan_data[subdomain_name].get("pshtt")
        subdomains[subdomain_name]["live"] = boolean_for(pshtt["Live"])
        subdomains[subdomain_name]["redirect"] = boolean_for(pshtt["Redirect"])
        subdomains[subdomain_name]["canonical"] = pshtt["Canonical URL"]

    # Save what we've got to the database so far.

    sorted_domains = list(domains.keys())
    sorted_domains.sort()
    sorted_subdomains = list(subdomains.keys())
    sorted_subdomains.sort()
    sorted_organizations = list(organizations.keys())
    sorted_organizations.sort()

    # Calculate high-level per-domain conclusions for each report.
    # Overwrites `domains` and `subdomains` in-place.
    process_domains(
        domains, organizations, subdomains, parent_scan_data, subdomain_scan_data
    )

    # Reset the database.
    LOGGER.info("Clearing the database.")
    with models.Connection(connection_string) as connection:
        connection.domains.clear()
        connection.reports.clear()
        connection.organizations.clear()

        # Calculate organization-level summaries. Updates `organizations` in-place.
        update_organization_totals(organizations, domains, subdomains)

        # Calculate government-wide summaries.
        report = full_report(domains, subdomains)
        report["report_date"] = date

        LOGGER.info("Creating all domains.")
        connection.domains.create_all(domains[domain_name] for domain_name in sorted_domains)
        LOGGER.info("Creating all subdomains.")
        connection.domains.create_all(
            subdomains[subdomain_name] for subdomain_name in sorted_subdomains
        )
        LOGGER.info("Creating all organizations.")
        connection.organizations.create_all(organizations[organization_name] for organization_name in sorted_organizations)

        # Create top-level summaries.
        LOGGER.info("Creating government-wide totals.")
        connection.reports.create(report)

    # Print and exit
    print_report(report)


# Reads in input CSVs (domain list).
def load_domain_data():

    domain_map = {}
    organization_map = {}
    gathered_subdomain_map = {}

    # if domains.csv wasn't cached, download it anew
    if not os.path.exists(PARENT_DOMAINS_CSV):
        LOGGER.info("Downloading domains.csv...")
        mkdir_p(PARENT_CACHE)
        if DOMAINS.startswith("http:") or DOMAINS.startswith("https:"):
            shell_out(["wget", DOMAINS, "-O", PARENT_DOMAINS_CSV])
        else:
            copyfile(DOMAINS, PARENT_DOMAINS_CSV)

    if not os.path.exists(PARENT_DOMAINS_CSV):
        LOGGER.critical("Couldn't download domains.csv")
        exit(1)

    with open(PARENT_DOMAINS_CSV, newline="") as csvfile:
        for row in csv.reader(csvfile):
            if row[0].lower().startswith("domain"):
                continue

            domain_name = row[0].lower().strip()
            organization_name_en = row[2].strip()
            organization_name_fr = row[3].strip()
            organization_slug = slugify.slugify(organization_name_en)

            if domain_name not in domain_map:
                # By assuming the domain name is the base domain if it appears
                # in current-federal.csv, we automatically treat fed.us domains
                # as base domains, without explicitly incorporating the Public
                # Suffix List.
                #
                # And since we excluded "fed.us" itself above, this should
                # cover all the bases.
                domain_map[domain_name] = {
                    "domain": domain_name,
                    "base_domain": domain_name,
                    "organization_name_en": organization_name_en,
                    "organization_name_fr": organization_name_fr,
                    "organization_slug": organization_slug,
                    "sources": ["canada-gov"],
                    "is_parent": True,
                    "exclude": {},
                }

            if organization_slug not in organization_map:
                organization_map[organization_slug] = {
                    "name_en": organization_name_en,
                    "name_fr": organization_name_fr,
                    "slug": organization_slug,
                    "total_domains": 1,
                }

            else:
                organization_map[organization_slug]["total_domains"] += 1

    with open(SUBDOMAIN_DOMAINS_CSV, newline="") as csvfile:
        for row in csv.reader(csvfile):
            if row[0].lower().startswith("domain"):
                continue

            subdomain_name = row[0].lower().strip()

            if subdomain_name not in gathered_subdomain_map:
                # check each source
                sources = []
                for i, source in enumerate(GATHERER_NAMES):
                    if boolean_for(row[i + 2]):
                        sources.append(source)

                gathered_subdomain_map[subdomain_name] = sources

    return domain_map, organization_map, gathered_subdomain_map


# Load in data from the CSVs produced by domain-scan.
# The 'domains' map is used to ignore any untracked domains.
def load_parent_scan_data(domains):

    parent_scan_data = {}
    for domain_name in domains.keys():
        parent_scan_data[domain_name] = {}

    headers = []
    with open(os.path.join(PARENT_RESULTS, "pshtt.csv"), newline="") as csvfile:
        for row in csv.reader(csvfile):
            if row[0].lower() == "domain":
                headers = row
                continue

            domain = row[0].lower()
            if not domains.get(domain):
                LOGGER.info("[pshtt] Skipping %s, not a federal domain from domains.csv.", domain)
                continue

            dict_row = {}
            for i, cell in enumerate(row):
                dict_row[headers[i]] = cell
            parent_scan_data[domain]["pshtt"] = dict_row

    headers = []
    with open(os.path.join(PARENT_RESULTS, "sslyze.csv"), newline="") as csvfile:
        for row in csv.reader(csvfile):
            if row[0].lower() == "domain":
                headers = row
                continue

            domain = row[0].lower()
            if not domains.get(domain):
                LOGGER.info("[sslyze] Skipping %s, not a in domains.csv.", domain)
                continue

            dict_row = {}
            for i, cell in enumerate(row):
                dict_row[headers[i]] = cell

            # If the scan was invalid, most fields will be empty strings.
            # It'd be nice to make this more semantic on the domain-scan side.
            if dict_row["SSLv2"] == "":
                LOGGER.info("[%s] Skipping, scan data was invalid.", domain)
                continue

            parent_scan_data[domain]["sslyze"] = dict_row

    return parent_scan_data


def load_subdomain_scan_data(domains, parent_scan_data, gathered_subdomains):

    # we'll only create entries if they are in pshtt and "live"
    subdomain_scan_data = {}

    # These will be entries in the Domain table.
    subdomains = {}

    # Next, load in subdomain pshtt data. While we also scan subdomains
    # for sslyze, pshtt is the data backbone for subdomains.
    pshtt_subdomains_csv = os.path.join(SUBDOMAIN_DATA_SCANNED, "results", "pshtt.csv")

    headers = []
    with open(pshtt_subdomains_csv, newline="") as csvfile:
        for row in csv.reader(csvfile):
            if row[0].lower() == "domain":
                headers = row
                continue

            subdomain = row[0].lower()
            parent_domain = row[1].lower()

            if subdomain not in gathered_subdomains:
                LOGGER.info("[%s] Skipping, not a gathered subdomain.", subdomain)
                continue

            if not domains.get(parent_domain):
                LOGGER.info("[%s] Skipping, not a subdomain of a tracked domain, parent %s.", subdomain, parent_domain)
                continue

            dict_row = {}
            for i, cell in enumerate(row):
                dict_row[headers[i]] = cell

            # Optimization: only bother storing in memory if Live is True.
            if boolean_for(dict_row["Live"]):

                # Initialize subdomains obj if this is its first one.
                if parent_scan_data[parent_domain].get("subdomains") is None:
                    parent_scan_data[parent_domain]["subdomains"] = []

                parent_scan_data[parent_domain]["subdomains"].append(subdomain)

                # if there are dupes for some reason, they'll be overwritten
                subdomain_scan_data[subdomain] = {"pshtt": dict_row}

                subdomains[subdomain] = {
                    "domain": subdomain,
                    "base_domain": parent_domain,
                    "organization_slug": domains[parent_domain]["organization_slug"],
                    "organization_name_en": domains[parent_domain]["organization_name_en"],
                    "organization_name_fr": domains[parent_domain]["organization_name_fr"],
                    "is_parent": False,
                    "sources": gathered_subdomains[subdomain],
                }

    # Load in sslyze subdomain data.
    # Note: if we ever add more subdomain scanners, this loop
    # could be genericized and iterated over really easily.
    sslyze_subdomains_csv = os.path.join(
        SUBDOMAIN_DATA_SCANNED, "results", "sslyze.csv"
    )

    headers = []
    with open(sslyze_subdomains_csv, newline="") as csvfile:
        for row in csv.reader(csvfile):
            if row[0].lower() == "domain":
                headers = row
                continue

            subdomain = row[0].lower()

            if not subdomain_scan_data.get(subdomain):
                LOGGER.info("[%s] Skipping, we didn't save pshtt data for this.", subdomain)
                continue

            dict_row = {}
            for i, cell in enumerate(row):
                dict_row[headers[i]] = cell

            # If the scan was invalid, most fields will be empty strings.
            # It'd be nice to make this more semantic on the domain-scan side.
            if dict_row["SSLv2"] == "":
                LOGGER.info("[%s] Skipping, scan data was invalid.", subdomain)
                continue

            # if there are dupes for some reason, they'll be overwritten
            subdomain_scan_data[subdomain]["sslyze"] = dict_row

    return subdomains, subdomain_scan_data


# Given the domain data loaded in from CSVs, draw conclusions,
# and filter/transform data into form needed for display.
def process_domains(
    domains, organizations, subdomains, parent_scan_data, subdomain_scan_data
):

    # For each domain, determine eligibility and, if eligible,
    # use the scan data to draw conclusions.
    for domain_name in domains.keys():

        ### HTTPS
        #
        # For HTTPS, we calculate individual reports for every subdomain.

        https_parent = {
            "eligible": False,  # domain eligible itself (is it live?)
            "eligible_zone": False,  # zone eligible (itself or any live subdomains?)
        }
        eligible_children = []
        eligible_zone = False

        # No matter what, put the preloaded state onto the parent,
        # since even an unused domain can always be preloaded.
        https_parent["preloaded"] = preloaded_or_not(
            parent_scan_data[domain_name]["pshtt"]
        )

        # Tally subdomains first, so we know if the parent zone is
        # definitely eligible as a zone even if not as a website
        for subdomain_name in parent_scan_data[domain_name].get("subdomains", []):

            if eligible_for_https(subdomains[subdomain_name]):
                eligible_children.append(subdomain_name)
                subdomains[subdomain_name]["https"] = https_behavior_for(
                    subdomain_name,
                    subdomain_scan_data[subdomain_name]["pshtt"],
                    subdomain_scan_data[subdomain_name].get("sslyze", None),
                    parent_preloaded=https_parent["preloaded"],
                )

        # ** syntax merges dicts, available in 3.5+
        if eligible_for_https(domains[domain_name]):
            https_parent = {
                **https_parent,
                **https_behavior_for(
                    domain_name,
                    parent_scan_data[domain_name]["pshtt"],
                    parent_scan_data[domain_name].get("sslyze", None),
                ),
            }
            https_parent["eligible_zone"] = True

        # even if not eligible directly, can be eligible via subdomains
        elif len(eligible_children) > 0:
            https_parent["eligible_zone"] = True

        # If the parent zone is preloaded, make sure that each subdomain
        # is considered to have HSTS in place. If HSTS is yes on its own,
        # leave it, but if not, then grant it the minimum level.
        # TODO:

        domains[domain_name]["https"] = https_parent

        # Totals based on summing up eligible reports within this domain.
        totals = {}

        # For HTTPS/HSTS, pshtt-eligible parent + subdomains.
        eligible_reports = [subdomains[name]["https"] for name in eligible_children]
        if https_parent["eligible"]:
            eligible_reports = [https_parent] + eligible_reports
        totals["https"] = total_https_report(eligible_reports)

        # For SSLv2/SSLv3/RC4/3DES, sslyze-eligible parent + subdomains.
        subdomain_names = parent_scan_data[domain_name].get("subdomains", [])
        eligible_reports = [
            subdomains[name]["https"]
            for name in subdomain_names
            if subdomains[subdomain_name].get("https")
            and subdomains[subdomain_name]["https"].get("rc4") is not None
        ]
        if https_parent and https_parent.get("rc4") is not None:
            eligible_reports = [https_parent] + eligible_reports
        totals["crypto"] = total_crypto_report(eligible_reports)

        domains[domain_name]["totals"] = totals


# Given a list of domains or subdomains, quick filter to which
# are eligible for this report, optionally for an organization.
def eligible_for(report, hosts, organization=None):
    return [
        host[report]
        for hostname, host in hosts.items()
        if (
            host.get(report)
            and host[report]["eligible"]
            and ((organization is None) or (host["organization_slug"] == organization["slug"]))
        )
    ]


# Go through each report type and add organization totals for each type.
def update_organization_totals(organizations, domains, subdomains):

    # For each organization, update their report counts for every domain they have.
    for organization_slug in organizations.keys():
        organization = organizations[organization_slug]

        # HTTPS. Parent and subdomains.
        # LOGGER.info("[%s][%s] Totalling report." % (organization['slug'], 'https'))
        eligible = eligible_for("https", domains, organization) + eligible_for(
            "https", subdomains, organization
        )
        organization["https"] = total_https_report(eligible)

        # Separate report for crypto, for sslyze-scanned domains.
        # LOGGER.info("[%s][%s] Totalling report." % (organization['slug'], 'crypto'))
        eligible = [
            domain["https"]
            for name, domain in domains.items()
            if (domain["organization_slug"] == organization["slug"])
            and domain.get("https")
            and (domain["https"].get("rc4") is not None)
        ]
        eligible = eligible + [
            subdomain["https"]
            for name, subdomain in subdomains.items()
            if (subdomain["organization_slug"] == organization["slug"])
            and subdomain.get("https")
            and (subdomain["https"].get("rc4") is not None)
        ]
        organization["crypto"] = total_crypto_report(eligible)

        # Special separate report for preloaded parent domains.
        # All parent domains, whether they use HTTP or not, are eligible.
        # LOGGER.info("[%s][%s] Totalling report." % (organization['slug'], 'preloading'))
        eligible = [
            host["https"]
            for hostname, host in domains.items()
            if host["organization_slug"] == organization_slug
        ]
        organization["preloading"] = total_preloading_report(eligible)


# Create a Report about each tracked stat.
def full_report(domains, subdomains):

    full = {}

    # HTTPS. Parent and subdomains.
    LOGGER.info("[https] Totalling full report.")
    eligible = eligible_for("https", domains) + eligible_for("https", subdomains)
    full["https"] = total_https_report(eligible)

    LOGGER.info("[crypto] Totalling full report.")
    eligible = [
        domain["https"]
        for name, domain in domains.items()
        if domain.get("https") and (domain["https"].get("rc4") is not None)
    ]
    eligible = eligible + [
        subdomain["https"]
        for name, subdomain in subdomains.items()
        if subdomain.get("https") and (subdomain["https"].get("rc4") is not None)
    ]
    full["crypto"] = total_crypto_report(eligible)

    # Special separate report for preloaded parent domains.
    # All parent domains, whether they use HTTP or not, are eligible.
    LOGGER.info("[preloading] Totalling full report.")
    eligible = [host["https"] for hostname, host in domains.items()]
    full["preloading"] = total_preloading_report(eligible)

    return full

def eligible_for_https(domain):
    return domain["live"] == True


# Given a pshtt report and (optional) sslyze report,
# fill in a dict with the conclusions.
def https_behavior_for(name, pshtt, sslyze, parent_preloaded=None):
    report = {"eligible": True}

    # assumes that HTTPS would be technically present, with or without issues
    if pshtt["Downgrades HTTPS"] == "True":
        https = 0  # No
    else:
        if pshtt["Valid HTTPS"] == "True":
            https = 2  # Yes
        elif (
            (pshtt["HTTPS Bad Chain"] == "True")
            and (pshtt["HTTPS Bad Hostname"] == "False")
        ):
            https = 1  # Yes
        else:
            https = -1  # No

    report["uses"] = https

    ###
    # Is HTTPS enforced?

    if https <= 0:
        behavior = 0  # N/A

    else:

        # "Yes (Strict)" means HTTP immediately redirects to HTTPS,
        # *and* that HTTP eventually redirects to HTTPS.
        #
        # Since a pure redirector domain can't "default" to HTTPS
        # for itself, we'll say it "Enforces HTTPS" if it immediately
        # redirects to an HTTPS URL.
        if (
            (pshtt["Strictly Forces HTTPS"] == "True")
            and (
                (pshtt["Defaults to HTTPS"] == "True") or (pshtt["Redirect"] == "True")
            )
        ):
            behavior = 3  # Yes (Strict)

        # "Yes" means HTTP eventually redirects to HTTPS.
        elif (
            (pshtt["Strictly Forces HTTPS"] == "False")
            and (pshtt["Defaults to HTTPS"] == "True")
        ):
            behavior = 2  # Yes

        # Either both are False, or just 'Strict Force' is True,
        # which doesn't matter on its own.
        # A "present" is better than a downgrade.
        else:
            behavior = 1  # Present (considered 'No')

    report["enforces"] = behavior

    ###
    # Characterize the presence and completeness of HSTS.

    if pshtt["HSTS Max Age"]:
        hsts_age = int(pshtt["HSTS Max Age"])
    else:
        hsts_age = None

    # If this is a subdomain, it can be considered as having HSTS, via
    # the preloading of its parent.
    if parent_preloaded:
        hsts = 3  # Yes, via preloading

    # Otherwise, without HTTPS there can be no HSTS for the domain directly.
    elif (https <= 0):
        hsts = -1  # N/A (considered 'No')

    else:

        # HSTS is present for the canonical endpoint.
        if (pshtt["HSTS"] == "True") and hsts_age:

            # Say No for too-short max-age's, and note in the extended details.
            if hsts_age >= 31536000:
                hsts = 2  # Yes, directly
            else:
                hsts = 1  # No

        else:
            hsts = 0  # No

    # Separate preload status from HSTS status:
    #
    # * Domains can be preloaded through manual overrides.
    # * Confusing to mix an endpoint-level decision with a domain-level decision.
    if pshtt["HSTS Preloaded"] == "True":
        preloaded = 2  # Yes
    elif (pshtt["HSTS Preload Ready"] == "True"):
        preloaded = 1  # Ready for submission
    else:
        preloaded = 0  # No

    report["hsts"] = hsts
    report["hsts_age"] = hsts_age
    report["preloaded"] = preloaded

    ###
    # Get cipher/protocol data via sslyze for a host.

    sslv2 = None
    sslv3 = None
    any_rc4 = None
    any_3des = None

    # values: unknown or N/A (-1), No (0), Yes (1)
    bod_crypto = None


    # N/A if no HTTPS
    if report["uses"] <= 0:
        bod_crypto = -1  # N/A

    elif sslyze is None:
        # LOGGER.info("[https][%s] No sslyze scan data found." % name)
        bod_crypto = -1  # Unknown

    else:
        ###
        # BOD 18-01 (cyber.dhs.gov) cares about SSLv2, SSLv3, RC4, and 3DES.
        any_rc4 = boolean_for(sslyze["Any RC4"])
        # TODO: kill conditional once everything is synced
        if sslyze.get("Any 3DES"):
            any_3des = boolean_for(sslyze["Any 3DES"])
        sslv2 = boolean_for(sslyze["SSLv2"])
        sslv3 = boolean_for(sslyze["SSLv3"])

        if any_rc4 or any_3des or sslv2 or sslv3:
            bod_crypto = 0
        else:
            bod_crypto = 1

    report["bod_crypto"] = bod_crypto
    report["rc4"] = any_rc4
    report["3des"] = any_3des
    report["sslv2"] = sslv2
    report["sslv3"] = sslv3

    # Final calculation: is the service compliant with all of M-15-13
    # (HTTPS+HSTS) and BOD 18-01 (that + RC4/3DES/SSLv2/SSLv3)?

    # For M-15-13 compliance, the service has to enforce HTTPS,
    # and has to have strong HSTS in place (can be via preloading).
    m1513 = (behavior >= 2) and (hsts >= 2)

    # For BOD compliance, only ding if we have scan data:
    # * If our scanner dropped, give benefit of the doubt.
    # * If they have no HTTPS, this will fix itself once HTTPS comes on.
    bod1801 = m1513 and (bod_crypto != 0)

    # Phew!
    report["m1513"] = m1513
    report["compliant"] = bod1801  # equivalent, since BOD is a superset

    return report


# Just returns a 0 or 2 for inactive (not live) zones, where
# we still may care about preloaded state.
def preloaded_or_not(pshtt):
    if pshtt["HSTS Preloaded"] == "True":
        return 2  # Yes
    else:
        return 0  # No


# 'eligible' should be a list of dicts with https report data.
def total_https_report(eligible):
    total_report = {
        "eligible": len(eligible),
        "uses": 0,
        "enforces": 0,
        "hsts": 0,
        # compliance roll-ups
        "m1513": 0,
        "compliant": 0,
    }

    for report in eligible:

        # Needs to be enabled, with issues is allowed
        if report["uses"] >= 1:
            total_report["uses"] += 1

        # Needs to be Default or Strict to be 'Yes'
        if report["enforces"] >= 2:
            total_report["enforces"] += 1

        # Needs to be present with >= 1 year max-age for canonical endpoint,
        # or preloaded via its parent zone.
        if report["hsts"] >= 2:
            total_report["hsts"] += 1

        # Factors in crypto score, but treats ineligible services as passing.
        for field in ["m1513", "compliant"]:
            if report[field]:
                total_report[field] += 1

    return total_report


def total_crypto_report(eligible):
    total_report = {
        "eligible": len(eligible),
        "bod_crypto": 0,
        "rc4": 0,
        "3des": 0,
        "sslv2": 0,
        "sslv3": 0,
    }

    for report in eligible:
        if report.get("bod_crypto") is None:
            continue

        # Needs to be a Yes
        if report["bod_crypto"] == 1:
            total_report["bod_crypto"] += 1

        # Tracking separately, may not display separately
        if report["rc4"]:
            total_report["rc4"] += 1
        if report["3des"]:
            total_report["3des"] += 1
        if report["sslv2"]:
            total_report["sslv2"] += 1
        if report["sslv3"]:
            total_report["sslv3"] += 1

    return total_report


def total_preloading_report(eligible):
    total_report = {"eligible": len(eligible), "preloaded": 0, "preload_ready": 0}

    # Tally preloaded and preload-ready
    for report in eligible:
        # We consider *every* domain eligible for preloading,
        # so there may be no pshtt data for some.
        if report.get("preloaded") is None:
            continue

        if report["preloaded"] == 1:
            total_report["preload_ready"] += 1
        elif report["preloaded"] == 2:
            total_report["preloaded"] += 1

    return total_report


# Hacky helper - print out the %'s after the command finishes.
def print_report(report):

    for report_type in report.keys():
        if report_type == "report_date" or report_type == "_id":
            continue

        LOGGER.info("[%s]" % report_type)
        eligible = report[report_type]["eligible"]
        for key in report[report_type].keys():
            if key == "eligible":
                LOGGER.info("%s: %i" % (key, report[report_type][key]))
            else:
                LOGGER.info(
                    "%s: %i%% (%i)"
                    % (
                        key,
                        percent(report[report_type][key], eligible),
                        report[report_type][key],
                    )
                )


### utilities
def shell_out(command, env=None):
    try:
        LOGGER.info("[cmd] %s" % str.join(" ", command))
        response = subprocess.check_output(command, shell=False, env=env)
        output = str(response, encoding="UTF-8")
        LOGGER.info(output)
        return output
    except subprocess.CalledProcessError:
        logging.critical("Error running %s." % (str(command)))
        exit(1)
        return None


def percent(num, denom):
    if denom == 0:
        return 0  # for shame!
    return round((num / denom) * 100)


# mkdir -p in python, from:
# https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise


def write(content, destination, binary=False):
    mkdir_p(os.path.dirname(destination))

    if binary:
        f = open(destination, "bw")
    else:
        f = open(destination, "w", encoding="utf-8")
    f.write(content)
    f.close()


def boolean_for(string):
    if string == "False":
        return False
    else:
        return True
