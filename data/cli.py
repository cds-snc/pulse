import os
import typing
import itertools
import datetime
import click
import ujson
from dateutil import parser
from data.env import *
from data import update as data_update
from data import processing
from data import logger


LOGGER = logger.get_logger(__name__)


class DateType(click.ParamType):
    name = 'date'

    def convert(self, value, param, ctx) -> str:
        try:
            datetime.datetime.strptime(value, '%Y-%m-%d')
            return value
        except ValueError:
            self.fail(f'{value} is not a valid date')
DATE = DateType()


def get_cached_date(directory: str) -> str:
    meta = os.path.join(directory, 'output/parents/results/meta.json')
    with open(meta) as meta_file:
        scan_meta = ujson.load(meta_file)
    return scan_meta['start_time'][0:10]


def get_date(ctx, param, value) -> str:
    # Date can be overridden if need be, but defaults to meta.json.
    directory, _ = os.path.split(__file__)

    return value if value is not None else get_cached_date(directory)


# Convert ['--option', 'value', ... ] to {'option': 'value', ...}
def transform_args(args: typing.List[str]) -> typing.Dict[str, str]:
    transformed = {}
    for option, value in zip(args, args[1:]):
        if option.startswith('--'):
            name = option.strip('--')
            transformed[name] = value if not value.startswith('--') else True
    return transformed


@click.group()
def main() -> None:
    pass


@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
    ),
    help='Coposition of `update`, `process`, and `upload` commands',
)
@click.option('--date', type=DATE, callback=get_date)
@click.option('--scan', type=click.Choice(['skip', 'download', 'here']), default='skip')
@click.option('--gather', type=click.Choice(['skip', 'here']), default='here')
@click.option('--upload-results', is_flag=True, default=False)
@click.argument('scan_args', nargs=-1, type=click.UNPROCESSED)
def run(date, scan, gather, upload_results, scan_args) -> None:
    update.callback(scan, gather, scan_args)
    date = get_date(None, 'date', date)
    process.callback(date)
    if upload_results:
        upload.callback(date)


@main.command(
    context_settings=dict(
        ignore_unknown_options=True,
    ),
    help='Gather and scan domains',
)
@click.option('--scan', type=click.Choice(['skip', 'download', 'here']), default='skip')
@click.option('--gather', type=click.Choice(['skip', 'here']), default='here')
@click.argument('scan_args', nargs=-1, type=click.UNPROCESSED)
def update(scan, gather, scan_args) -> None:
    LOGGER.info('Starting update')
    data_update.update(scan, gather, transform_args(scan_args))
    LOGGER.info('Finished update')


@main.command(
    help='Download scan results from s3',
)
def download() -> None:
    LOGGER.info('Downloading production data')
    data_update.download_s3()
    LOGGER.info('Finished downloading production data')


@main.command(
    help='Upload scan results to s3',
)
@click.option('--date', type=DATE, callback=get_date)
def upload(date) -> None:
    # Sanity check to make sure we have what we need.
    if not os.path.exists(os.path.join(PARENTS_RESULTS, "meta.json")):
        LOGGER.info("No scan metadata downloaded, aborting.")
        return

    LOGGER.info(f'[{date}] Syncing scan data and database to S3.')
    data_update.upload_s3(date)
    LOGGER.info(f"[{date}] Scan data and database now in S3.")


@main.command(
    help='Process scan data',
)
@click.option('--date', type=DATE, callback=get_date)
def process(date) -> None:
    # Sanity check to make sure we have what we need.
    if not os.path.exists(os.path.join(PARENTS_RESULTS, "meta.json")):
        LOGGER.info("No scan metadata downloaded, aborting.")
        return

    LOGGER.info(f"[{date}] Loading data into Pulse.")
    result = processing.run(date)
    LOGGER.info(f"[{date}] Data now loaded into Pulse.")
