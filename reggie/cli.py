#!/usr/bin/env python

"""
Click-based CLI for Reggie processing.
"""

from reggie.configs.configs import Config
from reggie.ingestion.preprocessor.state_router import state_router
from reggie.main import convert_voter_file
import datetime
import click


@click.command(help="convert a non-standard voter file")
@click.option(
    "--state", required=True, default=None, help="U.S. state name: e.g. florida"
)
@click.option(
    "--local_file",
    required=True,
    default=None,
    help="location and name of file: e.g. 'FL_2019-01-01.zip'",
)
@click.option(
    "--file_date",
    required=True,
    default=None,
    help="date of voter file in format 'YYYY-MM-DD'",
)
@click.option("--write_file", required=False, default=True, is_flag=True)
def convert_cli(state, local_file, file_date, write_file):
    if file_date is None:
        file_date = datetime.datetime.today().date().isoformat()
    convert_voter_file(
        state=state, local_file=local_file, file_date=file_date, write_file=write_file
    )


if __name__ == "__main__":
    convert_cli()
