from pybel.manager import Namespace, NamespaceEntry

from .namespace_manager import BELNamespaceManagerMixin
from .abstract_manager import AbstractManager
example = 'https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/master/src/ontology/doid.obo'

from typing import Optional

def get_go_from_obo(path: Optional[str] = None, force_download: bool = False) -> MultiDiGraph:
    """Download and parse a GO obo file with :mod:`obonet` into a MultiDiGraph.

    :param path: path to the file
    :param force_download: True to force download resources
    """
    if path is None and os.path.exists(GO_OBO_PICKLE_PATH) and not force_download:
        log.info('loading from %s', GO_OBO_PICKLE_PATH)
        return read_gpickle(GO_OBO_PICKLE_PATH)

    if path is not None:
        return obonet.read_obo(path)

    path = download_go_obo(force_download=force_download)

    log.info('reading OBO')
    result = obonet.read_obo(path)

    log.info('caching pickle to %s', GO_OBO_PICKLE_PATH)
    write_gpickle(result, GO_OBO_PICKLE_PATH)

    return result

base = AbstractManager._make_base()

class Term(base):
    """"""

class Manager(BELNamespaceManagerMixin):
    def _create_namespace_entry_from_model(self, model, namespace: Namespace) -> NamespaceEntry:
        pass

    module_name = 'doid'
    _base = base
