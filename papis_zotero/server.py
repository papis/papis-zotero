"""Start a web server listening for Zotero.

This server is compatible with the "Zotero connector". This means that if Zotero
is *not* running, you can have items from your web browser added directly
into Papis.
"""

import http.server
import json
from functools import lru_cache as cache
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import papis.logging

if TYPE_CHECKING:
    from papis.document import KeyConversionPair

logger = papis.logging.get_logger(__name__)

# NOTE: 5.0.75 was released in October 8, 2019 at the same time with Python 3.8
ZOTERO_CONNECTOR_API_VERSION = 2
ZOTERO_VERSION = "5.0.75"
ZOTERO_PORT = 23119


@cache
def _zotero_key_conversions() -> "List[KeyConversionPair]":
    from papis.document import KeyConversionPair

    from papis_zotero.utils import ZOTERO_TO_PAPIS_TYPES

    return [
        KeyConversionPair("creators", [{
            "key": "author_list",
            "action": lambda a: zotero_authors(a)  # noqa: PLW0108
            }]),
        KeyConversionPair("tags", [{
            "key": "tags",
            "action": lambda t: [tag["tag"] for tag in t]
            }]),
        KeyConversionPair("date", [
            {"key": "year", "action": lambda d: int(d.split("-")[0])},
            {"key": "month", "action": lambda d: int(d.split("-")[1])},
            ]),
        KeyConversionPair("archiveID", [
            {"key": "eprint", "action": lambda a: a.split(":")[-1]}
            ]),
        KeyConversionPair("type", [
            {"key": "type", "action": ZOTERO_TO_PAPIS_TYPES.get}
            ]),
    ]


def zotero_authors(creators: List[Dict[str, str]]) -> List[Dict[str, str]]:
    authors = []
    for creator in creators:
        if creator["creatorType"] != "author":
            continue

        authors.append({
            "given": creator["firstName"],
            "family": creator["lastName"],
        })

    return authors


def zotero_data_to_papis_data(item: Dict[str, Any]) -> Dict[str, Any]:
    item.pop("id", None)
    item.pop("attachments", None)
    item.pop("html", None)
    item.pop("detailedCookies", None)
    item.pop("uri", None)
    item.pop("sessionID", None)

    if not item.get("referrer"):
        item.pop("referrer", None)

    from papis_zotero.utils import ZOTERO_EXCLUDED_FIELDS, ZOTERO_TO_PAPIS_FIELDS

    for foreign_key, key in ZOTERO_TO_PAPIS_FIELDS.items():
        if foreign_key in item:
            item[key] = item.pop(foreign_key)

    from papis.document import keyconversion_to_data
    item = keyconversion_to_data(
        _zotero_key_conversions(), item,
        keep_unknown_keys=True)

    for key in ZOTERO_EXCLUDED_FIELDS:
        if key in item:
            del item[key]

    # try to get information from Crossref as well
    if "doi" in item:
        from papis.crossref import doi_to_data
        try:
            crossref_data = doi_to_data(item["doi"])
            crossref_data.pop("title", None)
            logger.info("Updating document with data from Crossref.")
        except ValueError:
            crossref_data = {}

        item.update(crossref_data)

    logger.info("Document metadata: %s.", item)
    return item


def download_zotero_attachments(attachments: List[Dict[str, str]]) -> List[str]:
    from papis_zotero.utils import (
        ZOTERO_SUPPORTED_MIMETYPES_TO_EXTENSION,
        download_document,
    )

    files = []
    for attachment in attachments:
        logger.info("Checking attachment: %s.", attachment)

        mime = str(attachment.get("mimeType"))
        if mime not in ZOTERO_SUPPORTED_MIMETYPES_TO_EXTENSION:
            continue

        url = attachment["url"]
        extension = ZOTERO_SUPPORTED_MIMETYPES_TO_EXTENSION[mime]
        logger.info("Downloading file (%s): '%s'.", mime, url)

        filename = download_document(url, expected_document_extension=extension)
        if filename is not None:
            files.append(filename)

    return files


class PapisRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, set_list: List[Tuple[str, str]], request: Any,
                 client_address: Any, server: Any) -> None:
        self.set_list = set_list
        super().__init__(request, client_address, server)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: PLR6301
        logger.info(fmt, *args)

    def set_zotero_headers(self) -> None:
        self.send_header("X-Zotero-Version", ZOTERO_VERSION)
        self.send_header("X-Zotero-Connector-API-Version",
                         str(ZOTERO_CONNECTOR_API_VERSION))
        self.end_headers()

    def read_input(self) -> bytes:
        length = int(self.headers["content-length"])
        return self.rfile.read(length)

    def do_GET(self) -> None:
        logger.info("Received GET request at '%s'.", self.path)
        if self.path == "/connector/ping":
            self.handle_get_ping()

    def handle_get_ping(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.set_zotero_headers()
        response = """\
        <!DOCTYPE html>
        <html>
            <head>
                <title>Zotero Connector Server is Available</title>
            </head>
            <body>
                Zotero Connector Server is Available
            </body>
        </html>
        """

        self.wfile.write(response.encode("utf-8"))

    def do_POST(self) -> None:
        logger.info("Received POST request at '%s'.", self.path)
        if self.path == "/connector/ping":
            self.handle_post_ping()
        elif self.path == "/connector/getSelectedCollection":
            self.handle_post_collection()
        elif self.path == "/connector/saveSnapshot":
            self.handle_post_snapshot()
        elif self.path == "/connector/saveItems":
            self.handle_post_add()

    def handle_post_ping(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.set_zotero_headers()
        response = json.dumps({"prefs": {"automaticSnapshots": True}})

        self.wfile.write(response.encode("utf-8"))

    def handle_post_collection(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.set_zotero_headers()

        from papis.api import get_lib_name
        papis_library = get_lib_name()

        response = json.dumps({
            "libraryID": 1,
            "libraryName": papis_library,
            "libraryEditable": True,
            "editable": True,
            "id": None,
            "name": papis_library
        })

        self.wfile.write(response.encode("utf-8"))

    def handle_post_add(self) -> None:
        logger.info("Adding paper from the Zotero Connector.")
        rawinput = self.read_input()
        data = json.loads(rawinput.decode("utf-8"))

        from papis.commands.add import run as add

        logger.info("Response: %s.", data)
        for item in data["items"]:
            attachments = item.get("attachments", [])
            if attachments:
                files = download_zotero_attachments(attachments)
            else:
                logger.info("Document has no attachments.")
                files = []

            papis_item = zotero_data_to_papis_data(item)
            if self.set_list:
                papis_item.update(self.set_list)

            logger.info("Adding paper to Papis.")
            add(files, data=papis_item)

        self.send_response(201)
        self.set_zotero_headers()

        self.wfile.write(rawinput)

    def handle_post_snapshot(self) -> None:
        import datetime
        import tempfile
        import urllib.parse

        rawinput = self.read_input()
        try:
            data = json.loads(rawinput.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Failed to decode data from the Zotero connector.", exc_info=e)

        html_template = """
        <!DOCTYPE html>
        <html>
            {html}
        </html>
        """
        full_html = html_template.lstrip().format(**data)
        temp_html = tempfile.mktemp(suffix=".html")
        logger.debug("Writing temporary HTML: '%s'.", temp_html)
        with open(temp_html, mode="w", encoding="utf-8") as f:
            f.write(full_html)

        current_date = datetime.datetime.now()
        data["date"] = data.get("date", current_date.isoformat())

        url = urllib.parse.urlparse(data["url"])
        data["author"] = url.hostname

        papis_item = zotero_data_to_papis_data(data)

        logger.info("Adding snapshot to Papis.")

        from papis.commands.add import run as add
        from papis.config import getstring
        add([temp_html], data=papis_item, folder_name=getstring("add-folder-name"))

        self.send_response(201)
        self.set_zotero_headers()
