import os
from typing import Optional

import tqdm
import click
import colorama

import papis.api
import papis.bibtex
import papis.commands.add
import papis.config
import papis.utils
import papis.logging

logger = papis.logging.get_logger(__name__)

BIBTEX_INFO_TEMPLATE = """{c.Back.BLACK}
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
    for entry in tqdm.tqdm(entries):
        if "keywords" in entry:
            entry["tags"] = entry.pop("keywords")

        if "author" not in entry:
            entry["tags"] = "Unknown Author"

        if "ref" in entry:
            entry["ref"] = entry["ref"].replace("?", "")

        msg = BIBTEX_INFO_TEMPLATE.format(
            c=colorama,
            author=entry.get("author"),
            title=entry.get("title"),
            ref=entry.get("ref"),
        )
        click.echo(msg)

        pdf_file = entry.pop("file", None)
        if pdf_file is not None:
            pdf_file = pdf_file.split(":")[1]
            pdf_file = os.path.join(os.path.dirname(bib_file), pdf_file)
            logger.info("File field detected: '%s'", pdf_file)

            if not os.path.exists(pdf_file):
                logger.warning(
                    "{c.Back.YELLOW}{c.Fore.BLACK}Document file not found: '%s'."
                    "{c.Style.RESET_ALL}", pdf_file)
                pdf_file = None

        papis.commands.add.run([pdf_file] if pdf_file is not None else [],
                               data=entry,
                               link=link)
