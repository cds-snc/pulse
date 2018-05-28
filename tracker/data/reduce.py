#!/usr/bin/env python
import csv
import collections
import logging
import itertools
import typing
import click


@click.group()
def main():
    pass


def merge_subdomains(domains: typing.Iterable[typing.IO[str]]) -> typing.Iterator[typing.List[str]]:
    unique_domains = set()
    reader = itertools.chain(*map(csv.DictReader, domains))

    for row in reader:
        domain = row.get('domain').strip() or 'unknown'
        if domain not in unique_domains:
            unique_domains.add(domain)
            yield [domain]


def merge_parents(domains: typing.Iterable[typing.IO[str]]) -> typing.Iterator[typing.List[str]]:
    reader = itertools.chain(*map(csv.DictReader, domains))

    unique_domains = collections.defaultdict(set)

    for row in reader:
        domain = row.get('domain').strip() or 'unknown'
        organization = row.get('organization').strip() or 'unknown'
        original = row.get('original') or False
        path = row.get('path') or ''

        if domain in unique_domains:
            logging.warning('conflict with domain %s', domain)

        unique_domains[domain].add((organization, original, path))

    for domain, entries in unique_domains.items():
        known = [entry for entry in entries if entry[0] != 'unknown']
        if known:
            entries = known

        if len(entries) > 1:

            logging.warning('domain %s has organizations %s', domain, ', '.join([entry[0] for entry in entries]))
            originals = [entry for entry in entries if entry[1]]
            if originals:
                entries = originals

            smallest_path = min(entries, key=lambda e: e[2])
            logging.warning('choosing %s', smallest_path[0])
            yield [
                domain,
                smallest_path[0]
            ]
        else:
            yield [domain, next(iter(entries))[0]]



@main.command()
@click.option('--type', type=str, default='subdomain')
@click.argument('domains', type=click.File('r'), nargs=-1)
@click.argument('output', type=click.File('w'), nargs=1)
def merge(type: str, domains: typing.Iterable[typing.IO[str]], output: typing.IO[str]) -> None:
    writer = csv.writer(output)

    if type == 'subdomain':
        writer.writerow(['domain'])
        combine = merge_subdomains
    else:
        writer.writerow(['domain', 'organization'])
        combine = merge_parents

    for row in combine(domains):
        writer.writerow(row)


if __name__ == '__main__':
    main()
