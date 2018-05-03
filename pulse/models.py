import pymongo
import os
import io
import datetime
import csv
import typing
from werkzeug.local import LocalProxy
from flask_pymongo import PyMongo
from pulse.data import CSV_FIELDS, FIELD_MAPPING, LABELS

# These functions are meant to be the only ones that access the g.db.db
# directly. If we ever decide to migrate from tinyg.db.db, that can all be
# coordinated here.

db = PyMongo()

# Data loads should clear the entire database first.
def clear_database():
    db.cx.drop_database(db.db)


class Report:
    # report_date (string, YYYY-MM-DD)
    # https.eligible (number)
    # https.uses (number)
    # https.enforces (number)
    # https.hsts (number)
    # https.bod (number)
    # analytics.eligible (number)
    # analytics.participates (number)

    # Initialize a report with a given date.
    def create(data):
        db.db.pulse.reports.insert_one(data.copy())

    def report_time(report_date):
        return datetime.datetime.strptime(report_date, "%Y-%m-%d")

    # There's only ever one.
    def latest():
        return db.db.pulse.reports.find_one({}, {'_id': False})


class Domain:
    # domain (string)
    # agency_slug (string)
    # is_parent (boolean)
    #
    # agency_name (string)
    # branch (string, legislative/judicial/executive)
    #
    # parent_domain (string)
    # sources (array of strings)
    #
    # live? (boolean)
    # redirect? (boolean)
    # canonical (string, URL)
    #
    # totals: {
    #   https: { ... }
    #   crypto: { ... }
    # }
    #
    # https: { ... }
    # analytics: { ... }
    #

    def create(data):
        return db.db.pulse.domains.insert_one(data)

    def create_all(iterable: typing.List[typing.Dict]):
        return db.db.pulse.domains.insert_many(iterable)

    def update(domain_name, data):
        return db.db.pulse.domains.update_one(
            {'domain': domain_name},
            {'$set': data},
        )

    def add_report(domain_name, report_name, report):
        return db.db.pulse.domains.update_one(
            {'domain': domain_name},
            {'$set': {report_name: report}}
        )

    def find(domain_name):
        return db.db.pulse.domains.find_one({'domain': domain_name}, {'_id': False})

    # Useful when you want to pull in all domain entries as peers,
    # such as reports which only look at parent domains, or
    # a flat CSV of all hostnames that match a report.
    def eligible(report_name):
        return db.db.pulse.domains.find(
            {f'{report_name}.eligible': True}, {'_id': False}
        )

    # Useful when you have mixed parent/subdomain reporting,
    # used for HTTPS but not yet others.
    def eligible_parents(report_name):
        return db.db.pulse.domains.find(
            {f'{report_name}.eligible_zone': True, 'is_parent': True}, {'_id': False}
        )

    # Useful when you want to pull down subdomains of a particular
    # parent domain. Used for HTTPS expanded reports.
    def eligible_for_domain(domain, report_name):
        return db.db.pulse.domains.find(
            {f'{report_name}.eligible': True, 'base_domain': domain}, {'_id': False}
        )

    def all():
        return db.db.pulse.domains.find({}, {'_id': False})

    def to_csv(domains, report_type):
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

        def value_for(value):
            # if it's a list, convert it to a list of strings and join
            if type(value) is list:
                value = [str(x) for x in value]
                value = ", ".join(value)
            elif type(value) is bool:
                value = {True: 'Yes', False: 'No'}[value]
            return value

        # initialize with a header row
        header = []

        # Common fields, and report-specific fields
        for category in ['common', report_type]:
            for field in CSV_FIELDS[category]:
                header.append(LABELS[category][field])
        writer.writerow(header)

        for domain in domains:
            row = []

            # Common fields, and report-specific fields
            for category in ['common', report_type]:

                # Currently, all report-specific fields use a mapping
                for field in CSV_FIELDS[category]:

                    # common fields are top-level on Domain objects
                    if category == 'common':
                        value = domain.get(field)
                    else:
                        value = domain[report_type].get(field)

                    # If a mapping exists e.g. 1 -> "Yes", etc.
                    if (
                            FIELD_MAPPING.get(category) and
                            FIELD_MAPPING[category].get(field) and
                            (FIELD_MAPPING[category][field].get(value) is not None)
                        ):
                        value = FIELD_MAPPING[category][field][value]

                    row.append(value_for(value))

            writer.writerow(row)

        return output.getvalue()


class Agency:
    # agency_slug (string)
    # agency_name (string)
    # branch (string)
    # total_domains (number)
    #
    # https {
    #   eligible (number)
    #   uses (number)
    #   enforces (number)
    #   hsts (number)
    #   modern (number)
    #   preloaded (number)
    # }
    # analytics {
    #   eligible (number)
    #   participating (number)
    # }
    #

    # An agency which had at least 1 eligible domain.
    def eligible(report_name):
        return db.db.pulse.agencies.find({f'{report_name}.eligible': {'$gt': 0}}, {'_id': False})

    # Create a new Agency record with a given name, slug, and total domain count.
    def create(data):
        return db.db.pulse.agencies.insert_one(data)

    def create_all(iterable):
        return db.db.pulse.agencies.insert_many(iterable)

    # For a given agency, add a report.
    def add_report(slug, report_name, report):
        return db.db.pulse.agencies.update_one(
            {'slug', slug},
            {'$set': {report_name: report}}
        )

    def find(slug):
        return db.db.pulse.agencies.find_one({'slug': slug}, {'_id': False})

    def all():
        return db.db.pulse.agencies.find({}, {'_id': False})
