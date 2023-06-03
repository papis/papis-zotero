import glob
import os
import re
import shutil
import sqlite3
from typing import Any, Dict, List

import papis.bibtex
import papis.strings
import papis.document
import papis.logging

logger = papis.logging.get_logger(__name__)

# Zotero item types to be excluded.
ZOTERO_EXCLUDED_TYPES = ("attachment", "note")

# Zotero excluded fields
ZOTERO_EXCLUDED_FIELDS = frozenset({
    "accessDate",
})

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
    "ISSN": "issn",
}

# separator between multiple tags
# FIXME: this should be handled by papis
ZOTERO_TAG_DELIMITER = " "


def get_fields(connection: sqlite3.Connection, item_id: str) -> Dict[str, str]:
    """
    :arg item_id: an identifier for the item to query.
    :returns: a dictionary mapping fields to their values, e.g. ``"doi"``.
    """

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
        if name in ZOTERO_EXCLUDED_FIELDS:
            continue

        name = ZOTERO_TO_PAPIS_FIELD_MAP.get(name, name)
        fields[name] = value

    date = fields.pop("date", None)
    if date is not None:
        from datetime import datetime

        try:
            d = datetime.strptime(date.split(" ")[0][:-3], "%Y-%m")
            fields["year"] = d.year
            fields["month"] = d.month
        except Exception as exc:
            logger.error("Failed to parse date.", exc_info=exc)
            fields["date"] = date

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
              input_path: str, output_path: str) -> List[str]:
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
        import_paths = glob.glob(os.path.join(input_path, "storage", key, "*.*"))
        if not import_paths:
            continue

        import_path = import_paths[0]
        _, ext = os.path.splitext(import_path)
        file_name = "{}{}".format(key, ext)
        local_path = os.path.join(output_path, item_key, file_name)

        try:
            shutil.copyfile(import_path, local_path)
            files.append(file_name)
        except Exception as exc:
            logger.error("Failed to export attachment '%s': '%s' (%s).", key,
                         path, mime, exc_info=exc)

    return files


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

    tags = ZOTERO_TAG_DELIMITER.join(str(row[0]) for row in cursor)
    return {"tags": tags} if tags else {}


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

    project = [name for name, in cursor]
    return {"project": project} if project else {}


def add_from_sql(input_path: str, output_path: str) -> None:
    """
    :param inpath: path to zotero SQLite database "zoter.sqlite" and
        "storage" to be imported
    :param outpath: path where all items will be exported to created if not
        existing
    """
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

    import yaml
    import papis.yaml

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
        dateAdded
      FROM
        items item,
        itemTypes itemType
      WHERE
        itemType.itemTypeID = item.itemTypeID AND
        itemType.typeName NOT IN ({})
      ORDER BY
        item.itemID
    """.format(",".join(["?"] * len(ZOTERO_EXCLUDED_TYPES)))

    from datetime import datetime
    cursor.execute(items_query, ZOTERO_EXCLUDED_TYPES)
    for i, (item_id, item_type, item_key, date_added) in enumerate(cursor):
        path = os.path.join(output_path, item_key)
        if not os.path.exists(path):
            os.makedirs(path)

        # convert fields
        date_added = (
            datetime.strptime(date_added, "%Y-%m-%d %H:%M:%S")
            .strftime(papis.strings.time_format))
        item_type = ZOTERO_TO_PAPIS_TYPE_MAP.get(item_type, item_type)
        logger.info("[%4d / %4d] Exporting item '%s'.", i, items_count, item_key)

        # get Zotero metadata
        fields = get_fields(connection, item_id)
        files = get_files(connection,
                          item_id,
                          item_key,
                          input_path=input_path,
                          output_path=output_path)

        item = {"type": item_type, "time-added": date_added, "files": files}
        item.update(fields)
        item.update(get_creators(connection, item_id))
        item.update(get_tags(connection, item_id))
        item.update(get_collections(connection, item_id))

        # create a reference
        ref = None
        extra = item.get("extra", None)
        if extra:
            matches = re.search(r".*Citation Key: (\w+)", extra)
            if matches:
                ref = matches.group(1)

        if ref is None:
            from papis.bibtex import create_reference
            ref = create_reference(item)

        item["ref"] = ref
        logger.info("Exporting item '%s' with reference '%s' to folder '%s'.",
                    item_key, ref, path)

        # write out the info file
        # FIXME: should use papis.yaml.data_to_yaml, but blocked by
        #   https://github.com/papis/papis/pull/571
        with open(os.path.join(path, "info.yaml"), "w+", encoding="utf-8") as fd:
            yaml.dump(item,
                      stream=fd,
                      allow_unicode=True,
                      default_flow_style=False)

    logger.info("Finished exporting from '%s'.", input_path)
    logger.info("Exported files can be found at '%s'.", output_path)
