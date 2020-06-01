# -*- coding: utf-8 -*-

"""Convert HMDD to BEL."""

import logging

import pandas as pd
import pyobo
from tqdm import tqdm

import pybel
import pybel.dsl
from .. import ensure_path

logger = logging.getLogger(__name__)

PREFIX = 'hmdd'
VERSION = '3.2'
URL = 'http://www.cuilab.cn/static/hmdd3/data/alldata.txt'


def get_bel() -> pybel.BELGraph:
    """Get the HMDD data."""
    #  category	mir	disease	pmid	description
    path = ensure_path(PREFIX, URL)
    df = pd.read_csv(
        path,
        sep='\t',
        dtype=str,
        encoding="ISO-8859-1",
    )

    failed_mirnas = 0
    mirna_to_dsl = {}
    mirnas = df['mir'].unique()
    it = tqdm(mirnas, desc='mapping miRNA names')
    for text in it:
        _, identifier, name = pyobo.ground('mirbase', text)
        if identifier is None:
            it.write(f'[mirbase] could not ground: {text}')
            failed_mirnas += 1
            continue
        mirna_to_dsl[text] = pybel.dsl.MicroRna(
            namespace='mirbase',
            identifier=identifier,
            name=name,
        )

    logger.info(f'failed on {failed_mirnas}/{len(mirnas)} miRNAs')

    failed_diseases = 0
    disease_to_dsl = {}
    diseases = df['disease'].unique()
    it = tqdm(diseases, desc='mapping disease names')
    for text in it:
        prefix, identifier, name = pyobo.ground(['mondo', 'doid', 'efo', 'hp', 'mesh'], text)
        if identifier is None and ', ' in text:
            i = text.index(', ')
            left, right = text[:i], text[i + 2:]
            x = f'{right} {left}'
            prefix, identifier, name = pyobo.ground(['mondo', 'doid', 'efo', 'hp', 'mesh'], x)
            if identifier is None and ', ' in x:
                x2 = ' '.join(z.strip() for z in text.split(',')[::-1])
                prefix, identifier, name = pyobo.ground(['mondo', 'doid', 'efo', 'hp', 'mesh'], x2)
        if identifier is None:
            it.write(f'could not ground {text}')
            failed_diseases += 1
            continue
        disease_to_dsl[text] = pybel.dsl.Pathology(
            namespace=prefix,
            identifier=identifier,
            name=name,
        )

    logger.info(f'failed on {failed_diseases}/{len(diseases)} diseases')

    rv = pybel.BELGraph(name='HMDD', version=VERSION)
    for _category, mir, disease, pmid, text in df.values:
        source = mirna_to_dsl.get(mir)
        target = disease_to_dsl.get(disease)
        if not source or not target:
            continue
        rv.add_regulates(
            source,
            target,
            citation=pmid,
            evidence=text,
        )
    return rv


if __name__ == '__main__':
    get_bel().summarize()
