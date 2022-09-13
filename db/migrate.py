import sys
from alembic import command
from alembic import context
from alembic.config import Config
import click


@click.command()
@click.option(
    '--db-url',
    '-d',
    default='postgresql://root:root@database/flickr_images',
)
@click.option(
    '--alembic-ini-path',
    '-a',
    default='alembic.ini'
)
def run_migrations(db_url, alembic_ini_path):
    alembic_config = Config(alembic_ini_path)
    alembic_config.attributes["db_url"] = db_url
    command.upgrade(alembic_config, "head")


def main():
    run_migrations(auto_envvar_prefix="FLICKR_APP")
    return 0


if __name__ == '__main__':
    sys.exit(main())
