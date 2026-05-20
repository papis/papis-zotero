from __future__ import annotations

import os
import re
from typing import Any

import papis.logging

from papis_zotero.utils import set_lib_from_path

logger = papis.logging.get_logger(__name__)

RE_SEPARATOR = re.compile(r"\s*,\s*")


def add_from_bibtex(bib_file: str,
                    out_folder: str | None = None,
                    link: bool = False) -> None:
    from papis.config import getformatpattern

    if out_folder is not None:
        set_lib_from_path(out_folder)
    folder_name = getformatpattern("add-folder-name")

    from papis.bibtex import bibtex_to_dict, create_reference, ref_cleanup

    entries = bibtex_to_dict(bib_file)
    nentries = len(entries)

    for i, entry in enumerate(entries):
        result: dict[str, Any] = entry.copy()

        # cleanup date
        if "date" in result:
            date = str(result.pop("date")).split("-")
            result["year"] = int(date[0])
            if len(date) >= 2:
                result["month"] = int(date[1])

        # cleanup tags
        if "keywords" in result:
            result["tags"] = RE_SEPARATOR.split(result.pop("keywords"))

        if "ref" in result:
            result["ref"] = ref_cleanup(result["ref"])
        else:
            result["ref"] = create_reference(result)

        # get file
        file_field = result.pop("file", None)
        if file_field is not None:

            # captures path ending in ".extension", followed by :, ; or }
            pattern = r"(?:/home|\./|(?<=:)).+?\.\w+(?=[:;}])"

            paths = re.findall(pattern, file_field)

            from papis.commands.add import run as add
            for p in paths:

                if not p.startswith("/home"):
                    path = os.path.join(os.path.dirname(bib_file), p)
                else:
                    path = p

                if os.path.exists(path):
                    logger.info("Document file found: '%s'.", path)

                    logger.info("[%4d/%-4d] Exporting item with ref '%s'.",
                            i, nentries, result["ref"])

                    add([path], data=result, link=link, folder_name=folder_name)

                else:
                    logger.warning("Document file not found: '%s'.", path)
