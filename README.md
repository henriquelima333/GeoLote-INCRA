# Análise de Sobreposição de Imóvel — Plugin QGIS

Plugin para análise de sobreposição de um imóvel com múltiplas camadas vetoriais,
gerando relatório tabular e geometrias de interseção.

---

## Instalação

### Opção 1 — Instalar pelo ZIP (recomendado)

1. Abra o QGIS
2. Menu **Plugins → Gerenciar e Instalar Plugins...**
3. Aba **Instalar a partir de ZIP**
4. Selecione o arquivo `analise_sobreposicao_imovel.zip`
5. Clique em **Instalar Plugin**

### Opção 2 — Copiar manualmente a pasta

1. Localize a pasta de plugins do QGIS no seu sistema:

   | Sistema       | Caminho                                                       |
   |---------------|---------------------------------------------------------------|
   | Windows       | `C:\Users\<usuário>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\` |
   | Linux         | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/` |
   | macOS         | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/` |

2. Copie a pasta `analise_sobreposicao_imovel` inteira para dentro da pasta `plugins`
3. Reinicie o QGIS
4. Menu **Plugins → Gerenciar e Instalar Plugins...**
5. Aba **Instalados** → marque **Análise de Sobreposição de Imóvel**

---

## Como usar

O algoritmo fica disponível no **Painel de Processing**:

```
Análise de Imóveis
  └── Análise de Sobreposição de Imóvel
```

### Parâmetros

| Parâmetro | Descrição |
|-----------|-----------|
| **Camada do Imóvel** | Camada de polígono de referência. Apenas o **primeiro polígono** é utilizado. |
| **Camadas para análise** | Uma ou mais camadas de polígonos a serem comparadas com o imóvel. |
| **Relatório de sobreposição** | Saída tabular (sem geometria) com `id_imovel`, `camada`, `area_m2` e `percent`. |
| **Geometrias de interseção** | Saída vetorial com os polígonos resultantes de cada sobreposição. |

### Fluxo interno

1. Extrai o primeiro polígono da camada de imóvel
2. Para cada camada de análise:
   - Aplica **filtro espacial** (`Extract by Location`) para selecionar apenas feições que intersectam o imóvel
   - Corrige geometrias inválidas (`Fix Geometries`)
   - Calcula a **interseção** entre o imóvel e as feições filtradas
   - Registra área (m²) e percentual de sobreposição
3. Grava relatório e geometrias nas saídas

---

## Estrutura de arquivos

```
analise_sobreposicao_imovel/
├── __init__.py        ← Entry point do plugin
├── plugin.py          ← Classe principal (registra o provider)
├── provider.py        ← Processing Provider
├── algorithm.py       ← Algoritmo de análise
├── icon.png           ← Ícone do plugin
├── metadata.txt       ← Metadados obrigatórios do QGIS
└── README.md          ← Esta documentação
```

---

## Requisitos

- QGIS **3.0** ou superior
- Sem dependências externas (usa apenas algoritmos nativos do QGIS Processing)

---

## Licença

MIT — livre para uso e modificação.
