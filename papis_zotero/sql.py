import glob
import os
import re
import shutil
import sqlite3
from typing import Any, Dict, List

import papis.document
import papis.logging

logger = papis.logging.get_logger(__name__)

# Zotero item types to be excluded.
ZOTERO_EXCLUDED_TYPES = ("attachment", "note")

# dictionary of Zotero attachments mimetypes to be included
# NOTE: mapped onto their respective extension to be used in papis
ZOTERO_INCLUDED_MIMETYPE_MAP = {
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

# dictionary translating from Zotero to papis type names
ZOTERO_TO_PAPIS_TYPE_MAP = {"journalArticle": "article"}

# dictionary translating from zotero to papis field names
ZOTERO_TO_PAPIS_FIELD_MAP = {
    "abstractNote": "abstract",
    "publicationTitle": "journal",
    "DOI": "doi",
    "itemType": "type",
    "ISBN": "isbn",
}

# seperator between multiple tags
ZOTERO_TAG_DELIMITER = ","


def get_fields(connection: sqlite3.Connection, item_id: str) -> Dict[str, str]:
    item_field_query = """
    SELECT
      fields.fieldName,
      itemDataValues.value
    FROM
      fields,
      itemData,
      itemDataValues
    WHERE
      itemData.itemID = ? AND
      fields.fieldID = itemData.fieldID AND
      itemDataValues.valueID = itemData.valueID
    """
    cursor = connection.cursor()
    cursor.execute(item_field_query, (item_id,))

    fields = {}
    for name, value in cursor:
        name = ZOTERO_TO_PAPIS_FIELD_MAP.get(name, name)
        fields[name] = value

    return fields


def get_creators(connection: sqlite3.Connection,
                 item_id: str) -> Dict[str, List[str]]:
    item_creator_query = """
    SELECT
      creatorTypes.creatorType,
      creators.firstName,
      creators.lastName
    FROM
      creatorTypes,
      creators,
      itemCreators
    WHERE
      itemCreators.itemID = ? AND
      creatorTypes.creatorTypeID = itemCreators.creatorTypeID AND
      creators.creatorID = itemCreators.creatorID
    ORDER BY
      creatorTypes.creatorType,
      itemCreators.orderIndex
    """

    cursor = connection.cursor()
    cursor.execute(item_creator_query, (item_id,))

    # gather creators
    creators_by_type: Dict[str, List[Dict[str, str]]] = {}
    for ctype, given_name, family_name in cursor:
        creators_by_type.setdefault(ctype.lower(), []).append({
            "given": given_name,
            "family": family_name,
            })

    # convert to papis format
    result: Dict[str, Any] = {}
    for ctype, creators in creators_by_type.items():
        result[ctype] = papis.document.author_list_to_author({"author_list": creators})
        result[f"{ctype}_list"] = creators

    return result


def get_files(connection: sqlite3.Connection, item_id: str, item_key: str,
              input_path: str, output_path: str) -> Dict[str, List[str]]:
    item_attachment_query = """
    SELECT
      items.key,
      itemAttachments.path,
      itemAttachments.contentType
    FROM
      itemAttachments,
      items
    WHERE
      itemAttachments.parentItemID = ? AND
      itemAttachments.contentType IN ({}) AND
      items.itemID = itemAttachments.itemID
    """.format(",".join(["?"] * len(ZOTERO_INCLUDED_MIMETYPE_MAP)))

    cursor = connection.cursor()
    cursor.execute(
        item_attachment_query,
        (item_id,) + tuple(ZOTERO_INCLUDED_MIMETYPE_MAP))

    files = []
    for key, path, mime in cursor:
        try:
            # NOTE: a single file is assumed in the attachment's folder
            # to avoid using path, which may contain invalid characters
            import_path = glob.glob(
                os.path.join(input_path, "storage", key, "*.*"))[0]

            extension = os.path.splitext(import_path)[1]
            file_name = "{}.{}".format(key, extension)
            local_path = os.path.join(output_path, item_key, file_name)

            shutil.copyfile(import_path, local_path)
            files.append(file_name)
        except Exception:
            logger.error("Failed to export attachment '%s': '%s' (%s).", key,
                         path, mime)

    return {"files": files}


def get_tags(connection: sqlite3.Connection, item_id: str) -> Dict[str, str]:
    item_tag_query = """
    SELECT
      tags.name
    FROM
      tags,
      itemTags
    WHERE
      itemTags.itemID = ? AND
      tags.tagID = itemTags.tagID
    """

    cursor = connection.cursor()
    cursor.execute(item_tag_query, (item_id,))

    return {"tags": ZOTERO_TAG_DELIMITER.join(str(row[0]) for row in cursor)}


def get_collections(connection: sqlite3.Connection,
                    item_id: str) -> Dict[str, List[str]]:
    item_collection_query = """
      SELECT
        collections.collectionName
      FROM
        collections,
        collectionItems
      WHERE
        collectionItems.itemID = ? AND
        collections.collectionID = collectionItems.collectionID
    """
    cursor = connection.cursor()
    cursor.execute(item_collection_query, (item_id,))

    return {"project": [name for name, in cursor]}


def add_from_sql(input_path: str, output_path: str) -> None:
    """
    :param inpath: path to zotero SQLite database "zoter.sqlite" and
        "storage" to be imported
    :param outpath: path where all items will be exported to created if not
        existing
    """
    import yaml

    if not os.path.exists(input_path):
        raise FileNotFoundError(
            "[Errno 2] No such file or directory: '{}'".format(input_path))

    if not os.path.exists(output_path):
        raise FileNotFoundError(
            "[Errno 2] No such file or directory: '{}'".format(output_path))

    zotero_sqlite_file = os.path.join(input_path, "zotero.sqlite")
    if not os.path.exists(zotero_sqlite_file):
        raise FileNotFoundError(
            "No 'zotero.sqlite' file found in '{}'".format(input_path))

    connection = sqlite3.connect(zotero_sqlite_file)
    cursor = connection.cursor()

    items_count_query = """
      SELECT
        COUNT(item.itemID)
      FROM
        items item,
        itemTypes itemType
      WHERE
        itemType.itemTypeID = item.itemTypeID AND
        itemType.typeName NOT IN ({})
      ORDER BY
        item.itemID
    """.format(",".join(["?"] * len(ZOTERO_EXCLUDED_TYPES)))

    cursor.execute(items_count_query, ZOTERO_EXCLUDED_TYPES)
    for row in cursor:
        items_count = row[0]

    items_query = """
      SELECT
        item.itemID,
        itemType.typeName,
        key,
        dateAdded,
        dateModified,
        clientDateModified
      FROM
        items item,
        itemTypes itemType
      WHERE
        itemType.itemTypeID = item.itemTypeID AND
        itemType.typeName NOT IN ({})
      ORDER BY
        item.itemID
    """.format(",".join(["?"] * len(ZOTERO_EXCLUDED_TYPES)))

    cursor.execute(items_query, ZOTERO_EXCLUDED_TYPES)
    for i, (item_id, item_type, item_key,
            date_added, date_modified, client_date_modified) in enumerate(cursor):
        item_type = ZOTERO_TO_PAPIS_TYPE_MAP.get(item_type, item_type)
        logger.info("[%4d / %4d] Exporting item '%s'.", i, items_count, item_key)

        path = os.path.join(output_path, item_key)
        if not os.path.exists(path):
            os.makedirs(path)

        # Get mendeley keys
        fields = get_fields(connection, item_id)
        extra = fields.get("extra", None)
        ref = item_key
        if extra:
            matches = re.search(r".*Citation Key: (\w+)", extra)
            if matches:
                ref = matches.group(1)

        logger.info("Exporting under ref: '%s'.", ref)
        item = {
            "ref": ref,
            "type": item_type,
            "created": date_added,
            "modified": date_modified,
            "modified.client": client_date_modified,
        }
        item.update(fields)
        item.update(get_creators(connection, item_id))
        item.update(get_tags(connection, item_id))
        item.update(get_collections(connection, item_id))
        item.update(
            get_files(connection,
                      item_id,
                      item_key,
                      input_path=input_path,
                      output_path=output_path))

        item.update({"ref": ref})

        with open(os.path.join(path, "info.yaml"), "w+") as item_file:
            yaml.dump(item, item_file, default_flow_style=False)

    logger.info("Finished exporting from '%s'.", input_path)
    logger.info("Exported files can be found at '%s'.", output_path)
