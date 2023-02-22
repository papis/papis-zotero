import glob
import logging
import os
import re
import shutil
import sqlite3
from typing import Any, Dict, Iterable, List, Optional

import yaml

# zotero item types to be excluded.
# "attachment" are automatically excluded and will be treated as "files"
excluded_types = ["note"]

# dictionary of zotero attachments mime types to be included
# mapped onto their respective extension to be used in papis
included_attachments = {
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

# dictionary translating from zotero to papis type names
translated_types = {"journalArticle": "article"}

# dictionary translating from zotero to papis field names
translated_fields = {"DOI": "doi"}

# seperator between multiple tags
tag_delimiter = ","

# if no attachment is found, give info.yaml as content file
# set to None if no file should be given in that case
default_file: Optional[str] = None

input_path: Optional[str] = None
output_path: Optional[str] = None


def get_tuple(elements: Iterable[str]) -> str:
    """
    Concatenate given strings to SQL tuple of strings
    """
    elements_tuple = "("
    for element in elements:
        if elements_tuple != "(":
            elements_tuple += ","
        elements_tuple += '"' + element + '"'
    elements_tuple += ")"
    return elements_tuple


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
        field_name = translated_fields.get(field_row[0], field_row[0])
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
      itemCreators.itemID = {itemID} AND
      creatorTypes.creatorTypeID = itemCreators.creatorTypeID AND
      creators.creatorID = itemCreators.creatorID
    ORDER BY
      creatorTypes.creatorType,
      itemCreators.orderIndex
    """
    creator_cursor = connection.cursor()
    creator_cursor.execute(
        item_creator_query.format(itemID=item_id)
    )
    creators: Dict[str, Any] = {}

    for creator_row in creator_cursor:
        creator_name = creator_row[0]
        creator_name_list = creator_name + "_list"
        given_name = creator_row[1]
        surname = creator_row[2]

        current_creators = creators.get(creator_name, "")
        if current_creators != "":
            current_creators += " and "
        current_creators += "{surname}, {given_name}".format(
            given_name=given_name, surname=surname
        )
        creators[creator_name] = current_creators

        current_creators_list = creators.get(creator_name_list, [])
        current_creators_list.append(
            {"given_name": given_name, "surname": surname}
        )
        creators[creator_name_list] = current_creators_list

    return creators


def get_files(connection: sqlite3.Connection,
              item_id: str,
              item_key: str) -> Dict[str, List[str]]:
    global input_path
    if input_path is None:
        raise ValueError("Input path is not set")

    if output_path is None:
        raise ValueError("Output path is not set")

    item_attachment_query = """
    SELECT
      items.key,
      itemAttachments.path,
      itemAttachments.contentType
    FROM
      itemAttachments,
      items
    WHERE
      itemAttachments.parentItemID = {itemID} AND
      itemAttachments.contentType IN {mimetypes} AND
      items.itemID = itemAttachments.itemID
    """
    mimetypes = get_tuple(included_attachments.keys())
    attachment_cursor = connection.cursor()
    attachment_cursor.execute(
        item_attachment_query.format(itemID=item_id, mimetypes=mimetypes)
    )
    files = []
    for attachement_row in attachment_cursor:
        key = attachement_row[0]
        path = attachement_row[1]
        mime = attachement_row[2]
        # extension = included_attachments[mime]
        try:
            # NOTE: a single file is assumed in the attachment's folder
            # to avoid using path, which may contain invalid characters
            import_path = glob.glob(input_path + "/storage/" + key + "/*.*")[0]
            extension = os.path.splitext(import_path)[1]
            local_path = os.path.join(
                output_path, item_key, key + "." + extension
            )
            shutil.copyfile(import_path, local_path)
            files.append(key + "." + extension)
        except Exception:
            print(
                "failed to export attachment {key}: {path} ({mime})".format(
                    key=key, path=path, mime=mime
                )
            )
            pass

    if files == [] and default_file:
        files.append(default_file)
    return {"files": files}


def get_tags(connection: sqlite3.Connection, item_id: str) -> Dict[str, str]:
    item_tag_query = """
    SELECT
      tags.name
    FROM
      tags,
      itemTags
    WHERE
      itemTags.itemID = {itemID} AND
      tags.tagID = itemTags.tagID
    """
    tag_cursor = connection.cursor()
    tag_cursor.execute(item_tag_query.format(itemID=item_id))
    tags = ""
    for tag_row in tag_cursor:
        if tags != "":
            tags += tag_delimiter + " "
        tags += "{tag}".format(tag=tag_row[0])

    return {"tags": tags}


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
    collections = []
    for collection_row in collection_cursor:
        collections.append(collection_row[0])

    return {"project": collections}


def add_from_sql(inpath: str, outpath: str) -> None:
    """
    :param inpath: path to zotero SQLite database "zoter.sqlite" and
        "storage" to be imported
    :param outpath: path where all items will be exported to created if not
        existing
    """
    global input_path
    global output_path

    logger = logging.getLogger("papis_zotero:importer:sql")
    input_path = inpath
    output_path = outpath

    connection = sqlite3.connect(os.path.join(input_path, "zotero.sqlite"))
    cursor = connection.cursor()

    excluded_types.append("attachment")
    excluded_type_tuple = get_tuple(excluded_types)
    items_count_query = """
      SELECT
        COUNT(item.itemID)
      FROM
        items item,
        itemTypes itemType
      WHERE
        itemType.itemTypeID = item.itemTypeID AND
        itemType.typeName NOT IN {excluded_type_tuple}
      ORDER BY
        item.itemID
    """
    cursor.execute(items_count_query.format(excluded_type_tuple=excluded_type_tuple))
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
        itemType.typeName NOT IN {excluded_type_tuple}
      ORDER BY
        item.itemID
    """

    cursor.execute(items_query.format(excluded_type_tuple=excluded_type_tuple))
    current_item = 0
    for row in cursor:
        current_item += 1
        item_id = row[0]
        item_type = translated_types.get(row[1], row[1])
        item_key = row[2]
        date_added = row[3]
        date_modified = row[4]
        client_date_modified = row[5]
        logger.info(
            "exporting item {current_item}/{items_count}: {key}".format(
                current_item=current_item, items_count=items_count, key=item_key
            )
        )

        path = os.path.join(output_path, item_key)
        if not os.path.exists(path):
            os.makedirs(path)

        # Get mendeley keys
        fields = get_fields(connection, item_id)
        extra = fields.get("extra", None)
        ref = item_key
        if extra:
            # try to convert
            matches = re.search(r".*Citation Key: (\w+)", extra)
            if matches:
                ref = matches.group(1)
        logger.info("exporting under ref %s" % ref)
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
        item.update(get_files(connection, item_id, item_key))

        item.update({"ref": ref})

        with open(os.path.join(path, "info.yaml"), "w+") as item_file:
            yaml.dump(item, item_file, default_flow_style=False)

    logger.info("done")
