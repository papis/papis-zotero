import os
import logging
from typing import Optional

import tqdm
import colorama

import papis.api
import papis.bibtex
import papis.commands.add
import papis.config
import papis.utils

logger = logging.getLogger("zotero:bibtex")

info_template = """{c.Back.BLACK}
{c.Fore.RED}||
{c.Fore.RED}||{c.Fore.YELLOW}    ref: {c.Fore.GREEN}{ref}
{c.Fore.RED}||{c.Fore.YELLOW} author: {c.Fore.GREEN}{author}
{c.Fore.RED}||{c.Fore.YELLOW}  title: {c.Fore.GREEN}{title}
{c.Fore.RED}||{c.Style.RESET_ALL}
"""


def add_from_bibtex(bib_file: str,
                    out_folder: Optional[str] = None,
                    link: bool = False) -> None:

    if out_folder is not None:
        papis.config.set_lib_from_name(out_folder)

    entries = papis.bibtex.bibtex_to_dict(bib_file)

    with tqdm.tqdm(entries) as t:
        for entry in t:

            if "keywords" in entry.keys():
                entry["tags"] = entry["keywords"]
                del entry["keywords"]

            if "author" not in entry.keys():
                entry["tags"] = "Unkown"

            if "ref" in entry.keys():
                entry["ref"] = entry["ref"].replace("?", "")

            print(info_template.format(
                c=colorama,
                author=entry.get("author"),
                title=entry.get("title"),
                ref=entry.get("ref"),
            ))

            pdf_file = entry.get("file")
            if pdf_file is not None:
                pdf_file = pdf_file.split(":")[1]
                pdf_file = os.path.join(os.path.dirname(bib_file), pdf_file)
                logger.info("\tINFO: File field detected (%s)" % pdf_file)
                if not os.path.exists(pdf_file):
                    logger.warning(
                        colorama.Back.YELLOW + colorama.Fore.BLACK
                        + ("Path (%s)" % pdf_file)
                        + colorama.Back.RED
                        + " not found! Ignoring it"
                        + colorama.Style.RESET_ALL
                    )
                    del entry["file"]
                    pdf_file = None

            papis.commands.add.run(
                [pdf_file] if pdf_file is not None else [],
                data=entry,
                link=link)
