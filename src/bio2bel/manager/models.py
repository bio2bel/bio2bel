# -*- coding: utf-8 -*-

"""SQLAlchemy models for Bio2BEL databases."""

from sqlalchemy import Column, Integer, String

__all__ = [
    'SpeciesMixin',
]


class SpeciesMixin:
    """A database model mixin for species."""

    id = Column(Integer, primary_key=True)  # noqa:A003

    taxonomy_id = Column(String(255), doc='NCBI taxonomy identifier')
    name = Column(String(255), doc='NCBI taxonomy label')

    def __repr__(self):  # noqa: D105
        return f'taxonomy:{self.taxonomy_id} ! {self.name}'
