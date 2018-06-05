import csv
import os
import typing
import datetime
import click
import ujson
from data import env
from data.env import DATA_DIR
from data import update as data_update
from data import processing
from data import logger
from data import models
from data.preprocess import pull_data


LOGGER = logger.get_logger(__name__)


class DateType(click.ParamType):
    name = "date"

    def convert(self, value, param, ctx) -> typing.Optional[str]:
        try:
            datetime.datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            self.fail(f"{value} is not a valid date")
DATE = DateType()


def get_cached_date(directory: str) -> str:
    meta = os.path.join(directory, "output/domains/results/meta.json")
    with open(meta) as meta_file:
        scan_meta = ujson.load(meta_file)
    return scan_meta["start_time"][0:10]


def get_date(
        ctx: typing.Optional[click.core.Context],  # pylint: disable=unused-argument
        param: typing.Optional[click.core.Option],  # pylint: disable=unused-argument
        value: typing.Optional[str],
    ) -> str:
    return value if value is not None else get_cached_date(DATA_DIR)


# Convert ["--option", "value", ... ] to {"option": "value", ...}
def transform_args(args: typing.List[str]) -> typing.Dict[str, typing.Union[str, bool]]:
    transformed = {}
    for option, value in zip(args, args[1:]):
        if option.startswith("--"):
            name = option.strip("--")
            transformed[name] = value if not value.startswith("--") else True
    return transformed


@click.group()
@click.option("--connection", type=str, default="mongodb://localhost:27017/track", envvar="TRACKER_MONGO_URI")
@click.pass_context
def main(ctx: click.core.Context, connection: str) -> None:
    ctx.obj = {
        'connection_string': connection
    }


@main.command(
    context_settings=dict(ignore_unknown_options=True),
    help="Coposition of `update`, `process`, and `upload` commands",
)
@click.option("--date", type=DATE)
@click.option('--scanner', type=str, multiple=True, default=['pshtt', 'sslyze'], envvar='SCANNERS')
@click.option('--domains', type=click.Path(), default=env.DOMAINS, envvar='DOMAINS')
@click.option('--output', type=click.Path(), default=env.SCAN_DATA, envvar='SCAN_DATA')
@click.argument("scan_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def run(
        ctx: click.core.Context,
        date: typing.Optional[str],
        scanner: typing.List[str],
        domains: str,
        output: str,
        scan_args: typing.List[str],
    ) -> None:

    update.callback(scanner, domains, output, scan_args)
    the_date = get_date(None, "date", date)
    process.callback(the_date)


@main.command()
@click.option("--output", type=click.Path())
@click.pass_context
def preprocess(ctx: click.core.Context, output: typing.Optional[str]) -> None:
    if not output:
        output = os.path.join(os.getcwd(), 'csv')
    pull_data(output, ctx.obj.get('connection_string'))


@main.command(
    context_settings=dict(ignore_unknown_options=True), help="Gather and scan domains"
)
@click.option('--scanner', type=str, multiple=True, default=['pshtt', 'sslyze'], envvar='SCANNERS')
@click.option('--domains', type=click.Path(), default=env.DOMAINS, envvar='DOMAINS')
@click.option('--output', type=click.Path(), default=env.SCAN_DATA, envvar='SCAN_DATA')
@click.argument("scan_args", nargs=-1, type=click.UNPROCESSED)
def update(scanner: typing.List[str], domains: str, output: str, scan_args: typing.List[str]) -> None:
    LOGGER.info("Starting update")
    data_update.update(scanner, domains, output, transform_args(scan_args))
    LOGGER.info("Finished update")


@main.command(help="Process scan data")
@click.option("--date", type=DATE, callback=get_date)
@click.pass_context
def process(ctx: click.core.Context, date: str) -> None:
    # Sanity check to make sure we have what we need.
    if not os.path.exists(os.path.join(env.SCAN_RESULTS, "meta.json")):
        LOGGER.info("No scan metadata downloaded, aborting.")
        return

    LOGGER.info(f"[{date}] Loading data into track-digital.")
    processing.run(date, ctx.obj.get('connection_string'))
    LOGGER.info(f"[{date}] Data now loaded into track-digital.")


@main.command(help="Populate DB with domains")
@click.argument('owners', type=click.File('r', encoding='utf-8-sig'))
@click.argument('domains', type=click.File('r', encoding='utf-8-sig'))
@click.pass_context
def insert(ctx: click.core.Context, owners: typing.IO[str], domains: typing.IO[str]) -> None:
    owners_reader = csv.DictReader(owners)
    domains_reader = csv.DictReader(domains)

    with models.Connection(ctx.obj.get('connection_string')) as connection:
        connection.owners.create_all(document for document in owners_reader)
        connection.input_domains.create_all(document for document in domains_reader)
