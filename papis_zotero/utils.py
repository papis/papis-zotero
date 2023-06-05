import os
import re

# Zotero item types to be excluded when converting to papis
ZOTERO_EXCLUDED_ITEM_TYPES = ("attachment", "note")

# Zotero excluded fields
ZOTERO_EXCLUDED_FIELDS = frozenset({
    "accessDate",
    "id",
    "shortTitle",
    "attachements",
})

# dictionary of Zotero attachments mimetypes to be included
# NOTE: mapped onto their respective extension to be used in papis
ZOTERO_SUPPORTED_MIMETYPES_TO_EXTENSION = {
    "application/vnd.ms-htmlhelp": "chm",
    "image/vnd.djvu": "djvu",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    "docx",
    "application/epub+zip": "epub",
    "application/octet-stream": "fb2",
    "application/x-mobipocket-ebook": "mobi",
    "application/pdf": "pdf",
    "text/rtf": "rtf",
    "application/zip": "zip",
}

# dictionary translating from zotero to papis field names
ZOTERO_TO_PAPIS_FIELDS = {
    "abstractNote": "abstract",
    "publicationTitle": "journal",
    "DOI": "doi",
    "itemType": "type",
    "ISBN": "isbn",
    "ISSN": "issn",
}


def is_pdf(filepath: str) -> bool:
    if not os.path.exists(filepath):
        return False

    with open(filepath, "rb") as fd:
        magic = fd.read(8)

    return re.match(r"%PDF-.\..", magic.decode()) is not None
