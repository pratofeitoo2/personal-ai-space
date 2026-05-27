# Cheatsheets de Gráficos

Este único documento contém quatro cheatsheets concisos em formato Markdown:

- Obsidian Tracker (pyrochlore/obsidian-tracker)
- Plugin Obsidian Charts (blocos de código de gráficos no Obsidian)
- Chart.js (biblioteca oficial — opções comuns e exemplos)
- Mapeamento: opções do Chart.js ↔ YAML do Obsidian Charts

---

**Notas**
- Estes cheatsheets são condensados a partir da documentação oficial e dos repositórios.
- Use os exemplos como modelos; adapte `searchType`, `searchTarget` e as opções de gráficos aos seus dados.


## 1) Cheatsheet do Obsidian Tracker

Propósito: coletar ocorrências e valores numéricos de notas e renderizar como gráficos (linha, barra, pizza, mês, bullet) ou resumos de texto.

Uso básico

- Insira um bloco de código cercado com a linguagem `tracker` (pares chave: valor no estilo YAML) em uma nota do Obsidian e visualize no modo Preview.
- Parâmetros mínimos necessários: `searchType`, `searchTarget` e pelo menos um contêiner de saída (`line`, `bar`, `summary`, `bullet`, `month` ou `pie`).

Modelo rápido

```yaml
```tracker
searchType: tag
searchTarget: meditation
line:
  title: "Meditação"
  lineColor: '#69b3a2'
```
```

Parâmetros principais

- `searchType` (obrigatório): tag | frontmatter | wiki | text | dvField | table | fileMeta | task
- `searchTarget` (obrigatório): alvo(s) a serem correspondidos (separados por vírgula para múltiplos alvos)
- `folder`: caminho raiz para busca (padrão: raiz do vault)
- `file`, `specifiedFilesOnly`, `fileContainsLinkedFiles`, `fileMultiplierAfterLink`
- `dateFormat` (padrão `YYYY-MM-DD`) — usa formato Moment.js ou `iso-8601`
- `startDate`, `endDate` (aceita datas relativas)
- `datasetName` (nomes para conjuntos de dados)
- `separator` (para alvos de múltiplos valores dentro de um campo)
- `constValue`, `ignoreAttachedValue`, `ignoreZeroValue`, `accum`, `stack`, `penalty`, `valueShift`
- `fitPanelWidth`, `aspectRatio`, `margin`, `fixedScale`

Contêineres de saída

- `line`, `bar` — gráficos com várias opções por gráfico (cores, rótulos de eixos, ticks, legenda, showLegend)
- `summary` — saída de texto usando `template` com expressões
- `bullet` — gráfico tipo bullet (semelhante a gauge)
- `month` — visualização mensal (círculo/anotação) com limites e sequências
- `pie` — gráfico de pizza/donut

Opções comuns de `line` / `bar`

- `title`, `xAxisLabel`, `yAxisLabel`, `xAxisTickInterval`, `yAxisTickInterval`
- `yMin`, `yMax`, `reverseYAxis`
- `allowInspectData` (valores ao passar o mouse), `showLegend`, `legendPosition`, `legendOrientation`
- `lineColor`, `lineWidth`, `showPoint`, `pointSize`, `fillGap`
- `barColor`, `xAxisPadding`

Destaques da visualização mensal (`month`)

- `mode`: circle | annotation
- `threshold` e `thresholdType` (GreaterThan | LessThan)
- `showCircle`, `showStreak`, `initMonth`, `showAnnotation`, `showTodayRing`
- controles de cor: `circleColor`, `circleColorByValue`, `circleColorByStreak`

Conversão de dados e opções avançadas

- `textValueMap`: converte valores de texto/emoji para números (suporta regex como chave)
- `shiftOnlyValueLargerThan`: limite para aplicação de `valueShift`
- `dateFormatPrefix` / `dateFormatSuffix`: padrões regex para extração de datas
- `specifiedFilesOnly`: true para buscar apenas arquivos especificados
- `fileContainsLinkedFiles`: incluir arquivos com links
- `fileMultiplierAfterLink`: multiplicar valores após links

Expressões (1.9.0+)

- Use `{{...}}` para incorporar expressões em `summary.template`, `bullet.value`, `pie.data` ou `pie.label`.
- Funções: `dataset(index)`, `sum(dataset)`, `average(dataset)`, `maxStreak(dataset)`, `first()`, `last()`, `min()`, `max()`, `normalize()`, `setMissingValues()` etc.
- Operadores suportados: `+ - * / %`.
- Exemplo: `template: "Total: {{sum()::0.2f}}"` (formatação estilo printf)
- `first()` — retorna o primeiro valor no conjunto de dados
- `last()` — retorna o último valor no conjunto de dados

Referência rápida de tipos de busca

- `tag`: corresponde a `#tag` ou `#tag:valor` (valor após dois pontos, sem espaço)
- `frontmatter`: `chave: valor` no frontmatter YAML
- `wiki`: links wiki (`[[Página]]`)
- `text`: texto simples ou regex (envolva regex em aspas simples; use grupo nomeado `?<value>` para extrair um valor)
- `dvField`: campos inline do Dataview (`chave:: valor`)
- `table`: lê uma tabela em um arquivo usando a sintaxe `filePath[tableIndex][colIndex]`
- `fileMeta`: `cDate`, `mDate`, `size`, `numWords`, `numChars`, `numSentences`
- `task`: suporta `task`, `task.all`, `task.done`, `task.notdone`

Exemplos

- Rastrear ocorrências de `#meditation`:
```yaml
```tracker
searchType: tag
searchTarget: meditation
bar:
  title: Meditação
```
```

- Rastrear peso do frontmatter:
```yaml
```tracker
searchType: frontmatter
searchTarget: weight
line:
  title: Peso
```
```

- Usar regex para extrair passos:
```yaml
```tracker
searchType: text
searchTarget: 'walked\s+(?<value>[0-9]+)\s+steps'
line:
  title: Passos
```
```

Onde encontrar mais

- Pasta de exemplos no repositório do plugin: `examples/` — contém muitos blocos completos do tracker e dados de exemplo.


## 2) Cheatsheet do Plugin Obsidian Charts

Propósito: criar gráficos no Obsidian usando um bloco de código cercado `chart` com propriedades YAML. (O plugin renderiza o gráfico usando Chart.js nos bastidores.)

Modelo básico

```yaml
```chart
type: "line"
labels: ["2025-11-01","2025-11-02"]
series:
  - title: "Série A"
    data: [10, 12]
  - title: "Série B"
    data: [7, 9]
```
```

Notas

- Use a indentação no estilo YAML com cuidado no Obsidian; colar pode alterar a indentação.
- `title` é opcional, mas recomendado.
- O Criador Gráfico (Command Palette ou atalho) pode ajudar a construir gráficos básicos.
- O plugin integra o Chart.js, então qualquer opção do Chart.js pode ser passada via `options`.

Valores comuns de `type`

- `line`, `bar`, `pie`, `doughnut`, `radar`, `polarArea`, `bubble`, `scatter`, `mixed`, `sankey`

Campos principais

- `type`: tipo de gráfico
- `labels`: array de rótulos para o eixo X (não usado para sankey)
- `series`: array de objetos de séries com `title` e `data`
- `options` (opções avançadas opcionais do Chart.js podem ser colocadas sob `options:` seguindo a configuração do Chart.js)

Opções específicas do Obsidian Charts

- `width`: largura CSS (ex.: "60%", "300px", "100%")
- `legend`: true/false para mostrar/ocultar legenda
- `legendPosition`: top, left, bottom, right
- `legendOrientation`: horizontal, vertical
- `fill`: true para gráficos de área (preenche sob a linha)
- `tension`: número (0-1) controla a suavidade da curva para gráficos de linha
- `transparency`: float [0, 1] para opacidade do gráfico
- `fitPanelWidth`: true para ajustar à largura do contêiner
- `time`: formato para eixos de tempo/data
- `aspectRatio`: número para proporção largura:altura

Opções de controle de eixo

- `xTitle` / `yTitle`: rótulos para os eixos x e y
- `indexAxis`: "x" ou "y" — alterna para gráfico de barras horizontal
- `beginAtZero`: true/false — inicia o eixo em zero
- `xReverse` / `yReverse`: true/false — inverte a direção do eixo
- `xAxisTickInterval` / `yAxisTickInterval`: número de pixels entre os ticks
- `xAxisTickLabelFormat` / `yAxisTickLabelFormat`: formato para rótulos de ticks (suporta padrões regex)
- `xAxisPadding`: preenchimento no eixo x

Modificadores de dados

- `spanGaps`: true para conectar pontos com dados ausentes
- `bestFit`: true para exibir linha de tendência
- `bestFitTitle`: rótulo personalizado para linha de tendência
- `stacked`: true para empilhar conjuntos de dados (para gráficos de barra e linha)

Temas e Cores

- Suporte a cores de tema: o plugin pode usar cores da UI/tema do Obsidian
- `backgroundColor` e `borderColor` por série na definição da série
- Exportação de imagem: formato configurável (PNG, JPG) e qualidade

### Plugin Obsidian Charts — Exemplos

1) Cores por série e tipos mistos
```yaml
```chart
type: "bar"
labels: ["Seg","Ter","Qua"]
series:
  - title: "Vendas"
    data: [12, 19, 3]
```
```

- Gráfico misto (dois tipos)
```yaml
```chart
labels: ["Q1","Q2","Q3"]
series:
  - title: "Receita"
    data: [100,120,140]
    type: "bar"
  - title: "Crescimento"
    data: [5,7,9]
    type: "line"
```
```

Avançado: incluir `options` do Chart.js

- Você pode frequentemente incluir `options:` no YAML para passar configurações do Chart.js (escalas, plugins, configurações de animação). O suporte exato depende da implementação do plugin e do parsing YAML. Exemplo:

```yaml
```chart
type: "line"
labels: ["Jan","Fev"]
series:
  - title: "A"
    data: [1,2]
options:
  plugins:
    legend:
      display: true
```
```


## 3) Chart.js Cheat-sheet (configuração comum)

Uso básico (navegador)

- Inclua o Chart.js via CDN ou npm e crie um elemento canvas.

Exemplo básico em JS

```js
const ctx = document.getElementById('myChart').getContext('2d');
const myChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Jan','Fev','Mar'],
    datasets: [{
      label: 'Série A',
      data: [10, 20, 15],
      fill: false,
      borderColor: 'rgb(75, 192, 192)'
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { display: true }},
    scales: { x: { display: true }, y: { beginAtZero: true }}
  }
});
```

Opções importantes

- `type`: 'line' | 'bar' | 'pie' | 'doughnut' | 'radar' | 'polarArea' | 'bubble' | 'scatter'
- `data.labels`: rótulos do eixo x
- `data.datasets`: array de conjuntos de dados (rótulo, dados, backgroundColor, borderColor, borderWidth, yAxisID)
- `options.responsive`: true/false
- `options.maintainAspectRatio` / `aspectRatio`
- `options.plugins.legend`: `display`, `position`, `labels` estilização
- `options.plugins.tooltip`: `mode`, `callbacks` para rótulos personalizados
- `options.scales`: configurações de eixos (`x`, `y`, múltiplos eixos com IDs)
- `animations`: configurações de animação por propriedade (duração, easing)

Exemplos de escala e eixos

- Eixo y linear com min/max e formatação de ticks
```js
options: {
  scales: {
    y: {
      min: 0,
      max: 100,
      ticks: { callback: v => v + ' unidades' }
    }
  }
}
```

Múltiplos conjuntos de dados e eixos

- Atribua `yAxisID` aos conjuntos de dados e defina os eixos em `options.scales`.

Decimação e desempenho

- Use `parsing: false` ao fornecer arrays de dados pré-analisados de objetos {x,y}.
- Use o plugin de decimação ou a opção `decimation` para amostrar grandes conjuntos de dados.
- Tree-shaking: importe apenas os controladores/elementos necessários se estiver usando a construção ESM.

Plugins

- O Chart.js suporta plugins (embutidos e de terceiros) para anotações, zoom, rótulos de dados.
- Configure em `options.plugins.<pluginId>`.

Callbacks de formatação

- Tooltips e ticks suportam funções de callback para formatação de texto personalizada.


## 4) Mapeamento: opções do Chart.js ↔ Obsidian Charts YAML

Visão geral: O plugin Charts do Obsidian aceita um bloco de código YAML simplificado que mapeia conceitualmente para `type`, `data.labels` e `data.datasets` do Chart.js. Para `options` avançadas, o plugin pode aceitar um objeto `options:` passado como YAML que mapeia diretamente para `options` do Chart.js.

Mapeamentos comuns

- `type` → Chart.js `type`
- `labels` → Chart.js `data.labels`
- `series` (array)
  - `title` → dataset `label`
  - `data` → dataset `data`
  - `type` (opcional por série) → dataset `type` (para gráficos mistos)
  - `backgroundColor`, `borderColor` podem ser definidos em `series` ou via `options`
- Obsidian `options:` → Chart.js `options` (escalas/plugins/animations)

Exemplo: definir min/max do eixo y via YAML

```yaml
```chart
type: "line"
labels: ["Jan","Fev","Mar"]
series:
  - title: "A"
    data: [10,20,15]
options:
  scales:
    y:
      min: 0
      max: 30
```
```

Limitações e dicas

- A indentação YAML do Obsidian deve ser exata; use o criador gráfico se tiver dúvidas.
- Algumas implementações de plugins podem sanitizar ou limitar quais opções do Chart.js são permitidas — teste blocos complexos de `options`.
- Para conjuntos de dados muito grandes, prefira arrays x/y pré-analisados e defina `parsing: false` se o plugin expuser essa opção.

---

## Exemplos Adicionais

Abaixo estão vários exemplos prontos para copiar, agrupados por ferramenta. Cuidado com a indentação ao colar no Obsidian; use o modo Preview para renderizar os blocos do Tracker.

### Exemplos do Obsidian Tracker

1) Rastreio de peso (valores do frontmatter)

```yaml
```tracker
searchType: frontmatter
searchTarget: weight
line:
  title: "Peso (kg)"
  yAxisLabel: "kg"
```
```

Notas: Adicione `weight: 70.2` no frontmatter da sua nota para registrar uma medição.

2) Pressão arterial (múltiplos valores por tag)

No conteúdo da sua nota diária: `#blood-pressure:180/120`

Bloco do Tracker:

```yaml
```tracker
searchType: tag
searchTarget: blood-pressure[0], blood-pressure[1]
line:
  title: "Pressão Arterial"
  lineColor: '#e76f51, #2a9d8f'
  yAxisLabel: 'mmHg'
```
```

3) Transferências financeiras usando caminho de tag aninhada

Exemplo de conteúdo da nota: `#finance/bank1/transfer:100USD`

```yaml
```tracker
searchType: tag
searchTarget: finance/bank1/transfer
line:
  title: "Transferências"
  yAxisLabel: "USD"
```
```

4) Extração por regex (passos)

```yaml
```tracker
searchType: text
searchTarget: 'walked\s+(?<value>[0-9]+)\s+steps'
line:
  title: "Passos"
  lineColor: '#4cc9f0'
```
```

5) Campo inline do Dataview (dvField)

Nota: Use `steps:: 1234` em uma nota.

```yaml
```tracker
searchType: dvField
searchTarget: steps
line:
  title: "Passos (dvField)"
```
```

6) Visualização mensal com limites e sequências (calendário)

```yaml
```tracker
searchType: tag
searchTarget: study
month:
  mode: circle
  threshold: 1
  thresholdType: GreaterThan
  showStreak: true
  showTodayRing: true
```
```

7) Exemplo de tabela (ler colunas específicas da tabela)

```yaml
```tracker
searchType: table
searchTarget: examples/data/Tables.md[0][0], examples/data/Tables.md[0][1]
line:
  title: "Exemplo de dados da tabela"
```
```

8) Mapeamento de texto para valor com textValueMap

```yaml
```tracker
searchType: text
searchTarget: 'mood: (\w+)'
textValueMap:
  happy: 5
  good: 4
  neutral: 3
  bad: 2
  sad: 1
bar:
  title: "Humor Diário"
```
```

9) Tracker com arquivos especificados apenas

```yaml
```tracker
searchType: frontmatter
searchTarget: weight
file: "Health/Daily.md,Health/Weekly.md"
specifiedFilesOnly: true
line:
  title: "Rastreamento de Peso"
  showPoint: true
```
```

10) Calendário com intensidade de sequência e anel de hoje

```yaml
```tracker
searchType: tag
searchTarget: exercise
folder: "Health"
month:
  mode: circle
  threshold: 1
  thresholdType: GreaterThan
  showStreak: true
  circleColorByStreak: true
  showTodayRing: true
  initMonth: 2025-11
```
```

11) Exemplo de expressão com first() e last()

```yaml
```tracker
searchType: frontmatter
searchTarget: steps
summary:
  template: "Primeiro: {{first()::0f}} | Último: {{last()::0f}} | Total: {{sum()::0f}} passos"
```
```

12) Gráfico de barras empilhadas com múltiplos conjuntos de dados

```yaml
```tracker
searchType: frontmatter
searchTarget: work, personal, hobby
stack: true
bar:
  title: "Distribuição do Tempo"
  barColor: ['#e74c3c', '#3498db', '#2ecc71']
```
```


### Plugin Obsidian Charts — Exemplos

1) Cores por série e tipos mistos

```yaml
```chart
labels: ["Jan","Fev","Mar"]
series:
  - title: "Receita"
    data: [100,120,140]
    type: "bar"
    backgroundColor: '#264653'
  - title: "Crescimento"
    data: [5,7,9]
    type: "line"
    borderColor: '#e76f51'
    fill: false
options:
  plugins:
    legend:
      position: top
```
```

2) Gráfico de donut com raio interno e rótulos

```yaml
```chart
type: "doughnut"
labels: ["A","B","C"]
series:
  - title: "Participação"
    data: [0.5,0.3,0.2]
options:
  cutout: '50%'
  plugins:
    legend:
      position: right
```
```

3) Formatação de tooltip via opções (se suportado pelo plugin)

```yaml
```chart
type: "bar"
labels: ["Q1","Q2"]
series:
  - title: "Vendas"
    data: [12000, 15000]
options:
  plugins:
    tooltip:
      callbacks:
        label: "function(context) { return '$' + context.parsed.y.toLocaleString(); }"
```
```


### Exemplos Específicos do Obsidian

1) Largura responsiva e proporção de aspecto

```yaml
```chart
type: "line"
width: "80%"
fitPanelWidth: true
aspectRatio: 2
labels: ["Jan","Fev","Mar","Abr"]
series:
  - title: "Receita"
    data: [100, 120, 140, 160]
```
```

2) Controle de eixo com títulos e eixos invertidos

```yaml
```chart
type: "bar"
indexAxis: "y"
xTitle: "Vendas ($)"
yTitle: "Regiões"
labels: ["Norte","Sul","Leste","Oeste"]
series:
  - title: "Q1"
    data: [50, 40, 60, 35]
xReverse: false
beginAtZero: true
```
```

3) Gráfico de barras empilhadas

```yaml
```chart
type: "bar"
stacked: true
labels: ["Jan","Fev","Mar"]
series:
  - title: "Produto A"
    data: [30, 40, 35]
  - title: "Produto B"
    data: [20, 30, 25]
  - title: "Produto C"
    data: [10, 15, 12]
legend: true
legendPosition: top
```
```

4) Gráfico de linha com tensão e spanGaps

```yaml
```chart
type: "line"
tension: 0.4
spanGaps: true
labels: ["Semana 1","Semana 2","Semana 3","Semana 4","Semana 5"]
series:
  - title: "Conclusão %"
    data: [25, 40, null, 60, 75]
yTitle: "Porcentagem (%)"
beginAtZero: true
```
```

5) Gráfico com linha de tendência (bestFit)

```yaml
```chart
type: "scatter"
bestFit: true
bestFitTitle: "Tendência"
series:
  - title: "Pontos de Dados"
    data: [{x: 1, y: 10}, {x: 2, y: 15}, {x: 3, y: 12}, {x: 4, y: 20}]
xTitle: "Tempo"
yTitle: "Valor"
```
```

6) Intervalos de ticks de eixo personalizados e rótulos

```yaml
```chart
type: "line"
xAxisTickInterval: 50
yAxisTickInterval: 100
labels: ["0","50","100","150","200"]
series:
  - title: "Desempenho"
    data: [10, 50, 120, 180, 220]
xTitle: "Distância (m)"
yTitle: "Tempo (s)"
```
```

7) Gráfico semi-transparente com largura personalizada

```yaml
```chart
type: "pie"
width: "50%"
transparency: 0.8
labels: ["Vermelho","Azul","Verde","Amarelo"]
series:
  - title: "Distribuição"
    data: [30, 25, 20, 25]
legend: true
legendPosition: right
```
```


## 3) Integração do Obsidian Charts + DataviewJS

Propósito: Criar gráficos dinâmicos que consultam seu vault usando DataviewJS, e depois renderizar com o plugin Obsidian Charts.

DataviewJS permite que você consulte notas e gere dados prontos para gráfico. Isso é mais poderoso do que gráficos estáticos, pois pode puxar dados em tempo real do seu vault.

Padrão básico

```js
```dataviewjs
// Consulta todas as páginas com uma propriedade de peso
const pages = dv.pages('#health').where(p => p.weight);

// Extrai datas e valores
const labels = pages.map(p => p.file.frontmatter.date);
const data = pages.map(p => p.weight);

// Retorna dados do gráfico (renderizados pelo plugin Obsidian Charts)
dv.el('div', `
\`\`\`chart
type: line
labels: ${JSON.stringify(labels)}
series:
  - title: Peso
    data: ${JSON.stringify(data)}
yTitle: Peso (kg)
\`\`\`
`);
```
```

Principais benefícios

- Consultar dados dinamicamente com filtros e condições DQL
- Combinar dados de múltiplos arquivos ou tags
- Calcular métricas derivadas (somas, médias, contagens)
- Atualizar automaticamente quando as notas mudam

Consultas DQL comuns para gráficos

- `dv.pages('#tag')` — obter páginas com uma tag
- `.where(p => p.property > value)` — filtrar por condição
- `.map(p => p.property)` — extrair campo específico
- `.groupBy(p => p.category)` — agrupar por campo
- `.sort(p => p.date, 'desc')` — ordenar resultados

Avançado: exemplo de painel dinâmico

```js
```dataviewjs
const data = dv.pages('tag: #expense')
  .groupBy(p => p.category)
  .map(g => ({ 
    category: g.key, 
    total: g.rows.reduce((sum, row) => sum + row.amount, 0) 
  }));

dv.el('div', `
\`\`\`chart
type: pie
labels: ${JSON.stringify(data.map(d => d.category))}
series:
  - title: Despesas por Categoria
    data: ${JSON.stringify(data.map(d => d.total))}
legend: true
\`\`\`
`);
```
```

---

## 4) Chart.js — Conceitos Básicos

### Chart.js — Conceitos Básicos

O Chart.js usa um sistema hierárquico de opções com múltiplos níveis:
- **Nível de gráfico:** aplica-se a todo o gráfico
- **Nível de conjunto de dados:** aplica-se a um conjunto de dados específico (ex.: cor da linha individual)
- **Nível de elemento:** configura pontos, barras, arcos
- **Nível de escala:** manipula eixos (x, y, y2, etc.)
- **Nível de plugin:** configuração para plugins (legenda, tooltip, anotação)
- **Nível de animação:** controle de animações em várias escalas

**Opções Globais vs. Locais**

Defina padrões globais para todos os gráficos:
```js
Chart.defaults.interaction.mode = 'nearest';
Chart.defaults.font.size = 12;
```

Substitua por opções específicas do gráfico:
```js
new Chart(ctx, {
  type: 'line',
  data: data,
  options: { interaction: { mode: 'index' } }  // substitui global
});
```

**Opções Comuns de Nível Raiz**

- `responsive` (true/false) — redimensiona automaticamente para o contêiner
- `maintainAspectRatio` (true/false) — preserva a proporção ao redimensionar
- `aspectRatio` (número) — proporção ao manterAspectRatio é verdadeiro
- `layout` — configurações de preenchimento e margem
- `interaction.mode` — como os tooltips interagem (nearest, index, point, dataset, x, y)
- `animation` — temporização e easing da animação
- `animation.duration` (ms), `animation.easing` (easeInOutQuart, linear, etc.)

**Opções Scriptable & Indexable**

Muitas opções aceitam funções (scriptable) ou arrays (indexable):

Scriptable (função baseada no contexto):
```js
options: {
  plugins: {
    legend: {
      labels: {
        color: function(ctx) { return ctx.dataset.label === 'Good' ? 'green' : 'red'; }
      }
    }
  }
}
```

Indexable (array com auto-loop):
```js
datasets: [{
  data: [10, 20, 30],
  backgroundColor: ['red', 'green', 'blue']  // ciclos se mais pontos de dados do que cores
}]
```

**Estilo de Fonte & Texto**

Opções de fonte padronizadas em todo o gráfico:
```js
options: {
  font: {
    family: 'Helvetica, Arial',
    size: 14,
    style: 'normal',  // 'italic', 'oblique', 'normal'
    weight: 'bold'
  },
  plugins: {
    legend: {
      labels: {
        font: { size: 16, weight: 'bold' }  // substitui fonte global
      }
    }
  }
}
```

**Opções Comuns de Cor & Borda**

Padronizado entre conjuntos de dados:
- `backgroundColor` — cor de preenchimento para barras, fatias de pizza, etc.
- `borderColor` — cor da borda
- `borderWidth` (número)
- `borderRadius` (número) — cantos arredondados em barras
- `borderDash` ([skip, space]) — linhas tracejadas
- `fill` (true/false) — preenche área sob a linha

### Chart.js — Exemplos

1) Múltiplos eixos (esquerda e direita)

```js
const ctx = document.getElementById('multi').getContext('2d');
const chart = new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['Jan','Fev','Mar'],
    datasets: [
      { label: 'Receita', data: [100,150,130], yAxisID: 'y' },
      { label: 'Conversão %', data: [2.4, 3.1, 2.9], type: 'line', yAxisID: 'yRight', borderColor: 'red', fill: false }
    ]
  },
  options: {
    scales: {
      y: { type: 'linear', position: 'left', beginAtZero: true },
      yRight: { type: 'linear', position: 'right', beginAtZero: true }
    }
  }
});
```

2) Dispersão & Bolha

Dispersão:
```js
new Chart(ctx, { type: 'scatter', data: { datasets: [{ label: 'Dispersão', data: [{x:1,y:2},{x:2,y:3}] }] } });
```

Bolha:
```js
new Chart(ctx, { type: 'bubble', data: { datasets: [{ label: 'Bolha', data: [{x:10,y:20,r:5}] }] } });
```

3) Decimação para grandes conjuntos de dados

```js
// habilite o plugin de decimação nas opções
options: {
  plugins: {
    decimation: { enabled: true, algorithm: 'lttb', samples: 1000 }
  }
}
```

4) Exemplo de callback de tooltip

```js
options: {
  plugins: {
    tooltip: {
      callbacks: {
        label: function(ctx) { return ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString(); }
      }
    }
  }
}
```

5) Modos de interação e comportamento do tooltip

```js
// 'nearest' — ponto de dado único mais próximo
options: { interaction: { mode: 'nearest' } }

// 'index' — todos os pontos no mesmo valor do eixo x
options: { interaction: { mode: 'index' } }

// 'dataset' — todos os pontos no mesmo conjunto de dados
options: { interaction: { mode: 'dataset' } }

// 'point' — apenas se o cursor estiver diretamente sobre o ponto
options: { interaction: { mode: 'point' } }

// 'x' — todos os pontos na mesma posição x
options: { interaction: { mode: 'x' } }

// 'y' — todos os pontos na mesma posição y
options: { interaction: { mode: 'y' } }
```

6) Layout responsivo com preenchimento e proporção de aspecto

```js
options: {
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 2,  // proporção largura:altura
  layout: {
    padding: {
      left: 20,
      right: 20,
      top: 10,
      bottom: 10
    }
  }
}
```

7) Configuração de animação

```js
options: {
  animation: {
    duration: 750,      // ms
    easing: 'easeInOutQuart',  // função de easing
    delay: function(ctx) { return ctx.dataIndex * 50; }  // animação em estalo
  }
}
```

8) Estilização por conjunto de dados (gráfico de barras com cores e bordas individuais)

```js
datasets: [{
  label: 'Vendas',
  data: [12, 19, 3, 5],
  backgroundColor: ['#264653', '#2a9d8f', '#e9c46a', '#f4a261'],
  borderColor: '#333',
  borderWidth: 2,
  borderRadius: 5,
  hoverBackgroundColor: '#ff6b6b'
}]
```

9) Gráfico de linha com gradiente e preenchimento

```js
options: {
  scales: {
    y: { beginAtZero: true, min: 0, max: 100 }
  },
  plugins: {
    filler: {
      propagate: true
    }
  }
},
data: {
  datasets: [{
    label: 'Progresso',
    data: [10, 25, 40, 65, 80],
    borderColor: '#264653',
    borderWidth: 3,
    fill: true,
    backgroundColor: 'rgba(38, 70, 83, 0.1)',
    tension: 0.4  // suavidade da curva
  }]
}
```

10) Bordas tracejadas e estilização personalizada

```js
datasets: [{
  label: 'Meta',
  data: [50, 50, 50],
  borderColor: '#e76f51',
  borderWidth: 2,
  borderDash: [5, 5],      // 5px traço, 5px espaço
  fill: false,
  pointStyle: 'triangle',
  pointRadius: 6
}]
```


### Exemplos de Mapeamento (Chart.js ↔ Obsidian YAML)

1) Mapear `yAxisID` do dataset e escalas

YAML do Obsidian (por série `type` e `yAxisID` personalizado via options):

```yaml
```chart
labels: ["Jan","Fev"]
series:
  - title: "A"
    data: [10,20]
    type: "bar"
  - title: "B"
    data: [1.5,2.2]
    type: "line"
options:
  scales:
    y:
      beginAtZero: true
    yRight:
      position: 'right'
  datasets:
    1:
      yAxisID: 'yRight'
```
```

Nota: o suporte do plugin para opções por dataset pode variar; se não suportado, use as opções do Chart.js diretamente quando o plugin permitir `options` brutas.


---

## 5) Recursos Avançados & Dicas

### Exportação de Imagem

Tanto o Obsidian Charts quanto o Chart.js suportam a exportação de gráficos como imagens:

Obsidian Charts
- Clique com o botão direito no gráfico e selecione "Exportar como imagem"
- Configure o formato (PNG, JPG) e a qualidade nas configurações do plugin
- Suporta dimensões personalizadas

Chart.js
```js
const canvas = document.querySelector('canvas');
const image = canvas.toDataURL('image/png');
const link = document.createElement('a');
link.href = image;
link.download = 'chart.png';
link.click();
```

### Dicas de Desempenho

- **Grandes conjuntos de dados:** Use o plugin de decimação para milhares de pontos de dados
- **Múltiplas séries:** Limite a 5-10 séries por gráfico para legibilidade
- **Animação:** Desative animações (`animation: { duration: 0 }`) em painéis com muitos gráficos
- **Responsivo:** Defina `maintainAspectRatio: false` para contêineres de tamanho fixo

### Problemas Comuns & Soluções

| Problema                   | Solução                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------- |
| Gráfico não renderizando   | Verifique se a indentação YAML está correta (2 espaços)                                           |
| Dados não atualizando      | Para Obsidian Charts: atualize a pré-visualização; Para Tracker: verifique os watchers de arquivo |
| Legenda sobrepondo gráfico | Use `legendPosition: 'top'` ou `'bottom'`                                                         |
| Eixos parecem errados      | Defina `beginAtZero: true` e valores explícitos de `min`/`max`                                    |
| Tooltip não aparecendo     | Verifique a configuração de `interaction.mode`; assegure-se de que os dados são numéricos         |

### Integração de Tema

Obsidian Charts pode usar as cores do tema do seu vault:

```yaml
```chart
type: bar
labels: ["A","B","C"]
series:
  - title: Dados
    data: [10, 20, 15]
# Deixe backgroundColor vazio para usar cores do tema
```
```

### Combinando Tracker + Charts

Padrão comum: Use o Tracker para coleta de dados, o plugin Charts para visualização:

1. O Tracker coleta dados de notas
2. O plugin Charts lê a saída do resumo do Tracker
3. Ou use DataviewJS para consultar dados rastreados e gerar gráficos

---

Referências

- docs do Chart.js: https://www.chartjs.org/docs/latest/
- noções básicas do plugin Obsidian Charts: https://charts.phib.ro/Meta/Charts/Basics
- Obsidian Tracker (pyrochlore): https://github.com/pyrochlore/obsidian-tracker

---

Gerado: 2025-11-27
Atualizado: 2025-11-27 (atualização abrangente)

**Últimos acréscimos:**
- Conceitos básicos do Chart.js (estrutura de configuração, opções globais, opções scriptable/indexable)
- Plugin Obsidian Charts: controles de eixo, modificadores de dados, gráficos empilhados, opções responsivas
- 7 novos exemplos do Obsidian Charts (largura, empilhamento, linhas de tendência, transparência, etc.)
- Obsidian Tracker: parâmetros avançados (textValueMap, specifiedFilesOnly, colorByStreak, showTodayRing)
- 6 novos exemplos do Tracker (mapeamento de texto, arquivos especificados, calendários, expressões)
- Integração do Obsidian Charts + DataviewJS para gráficos dinâmicos
- Seção de recursos avançados: exportação, dicas de desempenho, solução de problemas, integração de tema
