#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import tempfile
import sys
import os
import papis.bibtex
import papis.api
from papis.commands.add import run as papis_add
import papis.config
import papis.utils
import yaml
import logging

logger = logging.getLogger('papis_zotero:importer')


def import_from_bibtexfile(
        bib_file,
        out_folder=None,
        link=False
    ):

    if out_folder is not None:
        papis.config.set_lib(out_folder)

    entries = papis.bibtex.bibtex_to_dict(bib_file)

    for entry in entries:
        for basic_field in ['ref', 'author', 'title']:
            if basic_field not in entry.keys():
                entry[basic_field] = papis.utils.input(
                    '%s Not found, please insert' % basic_field,
                    default="???????"
                )

        print('INFO: Processing  |   ref: %s' % entry.get('ref'))
        print('                  |Author: %s' % entry.get('author'))
        print('                  | Title: %s' % entry.get('title'))
        print('                  |')

        pdf_file = None
        if 'file' in entry.keys():
            pdf_file = entry.get('file').split(':')[1]
            pdf_file = os.path.join(os.path.dirname(bib_file), pdf_file)
            print('\tINFO: File field detected (%s)' % pdf_file)
            if not os.path.exists(pdf_file):
                print('\tWARNING: Path (%s) not found! Ignoring it' % pdf_file)
                del entry['file']
                pdf_file = None

        papis_add(
            [pdf_file] if pdf_file is not None else [],
            data=entry,
            link=link
        )
