import os
import re
from typing import Any, Dict, Optional

import papis.bibtex
import papis.commands.add
import papis.config
import papis.logging

logger = papis.logging.get_logger(__name__)

RE_SEPARATOR = re.compile(r"\s*,\s*")


def add_from_bibtex(bib_file: str,
                    out_folder: Optional[str] = None,
                    link: bool = False) -> None:
    if out_folder is not None:
        papis.config.set_lib_from_name(out_folder)

    entries = papis.bibtex.bibtex_to_dict(bib_file)
    nentries = len(entries)
    for i, entry in enumerate(entries):
        result: Dict[str, Any] = entry.copy()

        # cleanup date
        if "date" in result:
            date = str(result.pop("date")).split("-")
            result["year"] = int(date[0])
            result["month"] = int(date[1])

        # cleanup tags
        if "keywords" in result:
            result["tags"] = RE_SEPARATOR.split(result.pop("keywords"))

        if "ref" in result:
            result["ref"] = papis.bibtex.ref_cleanup(result["ref"])
        else:
            result["ref"] = papis.bibtex.create_reference(result)

        # get file
        pdf_file = result.pop("file", None)
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
                    i, nentries, result["ref"])

        papis.commands.add.run([pdf_file] if pdf_file is not None else [],
                               data=result,
                               link=link)
