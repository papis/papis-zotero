import click
import os
import papis.api

import logging
import http.server
import papis_zotero.server


@click.group('zotero')
@click.help_option('-h', '--help')
def main():
    """
    Zotero interface for papis
    """
    logger = logging.getLogger("papis:zotero")


@main.command('serve')
@click.help_option('-h', '--help')
@click.option(
    "--port",
    help="Port to listen to",
    default=papis_zotero.server.zotero_port,
    type=int
)
@click.option(
    "--address",
    help="Address to bind",
    default="localhost"
)
def serve(address, port):
    """Start a zotero-connector server"""
    global logger
    server_address = (address, port)
    httpd = http.server.HTTPServer(
        server_address,
        papis_zotero.server.PapisRequestHandler
    )
    httpd.serve_forever()


@main.command('import')
@click.help_option('-h', '--help')
@click.option(
    '-f', '--from-bibtex', 'from_bibtex',
    help='Import zotero library from a bibtex dump, the files fields in '
         'the bibtex files should point to valid paths',
    default=None,
    type=click.Path(exists=True)
)
@click.option(
    '-s', '--from-sql', 'from_sql',
    help='Path to the FOLDER where the "zotero.sqlite" file resides',
    default=None,
    type=click.Path(exists=True)
)
@click.option(
    '-o', '--outfolder',
    help='Folder to save the imported library',
    type=str,
    required=True
)
@click.option(
    '--link',
    help='Wether to link the pdf files or copy them',
    default=None
)
def do_importer(from_bibtex, from_sql, outfolder, link):
    """Import zotero libraries into papis libraries
    """
    import papis_zotero.bibtex
    import papis_zotero.sql
    if not os.path.exists(outfolder):
        os.makedirs(outfolder)
    if from_bibtex is not None:
        papis_zotero.bibtex.add_from_bibtex(
            from_bibtex, outfolder, link
        )
    elif from_sql is not None:
        papis_zotero.sql.add_from_sql(
            from_sql, outfolder
        )


if __name__ == "__main__":
    main()
