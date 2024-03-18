from functools import partial
import os
import http.server
from typing import List, Optional, Tuple

import click

import papis.config
import papis.logging
import papis_zotero.server

logger = papis.logging.get_logger(__name__)


@click.group("zotero")                  # type: ignore[arg-type]
@click.help_option("-h", "--help")
def main() -> None:
    """Zotero interface for papis."""


@main.command("serve")                  # type: ignore[arg-type]
@click.help_option("-h", "--help")
@click.option("--port",
              help="Port to listen to",
              default=papis_zotero.server.ZOTERO_PORT,
              type=int)
@click.option("--address", help="Address to bind", default="localhost")
@click.option(
    "-s", "--set", "set_list",
    help="Set imported document metadata as <key> <value>. Can be used multiple times.",
    multiple=True,
    type=(str, str))
def serve(address: str, port: int, set_list: List[Tuple[str, str]],) -> None:
    """Start a ``zotero-connector`` server."""

    logger.warning("The 'zotero-connector' server is experimental. "
                   "Please report bugs and improvements at "
                   "https://github.com/papis/papis-zotero/issues.")

    server_address = (address, port)
    request_handler = partial(papis_zotero.server.PapisRequestHandler, set_list)
    try:
        httpd = http.server.HTTPServer(server_address, request_handler)
    except OSError:
        logger.error(
            "Address '%s:%s' is already in use. This may be because you "
            "have the Zotero application open.", address, port)
        logger.error("papis zotero serve requires to be the only one "
                     "listening on that port. Zotero must quit before this "
                     "command can be used!")
        return

    logger.info("Starting server in address https://%s:%s.", address, port)
    logger.info("Press Ctrl-C to exit.")

    httpd.serve_forever()


@main.command("import")                 # type: ignore[arg-type]
@click.help_option("-h", "--help")
@click.option(
    "-f",
    "--from-bibtex",
    "from_bibtex",
    help="Import Zotero library from a BibTeX dump, the files fields in "
    "the BibTeX files should point to valid paths",
    default=None,
    type=click.Path(exists=True))
@click.option("-s",
              "--from-sql",
              "--from-sql-folder",
              "from_sql",
              help="Path to the FOLDER where the 'zotero.sqlite' file resides",
              default=None,
              type=click.Path(exists=True))
@click.option("-o",
              "--outfolder",
              help="Folder to save the imported library",
              default=None,
              type=str)
@click.option("--link",
              help="Whether to link the pdf files or copy them",
              is_flag=True,
              default=False)
def do_importer(from_bibtex: Optional[str], from_sql: Optional[str],
                outfolder: Optional[str], link: bool) -> None:
    """Import zotero libraries into papis libraries."""
    import papis_zotero.bibtex
    import papis_zotero.sql

    if outfolder is None:
        outfolder = papis.config.get_lib_dirs()[0]

    if not os.path.exists(outfolder):
        os.makedirs(outfolder)

    if from_bibtex is not None:
        import papis_zotero.bibtex
        papis_zotero.bibtex.add_from_bibtex(from_bibtex, outfolder, link)
    elif from_sql is not None:
        import papis_zotero.sql
        try:
            papis_zotero.sql.add_from_sql(from_sql, outfolder, link)
        except Exception as exc:
            logger.error("Failed to import from file: %s",
                         from_sql,
                         exc_info=exc)
    else:
        logger.error("Either '--from-bibtex' or '--from-sql-folder' should be "
                     "passed to import from Zotero.")
