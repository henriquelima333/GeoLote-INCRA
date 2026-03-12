# -*- coding: utf-8 -*-
"""
GeoLote - Plugin QGIS
Classe principal do plugin.
"""

import os
from qgis.PyQt.QtWidgets import QAction, QToolBar
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
from qgis.utils import iface as qgis_iface
import processing

from .provider import AnaliseSobreposicaoProvider


class AnaliseSobreposicaoPlugin:

    def __init__(self, iface):
        self.iface        = iface
        self.provider     = None
        self.action       = None
        self.toolbar      = None

    # ------------------------------------------------------------------ #
    #  Processing Provider
    # ------------------------------------------------------------------ #

    def initProcessing(self):
        self.provider = AnaliseSobreposicaoProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    # ------------------------------------------------------------------ #
    #  GUI — barra de ferramentas + menu
    # ------------------------------------------------------------------ #

    def initGui(self):
        self.initProcessing()

        icon_path = os.path.join(os.path.dirname(__file__), 'geolote_icon.png')
        icon      = QIcon(icon_path)

        # ── Ação principal ───────────────────────────────────────────── #
        self.action = QAction(icon, 'GeoLote — Análise de Sobreposição', self.iface.mainWindow())
        self.action.setToolTip(
            'GeoLote: Analisa a sobreposição do imóvel com múltiplas camadas'
        )
        self.action.triggered.connect(self._open_algorithm)

        # ── Barra de ferramentas própria ─────────────────────────────── #
        self.toolbar = self.iface.mainWindow().findChild(QToolBar, 'GeoLote')
        if not self.toolbar:
            self.toolbar = self.iface.addToolBar('GeoLote')
            self.toolbar.setObjectName('GeoLote')

        self.toolbar.addAction(self.action)

        # ── Menu Plugins → GeoLote ───────────────────────────────────── #
        self.iface.addPluginToMenu('GeoLote', self.action)

    # ------------------------------------------------------------------ #
    #  Abre o algoritmo direto no diálogo do Processing
    # ------------------------------------------------------------------ #

    def _open_algorithm(self):
        processing.execAlgorithmDialog(
            'geolote:analise_sobreposicao_imovel_otimizada'
        )

    # ------------------------------------------------------------------ #
    #  Limpeza ao desinstalar
    # ------------------------------------------------------------------ #

    def unload(self):
        # Remove do menu
        self.iface.removePluginMenu('GeoLote', self.action)

        # Remove a barra de ferramentas
        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None

        # Remove o provider
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
