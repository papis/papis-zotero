import os
from typing import Optional

import papis.bibtex
import papis.commands.add
import papis.config
import papis.logging

logger = papis.logging.get_logger(__name__)


def add_from_bibtex(bib_file: str,
                    out_folder: Optional[str] = None,
                    link: bool = False) -> None:
    if out_folder is not None:
        papis.config.set_lib_from_name(out_folder)

    entries = papis.bibtex.bibtex_to_dict(bib_file)
    nentries = len(entries)
    for i, entry in enumerate(entries):
        # cleanup tags
        if "date" in entry:
            date = str(entry.pop("date")).split("-")
            entry["year"] = int(date[0])    # type: ignore[assignment]
            entry["month"] = int(date[1])   # type: ignore[assignment]

        if "keywords" in entry:
            entry["tags"] = entry.pop("keywords")

        if "author" not in entry:
            if "tags" in entry:
                entry["tags"] = "{} unknown-author".format(entry["tags"])
            else:
                entry["tags"] = "unknown-author"

        if "ref" in entry:
            entry["ref"] = papis.bibtex.ref_cleanup(entry["ref"])
        else:
            entry["ref"] = papis.bibtex.create_reference(entry)

        # get file
        pdf_file = entry.pop("file", None)
        if pdf_file is not None:
            pdf_file = pdf_file.split(":")[1]
            pdf_file = os.path.join(*pdf_file.split("/"))
            pdf_file = os.path.join(os.path.dirname(bib_file), pdf_file)

            if os.path.exists(pdf_file):
                logger.info("Document file found: '%s'.", pdf_file)
            else:
                logger.warning("Document file not found: '%s'.", pdf_file)
                pdf_file = None

        # add to library
        logger.info("[%4d/%-4d] Exporting item with ref '%s'.",
                    i, nentries, entry["ref"])

        papis.commands.add.run([pdf_file] if pdf_file is not None else [],
                               data=entry,
                               link=link)
