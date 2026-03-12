# -*- coding: utf-8 -*-
"""
GeoLote - Plugin QGIS
Algoritmo principal de análise.
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsProcessing,
    QgsFeatureSink,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterFeatureSink,
    QgsWkbTypes
)
import processing


# Campos fixos sempre presentes na camada de interseções
_CAMPOS_FIXOS = ['id_imovel', 'camada', 'area_m2']

# Prefixo aplicado a campos originais que colidam com campos fixos
_PREFIXO = 'orig_'


def _sanitize_field_name(name, used_names):
    """
    Trunca o nome a 10 chars (limite SHP), resolve colisão com campos fixos
    e garante unicidade dentro do conjunto already_used.
    Retorna o nome final e atualiza used_names in-place.
    """
    name = name[:10]

    if name.lower() in _CAMPOS_FIXOS:
        name = (_PREFIXO + name)[:10]

    base, idx = name, 1
    while name.lower() in used_names:
        suffix = f'_{idx}'
        name   = base[:10 - len(suffix)] + suffix
        idx   += 1

    used_names.add(name.lower())
    return name


def _build_intersecoes_fields(layers, feedback):
    """
    Constrói QgsFields unificado para a camada de interseções.

    Campos fixos:  id_imovel | camada | area_m2
    Campos extras: todos os campos originais de cada camada de análise,
                   concatenados (com sanitização de nomes).

    Retorna:
        fields_int  – QgsFields completo
        mapeamento  – { nome_camada: [(nome_orig, nome_final), ...] }
    """
    fields_int  = QgsFields()
    fields_int.append(QgsField('id_imovel', QVariant.String))
    fields_int.append(QgsField('camada',    QVariant.String))
    fields_int.append(QgsField('area_m2',   QVariant.Double))

    mapeamento   = {}
    used_names   = set(_CAMPOS_FIXOS)

    for l in layers:
        mapa_camada = []

        for field in l.fields():
            nome_orig  = field.name()
            nome_final = _sanitize_field_name(nome_orig, used_names)

            novo = QgsField(nome_final, field.type())
            novo.setLength(field.length())
            novo.setPrecision(field.precision())
            fields_int.append(novo)

            mapa_camada.append((nome_orig, nome_final))

            if nome_final != nome_orig:
                feedback.pushInfo(
                    f'  [renomeado] "{nome_orig}" → "{nome_final}"'
                    f' (camada: {l.name()})'
                )

        mapeamento[l.name()] = mapa_camada

    return fields_int, mapeamento


class AnaliseSobreposicaoImovel(QgsProcessingAlgorithm):

    IMOVEL      = 'IMOVEL'
    CAMADAS     = 'CAMADAS'
    RELATORIO   = 'RELATORIO'
    INTERSECOES = 'INTERSECOES'

    # ------------------------------------------------------------------ #
    #  Metadados
    # ------------------------------------------------------------------ #

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return AnaliseSobreposicaoImovel()

    def name(self):
        return 'analise_sobreposicao_imovel_otimizada'

    def displayName(self):
        return self.tr('Análise de Sobreposição de Imóvel')

    def group(self):
        return self.tr('GeoLote')

    def groupId(self):
        return 'geolote'

    def shortHelpString(self):
        return self.tr(
            '<b>Análise de Sobreposição de Imóvel</b><br><br>'
            'Analisa a sobreposição do <b>PRIMEIRO polígono</b> da camada de imóvel '
            'com múltiplas camadas vetoriais.<br><br>'
            '<b>Entradas:</b><br>'
            '• <i>Camada do Imóvel</i> — polígono de referência (usa o primeiro polígono)<br>'
            '• <i>Camadas para análise</i> — uma ou mais camadas de polígonos<br><br>'
            '<b>Saídas:</b><br>'
            '• <i>Relatório</i> — tabela com área (m²) e percentual por camada<br>'
            '• <i>Geometrias de interseção</i> — polígonos sobrepostos com '
            '<b>todos os atributos originais</b> de cada feição preservados<br><br>'
            '<b>Obs.:</b> nomes de campos são truncados a 10 caracteres (limite SHP). '
            'Conflitos de nome recebem sufixo numérico automático.'
        )

    # ------------------------------------------------------------------ #
    #  Parâmetros
    # ------------------------------------------------------------------ #

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.IMOVEL,
                self.tr('Camada do Imóvel (será usado o PRIMEIRO polígono)'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )

        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.CAMADAS,
                self.tr('Camadas para análise'),
                QgsProcessing.TypeVectorPolygon
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.RELATORIO,
                self.tr('Relatório de sobreposição')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.INTERSECOES,
                self.tr('Geometrias de interseção')
            )
        )

    # ------------------------------------------------------------------ #
    #  Processamento
    # ------------------------------------------------------------------ #

    def processAlgorithm(self, parameters, context, feedback):

        layer  = self.parameterAsVectorLayer(parameters, self.IMOVEL, context)
        layers = self.parameterAsLayerList(parameters, self.CAMADAS, context)

        # ── Valida imóvel ────────────────────────────────────────────── #
        features = list(layer.getFeatures())

        if not features:
            feedback.reportError(
                'A camada de imóvel está vazia!', fatalError=True
            )
            return {}

        feat       = features[0]
        geom       = feat.geometry()
        area_total = geom.area()

        feedback.pushInfo(
            f'Polígono selecionado — ID: {feat.id()} | Área: {area_total:.4f} m²'
        )
        if len(features) > 1:
            feedback.pushWarning(
                f'A camada possui {len(features)} polígonos. '
                'Apenas o PRIMEIRO será utilizado.'
            )

        # ── Campos do relatório (fixos) ──────────────────────────────── #
        fields_rel = QgsFields()
        fields_rel.append(QgsField('id_imovel', QVariant.String))
        fields_rel.append(QgsField('camada',    QVariant.String))
        fields_rel.append(QgsField('area_m2',   QVariant.Double))
        fields_rel.append(QgsField('percent',   QVariant.Double))

        # ── Campos das interseções: fixos + dinâmicos ────────────────── #
        feedback.pushInfo('\nMapeando campos das camadas de análise...')
        fields_int, mapeamento = _build_intersecoes_fields(layers, feedback)
        feedback.pushInfo(
            f'Total de campos na camada de interseções: {fields_int.count()}\n'
        )

        # ── Sinks ────────────────────────────────────────────────────── #
        (sink_rel, dest_rel) = self.parameterAsSink(
            parameters, self.RELATORIO, context,
            fields_rel, QgsWkbTypes.NoGeometry, layer.sourceCrs()
        )

        (sink_int, dest_int) = self.parameterAsSink(
            parameters, self.INTERSECOES, context,
            fields_int, QgsWkbTypes.Polygon, layer.sourceCrs()
        )

        # ── Loop ─────────────────────────────────────────────────────── #
        rel_feats = []
        int_feats = []
        total     = len(layers)

        for i, l in enumerate(layers):

            if feedback.isCanceled():
                break

            feedback.pushInfo(f'[{i + 1}/{total}] Processando: {l.name()}')

            # 1. Filtro espacial
            filtro = processing.run(
                'native:extractbylocation',
                {
                    'INPUT':     l,
                    'PREDICATE': [0],
                    'INTERSECT': layer,
                    'OUTPUT':    'TEMPORARY_OUTPUT'
                },
                context=context, feedback=feedback
            )

            layer_filtrada = filtro['OUTPUT']

            if layer_filtrada.featureCount() == 0:
                feedback.pushInfo('  → Sem interseção. Pulando.\n')
                feedback.setProgress(int((i + 1) / total * 100))
                continue

            feedback.pushInfo(
                f'  → {layer_filtrada.featureCount()} feição(ões) candidata(s).'
            )

            # 2. Corrige geometrias
            fixed = processing.run(
                'native:fixgeometries',
                {'INPUT': layer_filtrada, 'OUTPUT': 'TEMPORARY_OUTPUT'},
                context=context, feedback=feedback
            )
            layer_fixed = fixed['OUTPUT']

            # 3. Interseção
            # native:intersection mantém campos do INPUT (imóvel) e do OVERLAY
            # (camada de análise). Os campos do OVERLAY vêm DEPOIS dos do INPUT.
            result = processing.run(
                'native:intersection',
                {
                    'INPUT':   layer,
                    'OVERLAY': layer_fixed,
                    'OUTPUT':  'TEMPORARY_OUTPUT'
                },
                context=context, feedback=feedback
            )

            inter_layer = result['OUTPUT']

            if inter_layer.featureCount() == 0:
                feedback.pushInfo('  → Nenhuma área resultante.\n')
                feedback.setProgress(int((i + 1) / total * 100))
                continue

            # Área total sobreposta (soma de todas as feições intersectadas)
            area_int = sum(
                f.geometry().area() for f in inter_layer.getFeatures()
            )
            percent = (area_int / area_total * 100) if area_total > 0 else 0.0

            feedback.pushInfo(
                f'  → Sobreposição: {area_int:.4f} m² ({percent:.2f}%)\n'
            )

            # Relatório
            r_feat = QgsFeature(fields_rel)
            r_feat.setAttributes([
                str(feat.id()), l.name(),
                round(area_int, 4), round(percent, 4)
            ])
            rel_feats.append(r_feat)

            # Mapeamento de campos desta camada
            mapa_camada  = mapeamento.get(l.name(), [])
            inter_fields = inter_layer.fields()

            # Índices dos campos do OVERLAY na camada de interseção resultante.
            # native:intersection preserva o nome original dos campos do OVERLAY,
            # então buscamos pelo nome original.
            for f in inter_layer.getFeatures():

                g    = f.geometry()
                attrs = [None] * fields_int.count()

                # Campos fixos
                attrs[fields_int.indexOf('id_imovel')] = str(feat.id())
                attrs[fields_int.indexOf('camada')]    = l.name()
                attrs[fields_int.indexOf('area_m2')]   = round(g.area(), 4)

                # Atributos originais da feição sobreposta
                for nome_orig, nome_final in mapa_camada:
                    idx_inter = inter_fields.indexOf(nome_orig)
                    idx_out   = fields_int.indexOf(nome_final)

                    if idx_inter >= 0 and idx_out >= 0:
                        attrs[idx_out] = f.attributes()[idx_inter]

                i_feat = QgsFeature(fields_int)
                i_feat.setGeometry(g)
                i_feat.setAttributes(attrs)
                int_feats.append(i_feat)

            feedback.setProgress(int((i + 1) / total * 100))

        # ── Grava saídas ─────────────────────────────────────────────── #
        if rel_feats:
            sink_rel.addFeatures(rel_feats, QgsFeatureSink.FastInsert)
        if int_feats:
            sink_int.addFeatures(int_feats, QgsFeatureSink.FastInsert)

        feedback.pushInfo(
            f'✔ Concluído! {len(rel_feats)} camada(s) com sobreposição '
            f'| {len(int_feats)} geometria(s) gerada(s).'
        )

        return {
            self.RELATORIO:   dest_rel,
            self.INTERSECOES: dest_int
        }
