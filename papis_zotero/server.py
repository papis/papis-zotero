"""Start a web server listening on port 23119. This server is
compatible with the `zotero connector`. This means that if zotero is
*not* running, you can have items from your web browser added directly
into papis.

"""

import http.server
import json
import logging
import re
import tempfile
import urllib.request
import urllib.error

from typing import Any, Dict

import papis.api
import papis.config
import papis.crossref
import papis.document

import papis_zotero.utils

logger = logging.getLogger("papis:zotero:server")
logging.basicConfig(filename="", level=logging.INFO)

connector_api_version = 2
zotero_version = "5.0.25"
zotero_port = 23119

papis_translation = {
    "abstractNote": "abstract",
    "publicationTitle": "journal",
    "DOI": "doi",
    "itemType": "type",
    "ISBN": "isbn",
}


def zotero_data_to_papis_data(item: Dict[str, Any]) -> Dict[str, Any]:
    data = {}

    for key in papis_translation.keys():
        if item.get(key):
            data[papis_translation[key]] = item.get(key)
            del item[key]

    # Maybe zotero has good tags
    if isinstance(item.get("tags"), list):
        try:
            data["tags"] = " ".join(item["tags"])
        except Exception:
            pass
        del item["tags"]

    if item.get("id"):
        del item["id"]

    if item.get("attachments"):
        del item["attachments"]

    # still get all information from zotero
    data.update(item)

    # and also get all infromation from crossref
    doi = data.get("doi")
    if doi is not None:
        crossref_data = papis.crossref.doi_to_data(str(doi))
        if crossref_data.get("title"):
            del crossref_data["title"]
        logger.info("Updating also from crossref")
        data.update(crossref_data)

    return data


class PapisRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info(fmt % args)

    def set_zotero_headers(self) -> None:
        self.send_header(
            "X-Zotero-Version",
            zotero_version
        )
        self.send_header(
            "X-Zotero-Connector-API-Version",
            str(connector_api_version)
        )
        self.end_headers()

    def read_input(self) -> bytes:
        length = int(self.headers["content-length"])
        return self.rfile.read(length)

    def pong(self, POST: bool = True) -> None:  # noqa: N803
        global logger
        logger.info("pong!")
        # Pong must respond to ping on both GET and POST
        # It must accepts application/json and text/plain
        if not POST:  # GET
            logger.debug("GET request")
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
        else:  # POST
            logger.debug("POST request")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.set_zotero_headers()
            response = json.dumps({"prefs": {"automaticSnapshots": True}})

        self.wfile.write(bytes(response, "utf8"))

    def papis_collection(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.set_zotero_headers()
        papis_library = papis.api.get_lib_name()
        response = json.dumps({
            "libraryID": 1,
            "libraryName": papis_library,
            # I'm not aware of a read-only papis mode
            "libraryEditable": True,
            # collection-level parameters
            "editable": True,
            # collection-level
            "id": None,
            # collection if collection, else library
            "name": papis_library
        })
        self.wfile.write(bytes(response, "utf8"))

    def add(self) -> None:
        logger.info("Adding paper from zotero connector")
        rawinput = self.read_input()
        data = json.loads(rawinput.decode("utf8"))

        for item in data["items"]:
            files = []
            if item.get("attachments") and len(item.get("attachments")) > 0:
                for attachment in item.get("attachments"):
                    mime = str(attachment.get("mimeType"))
                    logger.info(
                        "Checking attachment (mime {0})".format(mime)
                    )
                    if re.match(r".*pdf.*", mime):
                        url = attachment.get("url")
                        logger.info("Downloading pdf '{0}'".format(url))
                        try:
                            pdfbuffer = urllib.request.urlopen(url).read()
                        except urllib.error.HTTPError:
                            logger.error(
                                "Error downloading pdf, probably you do not"
                                "have the rights for the journal."
                            )
                            continue

                        pdfpath = tempfile.mktemp(suffix=".pdf")
                        logger.info("Saving pdf in '{0}'".format(pdfpath))

                        with open(pdfpath, "wb+") as fd:
                            fd.write(pdfbuffer)

                        if papis_zotero.utils.is_pdf(pdfpath):
                            files.append(pdfpath)
                        else:
                            logger.error(
                                "File retrieved does not appear to be a pdf"
                                "So no file will be saved..."
                            )
            else:
                logger.warning("Document has no attachments")

            papis_item = zotero_data_to_papis_data(item)
            if len(files) == 0:
                logger.warning("Not adding any attachments...")
            logger.info("Adding paper")
            papis.commands.add.run(files, data=papis_item)

        self.send_response(201)  # Created
        self.set_zotero_headers()
        # return the JSON data back
        self.wfile.write(rawinput)

    def snapshot(self) -> None:
        logger.warning("Snapshot not implemented")
        self.send_response(201)
        self.set_zotero_headers()

    def do_POST(self) -> None:      # noqa: N802
        if self.path == "/connector/ping":
            self.pong()
        elif self.path == "/connector/getSelectedCollection":
            self.papis_collection()
        elif self.path == "/connector/saveSnapshot":
            self.snapshot()
        elif self.path == "/connector/saveItems":
            self.add()

    def do_GET(self) -> None:       # noqa: N802
        if self.path == "/connector/ping":
            self.pong(POST=False)
