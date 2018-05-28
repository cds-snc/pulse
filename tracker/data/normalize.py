#!/usr/bin/env python
import csv
import re
import typing
import publicsuffix
import click

@click.command()
@click.option('--domain-column', type=str, default='domain')
@click.option('--organization-column', type=str, default='organization')
@click.option('--encoding', type=str, default='utf-8')
@click.option('--ignore', type=str)
@click.argument('domains', type=click.Path())
@click.argument('output-parents', type=click.File('w'))
@click.argument('output-subdomains', type=click.File('w'))
def normalize(
        domain_column: str,
        organization_column: str,
        encoding: str,
        ignore: str,
        domains: str,
        output_parents: typing.IO[str],
        output_subdomains: typing.IO[str]) -> None:

    with open(domains, 'r', newline='', encoding=encoding) as domain_file:
        input_domains = csv.DictReader(domain_file)
        output_parent_csv = csv.DictWriter(output_parents, fieldnames=['domain', 'organization', 'original', 'path'])
        output_subdomain_csv = csv.DictWriter(output_subdomains, fieldnames=['domain'])

        output_parent_csv.writeheader()
        output_subdomain_csv.writeheader()

        domain_pattern = re.compile(r"^(?:https?://)?(?:www\.)?(.*?)([^a-zA-Z0-9-.].*)?$")

        psl = publicsuffix.PublicSuffixList(publicsuffix.fetch())
        parents = set()
        subdomains = set()

        for row in input_domains:
            domain = row.get(domain_column).strip().lower()
            if domain == ignore:
                continue

            match = domain_pattern.search(domain)
            if match:
                subdomain = match.group(1)
            else:
                continue
            parent = psl.get_public_suffix(subdomain)

            # TODO: Handle cases where no subdomains for a given parent exist
            # TODO: If a given domain is a parent domain, it might not be the owner of a
            if parent not in parents:
                output_parent_csv.writerow({'domain': parent, 'organization': row.get(organization_column), 'original': parent == subdomain, 'path': match.group(2)})
                parents.add(parent)

            if parent != subdomain and subdomain not in subdomains:
                output_subdomain_csv.writerow({'domain': subdomain})
                subdomains.add(subdomain)


if __name__ == '__main__':
    normalize()
