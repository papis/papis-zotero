"""Start a web server listening on port 23119. This server is
compatible with the `zotero connector`. This means that if zotero is
*not* running, you can have items from your web browser added directly
into papis.

"""

import json
import http.server
from typing import Any, Dict, List

import papis.api
import papis.crossref
import papis.document
import papis.commands.add
import papis.logging

import papis_zotero.utils

logger = papis.logging.get_logger(__name__)

# NOTE: 5.0.75 was released in October 8, 2019 at the same time with Python 3.8
ZOTERO_CONNECTOR_API_VERSION = 2
ZOTERO_VERSION = "5.0.75"
ZOTERO_PORT = 23119

_k = papis.document.KeyConversionPair

ZOTERO_TO_PAPIS_CONVERSIONS = [
    _k("creators", [{
        "key": "author_list",
        "action": lambda a: zotero_authors(a)
        }]),
    _k("tags", [{
        "key": "tags",
        "action": lambda t: "; ".join(tag["tag"] for tag in t)
        }]),
    _k("date", [
        {"key": "year", "action": lambda d: int(d.split("-")[0])},
        {"key": "month", "action": lambda d: int(d.split("-")[1])},
        ]),
    _k("archiveID", [
        {"key": "eprint", "action": lambda a: a.split(":")[-1]}
        ]),
    _k("type", [
        {"key": "type", "action": papis_zotero.utils.ZOTERO_TO_PAPIS_TYPES.get}
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

    for foreign_key, key in papis_zotero.utils.ZOTERO_TO_PAPIS_FIELDS.items():
        if foreign_key in item:
            item[key] = item.pop(foreign_key)

    item = papis.document.keyconversion_to_data(ZOTERO_TO_PAPIS_CONVERSIONS,
                                                item,
                                                keep_unknown_keys=True)
    for key in papis_zotero.utils.ZOTERO_EXCLUDED_FIELDS:
        if key in item:
            del item[key]

    # try to get information from Crossref as well
    if "doi" in item:
        try:
            crossref_data = papis.crossref.doi_to_data(item["doi"])
            crossref_data.pop("title", None)
            logger.info("Updating document with data from Crossref.")
        except ValueError:
            crossref_data = {}

        item.update(crossref_data)

    logger.info("Document metadata: %s", item)
    return item


def download_zotero_attachments(attachments: List[Dict[str, str]]) -> List[str]:
    files = []

    for attachment in attachments:
        logger.info("Checking attachment: %s", attachment)

        mime = str(attachment.get("mimeType"))
        if mime not in papis_zotero.utils.ZOTERO_SUPPORTED_MIMETYPES_TO_EXTENSION:
            continue

        url = attachment["url"]
        extension = papis_zotero.utils.ZOTERO_SUPPORTED_MIMETYPES_TO_EXTENSION[mime]
        logger.info("Downloading file (%s): '%s'.", mime, url)

        filename = papis_zotero.utils.download_document(
            url, expected_document_extension=extension)
        if filename is not None:
            files.append(filename)

    return files


class PapisRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info(fmt, *args)

    def set_zotero_headers(self) -> None:
        self.send_header("X-Zotero-Version", ZOTERO_VERSION)
        self.send_header("X-Zotero-Connector-API-Version",
                         str(ZOTERO_CONNECTOR_API_VERSION))
        self.end_headers()

    def read_input(self) -> bytes:
        length = int(self.headers["content-length"])
        return self.rfile.read(length)

    def do_GET(self) -> None:  # noqa: N802
        logger.info("Received GET request at '%s'", self.path)
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

    def do_POST(self) -> None:  # noqa: N802
        logger.info("Received POST request at '%s'", self.path)
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
        papis_library = papis.api.get_lib_name()

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

        logger.info("Response: %s", data)
        for item in data["items"]:
            attachments = item.get("attachments", [])
            if attachments:
                files = download_zotero_attachments(attachments)
            else:
                logger.info("Document has no attachments.")
                files = []

            papis_item = zotero_data_to_papis_data(item)
            logger.info("Adding paper to papis.")
            papis.commands.add.run(files, data=papis_item)

        self.send_response(201)
        self.set_zotero_headers()

        self.wfile.write(rawinput)

    def handle_post_snapshot(self) -> None:
        logger.error("Snapshot not implemented!")
        self.send_response(201)
        self.set_zotero_headers()
