# -*- coding: utf-8 -*-
"""
GeoLote - Plugin QGIS
Processing Provider — agrupa os algoritmos do plugin no painel de Processing.
"""

import os
from qgis.core import QgsProcessingProvider
from PyQt5.QtGui import QIcon
from .algorithm import AnaliseSobreposicaoImovel


class AnaliseSobreposicaoProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()

    def id(self):
        return 'geolote'

    def name(self):
        return 'GeoLote'

    def longName(self):
        return 'GeoLote — Análise de Sobreposição de Imóvel'

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'geolote_icon.png')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return super().icon()

    def loadAlgorithms(self):
        self.addAlgorithm(AnaliseSobreposicaoImovel())
