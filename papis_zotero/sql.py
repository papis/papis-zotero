import glob
import logging
import os
import re
import shutil
import sqlite3
from typing import Any, Dict, List

from papis_zotero.utils import to_sql_tuple

logger = logging.getLogger("papis.{}".format(__name__))

# Zotero item types to be excluded.
ZOTERO_EXCLUDED_TYPES = ["attachment", "note"]
ZOTERO_EXCLUDED_TYPES_SQL = to_sql_tuple(ZOTERO_EXCLUDED_TYPES)

# dictionary of Zotero attachments mimetypes to be included
# NOTE: mapped onto their respective extension to be used in papis
ZOTERO_INCLUDED_MIMETYPE_MAP = {
    "application/vnd.ms-htmlhelp": "chm",
    "image/vnd.djvu": "djvu",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/epub+zip": "epub",
    "application/octet-stream": "fb2",
    "application/x-mobipocket-ebook": "mobi",
    "application/pdf": "pdf",
    "text/rtf": "rtf",
    "application/zip": "zip",
}
ZOTERO_INCLUDED_MIMETYPE_MAP_SQL = to_sql_tuple(ZOTERO_INCLUDED_MIMETYPE_MAP)

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
      itemData.itemID = {itemID} AND
      fields.fieldID = itemData.fieldID AND
      itemDataValues.valueID = itemData.valueID
    """
    field_cursor = connection.cursor()
    field_cursor.execute(item_field_query.format(itemID=item_id))
    fields = {}
    for field_row in field_cursor:
        field_name = ZOTERO_TO_PAPIS_FIELD_MAP.get(field_row[0], field_row[0])
        field_value = field_row[1]
        fields[field_name] = field_value
    return fields


def get_creators(connection: sqlite3.Connection, item_id: str) -> Dict[str, List[str]]:
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
      itemCreators.itemID = {item_id} AND
      creatorTypes.creatorTypeID = itemCreators.creatorTypeID AND
      creators.creatorID = itemCreators.creatorID
    ORDER BY
      creatorTypes.creatorType,
      itemCreators.orderIndex
    """.format(item_id=item_id)
    creator_cursor = connection.cursor()
    creator_cursor.execute(item_creator_query)

    creators: Dict[str, Any] = {}
    for creator_row in creator_cursor:
        creator_name = creator_row[0]
        creator_name_list = "{}_list".format(creator_name)
        given_name = creator_row[1]
        surname = creator_row[2]

        current_creators = creators.get(creator_name, "")
        if current_creators != "":
            current_creators += " and "

        current_creators += "{}, {}".format(surname, given_name)
        creators[creator_name] = current_creators

        current_creators_list = creators.get(creator_name_list, [])
        current_creators_list.append(
            {"given_name": given_name, "surname": surname}
        )
        creators[creator_name_list] = current_creators_list

    return creators


def get_files(connection: sqlite3.Connection,
              item_id: str,
              item_key: str,
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
      itemAttachments.parentItemID = {item_id} AND
      itemAttachments.contentType IN {mimetypes} AND
      items.itemID = itemAttachments.itemID
    """.format(item_id=item_id, mimetypes=ZOTERO_INCLUDED_MIMETYPE_MAP_SQL)

    attachment_cursor = connection.cursor()
    attachment_cursor.execute(item_attachment_query)

    files = []
    for attachement_row in attachment_cursor:
        key = attachement_row[0]
        path = attachement_row[1]
        mime = attachement_row[2]

        try:
            # NOTE: a single file is assumed in the attachment's folder
            # to avoid using path, which may contain invalid characters
            import_path = glob.glob(os.path.join(input_path, "storage", key, "*.*"))[0]

            extension = os.path.splitext(import_path)[1]
            file_name = "{}.{}".format(key, extension)
            local_path = os.path.join(output_path, item_key, file_name)

            shutil.copyfile(import_path, local_path)
            files.append(file_name)
        except Exception:
            logger.error("Failed to export attachment '%s': '%s' (%s).",
                         key, path, mime)

    return {"files": files}


def get_tags(connection: sqlite3.Connection, item_id: str) -> Dict[str, str]:
    item_tag_query = """
    SELECT
      tags.name
    FROM
      tags,
      itemTags
    WHERE
      itemTags.itemID = {item_id} AND
      tags.tagID = itemTags.tagID
    """.format(item_id=item_id)

    tag_cursor = connection.cursor()
    tag_cursor.execute(item_tag_query)

    return {"tags": ZOTERO_TAG_DELIMITER.join(str(row[0]) for row in tag_cursor)}


def get_collections(connection: sqlite3.Connection,
                    item_id: str) -> Dict[str, List[str]]:
    item_collection_query = """
      SELECT
        collections.collectionName
      FROM
        collections,
        collectionItems
      WHERE
        collectionItems.itemID = {itemID} AND
        collections.collectionID = collectionItems.collectionID
    """
    collection_cursor = connection.cursor()
    collection_cursor.execute(item_collection_query.format(itemID=item_id))

    return {"project": [row[0] for row in collection_cursor]}


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
        itemType.typeName NOT IN {excluded}
      ORDER BY
        item.itemID
    """.format(excluded=ZOTERO_EXCLUDED_TYPES_SQL)

    cursor.execute(items_count_query)
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
        itemType.typeName NOT IN {excluded}
      ORDER BY
        item.itemID
    """.format(excluded=ZOTERO_EXCLUDED_TYPES_SQL)
    cursor.execute(items_query)

    current_item = 0
    for row in cursor:
        current_item += 1
        item_id = row[0]
        item_type = ZOTERO_TO_PAPIS_TYPE_MAP.get(row[1], row[1])
        item_key = row[2]
        date_added = row[3]
        date_modified = row[4]
        client_date_modified = row[5]
        logger.info("[%4d / %4d] Exporting item '%s'.",
                    current_item, items_count, item_key)

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
        item.update(get_files(connection, item_id, item_key,
                              input_path=input_path, output_path=output_path))

        item.update({"ref": ref})

        with open(os.path.join(path, "info.yaml"), "w+") as item_file:
            yaml.dump(item, item_file, default_flow_style=False)

    logger.info("Finished exporting from '%s'.", input_path)
    logger.info("Exported files can be found at '%s'.", output_path)
