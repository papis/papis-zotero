import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import papis.config
import papis.bibtex
import papis.strings
import papis.document
import papis.logging
import papis.commands.add

import papis_zotero.utils

logger = papis.logging.get_logger(__name__)

# fuzzy date matching
ISO_DATE_RE = re.compile(r"(?P<year>\d{4})-?(?P<month>\d{2})?-?(?P<day>\d{2})?")


ZOTERO_QUERY_ITEM_FIELD = """
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


def get_fields(connection: sqlite3.Connection, item_id: str) -> Dict[str, str]:
    """
    :arg item_id: an identifier for the item to query.
    :returns: a dictionary mapping fields to their values, e.g. ``"doi"``.
    """
    cursor = connection.cursor()
    cursor.execute(ZOTERO_QUERY_ITEM_FIELD, (item_id,))

    # get fields
    fields = {}
    for name, value in cursor:
        if name in papis_zotero.utils.ZOTERO_EXCLUDED_FIELDS:
            continue

        name = papis_zotero.utils.ZOTERO_TO_PAPIS_FIELDS.get(name, name)
        fields[name] = value

    # get year and month from date if available
    date = fields.pop("date", None)
    if date is not None:
        m = ISO_DATE_RE.match(date)
        if m:
            if m.group("year"):
                fields["year"] = int(m.group("year"))
            if m.group("month"):
                fields["month"] = int(m.group("month"))
        else:
            # NOTE: didn't manage to match, so just save the whole date
            fields["date"] = date

    return fields


ZOTERO_QUERY_ITEM_CREATORS = """
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


def get_creators(connection: sqlite3.Connection,
                 item_id: str) -> Dict[str, List[str]]:
    cursor = connection.cursor()
    cursor.execute(ZOTERO_QUERY_ITEM_CREATORS, (item_id,))

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


ZOTERO_QUERY_ITEM_ATTACHMENTS = """
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
""".format(",".join(["?"] * len(
    papis_zotero.utils.ZOTERO_SUPPORTED_MIMETYPES_TO_EXTENSION)))


def get_files(connection: sqlite3.Connection, item_id: str, item_key: str,
              input_path: str, out_folder: str) -> List[str]:
    cursor = connection.cursor()
    cursor.execute(
        ZOTERO_QUERY_ITEM_ATTACHMENTS,
        (item_id,) + tuple(papis_zotero.utils.ZOTERO_SUPPORTED_MIMETYPES_TO_EXTENSION))

    files = []
    for key, path, mime_type in cursor:
        if match := re.match("storage:(.*)", path):
            file_name = match.group(1)
            files.append(os.path.join(input_path, "storage", key, file_name))
        elif os.path.exists(path):
            # NOTE: this is likely a symlink to some other on-disk location
            files.append(path)
        else:
            logger.error("Failed to export attachment %s (with type %s) from path '%s'",
                         key, mime_type, path)

    return files


ZOTERO_QUERY_ITEM_TAGS = """
SELECT
    tags.name
FROM
    tags,
    itemTags
WHERE
    itemTags.itemID = ? AND
    tags.tagID = itemTags.tagID
"""


def get_tags(connection: sqlite3.Connection, item_id: str) -> Dict[str, List[str]]:
    cursor = connection.cursor()
    cursor.execute(ZOTERO_QUERY_ITEM_TAGS, (item_id,))

    tags = [str(row[0]) for row in cursor]
    return {"tags": tags} if tags else {}


ZOTERO_QUERY_ITEM_COLLECTIONS = """
SELECT
    collections.collectionName
FROM
    collections,
    collectionItems
WHERE
    collectionItems.itemID = ? AND
    collections.collectionID = collectionItems.collectionID
"""


def get_collections(connection: sqlite3.Connection,
                    item_id: str) -> Dict[str, List[str]]:
    cursor = connection.cursor()
    cursor.execute(ZOTERO_QUERY_ITEM_COLLECTIONS, (item_id,))

    collections = [name for name, in cursor]
    return {"collections": collections} if collections else {}


ZOTERO_QUERY_ITEM_COUNT = """
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
""".format(",".join(["?"] * len(papis_zotero.utils.ZOTERO_EXCLUDED_ITEM_TYPES)))

ZOTERO_QUERY_ITEMS = """
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
""".format(",".join(["?"] * len(papis_zotero.utils.ZOTERO_EXCLUDED_ITEM_TYPES)))


def add_from_sql(input_path: str,
                 out_folder: Optional[str] = None,
                 link: bool = False) -> None:
    """
    :param inpath: path to zotero SQLite database "zoter.sqlite" and
        "storage" to be imported
    :param outpath: path where all items will be exported to created if not
        existing
    """

    if out_folder is None:
        out_folder = papis.config.get_lib_dirs()[0]

    if not os.path.exists(input_path):
        raise FileNotFoundError(
            "[Errno 2] No such file or directory: '{}'".format(input_path))

    if not os.path.exists(out_folder):
        raise FileNotFoundError(
            "[Errno 2] No such file or directory: '{}'".format(out_folder))

    zotero_sqlite_file = os.path.join(input_path, "zotero.sqlite")
    if not os.path.exists(zotero_sqlite_file):
        raise FileNotFoundError(
            "No 'zotero.sqlite' file found in '{}'".format(input_path))

    connection = sqlite3.connect(zotero_sqlite_file)
    cursor = connection.cursor()

    cursor.execute(ZOTERO_QUERY_ITEM_COUNT,
                   papis_zotero.utils.ZOTERO_EXCLUDED_ITEM_TYPES)
    for row in cursor:
        items_count = row[0]

    cursor.execute(ZOTERO_QUERY_ITEMS,
                   papis_zotero.utils.ZOTERO_EXCLUDED_ITEM_TYPES)
    if out_folder is not None:
        papis.config.set_lib_from_name(out_folder)

    folder_name = papis.config.getstring("add-folder-name")
    for i, (item_id, item_type, item_key, date_added) in enumerate(cursor, start=1):
        # convert fields
        date_added = (
            datetime.strptime(date_added, "%Y-%m-%d %H:%M:%S")
            .strftime(papis.strings.time_format))
        item_type = papis_zotero.utils.ZOTERO_TO_PAPIS_TYPES.get(item_type, item_type)

        # get Zotero metadata
        fields = get_fields(connection, item_id)
        files = get_files(connection,
                          item_id,
                          item_key,
                          input_path=input_path,
                          out_folder=out_folder)

        item = {"type": item_type, "time-added": date_added, "files": files}
        item.update(fields)
        item.update(get_creators(connection, item_id))
        item.update(get_tags(connection, item_id))
        item.update(get_collections(connection, item_id))

        logger.info("[%4d/%-4d] Exporting item '%s' to library '%s'.",
                    i, items_count, item_key, out_folder)

        papis.commands.add.run(paths=files, data=item, link=link,
                               folder_name=folder_name
                               )

    logger.info("Finished exporting from '%s'.", input_path)
    logger.info("Exported files can be found at '%s'.", out_folder)
