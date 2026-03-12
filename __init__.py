# -*- coding: utf-8 -*-
"""
Análise de Sobreposição de Imóvel - Plugin QGIS
Entry point do plugin.
"""


def classFactory(iface):
    from .plugin import AnaliseSobreposicaoPlugin
    return AnaliseSobreposicaoPlugin(iface)
