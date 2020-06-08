# -*- coding: utf-8 -*-

"""circRNADisease: experimentally supported circRNA and disease associations database."""

import pandas as pd

URL = 'http://cgga.org.cn:9091/circRNADisease/download/2017-12-25.txt'


def _get_df():
    df = pd.read_csv(
        URL,
        sep='\t',
        usecols=[
            'pmid',
            'circRNA id',
            'circRNA name',
            'circRNA synonyms',
            'disease',
            'method of circRNA detection',
            'species',
            'expression pattern',
        ],
    )
    return df
