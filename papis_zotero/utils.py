import tempfile
from typing import Any, Dict, Optional

import papis.utils
import papis.logging

logger = papis.logging.get_logger(__name__)

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

# TODO: This mapping is copied from 'papis.bibtex.bibtex_type_converter' with
# no changes. It will be available in papis>0.13, so it should be deleted and
# replaced when we can depend on a newer version

ZOTERO_TO_PAPIS_TYPES: Dict[str, str] = {
    # Zotero
    "annotation": "misc",
    "attachment": "misc",
    "audioRecording": "audio",
    "bill": "legislation",
    "blogPost": "online",
    "bookSection": "inbook",
    "case": "jurisdiction",
    "computerProgram": "software",
    "conferencePaper": "inproceedings",
    "dictionaryEntry": "misc",
    "document": "article",
    "email": "online",
    "encyclopediaArticle": "article",
    "film": "video",
    "forumPost": "online",
    "hearing": "jurisdiction",
    "instantMessage": "online",
    "interview": "article",
    "journalArticle": "article",
    "magazineArticle": "article",
    "manuscript": "unpublished",
    "map": "misc",
    "newspaperArticle": "article",
    "note": "misc",
    "podcast": "audio",
    "preprint": "unpublished",
    "presentation": "misc",
    "radioBroadcast": "audio",
    "statute": "jurisdiction",
    "tvBroadcast": "video",
    "videoRecording": "video",
    "webpage": "online",
    # Others
    "journal": "article",
    "monograph": "book",
}


# TODO: this function is copied from `papis.downloaders.__init__` with no
# changes. It will be available in papis>0.13, so it should be deleted when
# we can depend on a newer version

def download_document(
        url: str,
        expected_document_extension: Optional[str] = None,
        cookies: Optional[Dict[str, Any]] = None,
        ) -> Optional[str]:
    """Download a document from *url* and store it in a local file.

    :param url: the URL of a remote file.
    :param expected_document_extension: an expected file type. If *None*, then
        an extension is guessed from the file contents, but this can also fail.
    :returns: a path to a local file containing the data from *url*.
    """
    if cookies is None:
        cookies = {}

    try:
        with papis.utils.get_session() as session:
            response = session.get(url, cookies=cookies, allow_redirects=True)
    except Exception as exc:
        logger.error("Failed to fetch '%s'.", url, exc_info=exc)
        return None

    if not response.ok:
        logger.error("Could not download document '%s'. (HTTP status: %s %d).",
                     url, response.reason, response.status_code)
        return None

    ext = expected_document_extension
    if ext is None:
        from papis.filetype import guess_content_extension
        ext = guess_content_extension(response.content)
        if not ext:
            logger.warning("Downloaded document does not have a "
                           "recognizable (binary) mimetype: '%s'.",
                           response.headers["Content-Type"])

    ext = ".{}".format(ext) if ext else ""
    with tempfile.NamedTemporaryFile(
            mode="wb+",
            suffix=ext,
            delete=False) as f:
        f.write(response.content)

    return f.name
