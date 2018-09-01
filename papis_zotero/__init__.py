import click
import papis.api

import logging
import http.server
import papis_zotero.server


@click.group()
@click.help_option('-h', '--help')
def main():
    logger = logging.getLogger("papis:zotero")
    logger.info("library '{0}'".format(papis.api.get_lib()))


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


if __name__ == "__main__":
    main()
