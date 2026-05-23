# 🔌 Conta Azul API v2 — Endpoints, Schemas e Gotchas

> Documento descoberto experimentalmente em 2026-05-22 testando contra
> `api-v2.contaazul.com/v1` com o tenant TABUAS. A documentação oficial
> está em https://developers.contaazul.com mas é incompleta/parcial.

## Base URL

```
https://api-v2.contaazul.com/v1
```

Todos os endpoints exigem `Authorization: Bearer <access_token>` obtido via OAuth2.

## Endpoints mapeados

| Recurso | Endpoint correto | Schema da resposta | Paginação |
|---|---|---|---|
| Categorias | `GET /categorias` | `{itens: [...], itens_totais}` | ❌ retorna tudo (até ~10 itens) |
| Pessoas (clientes/fornecedores) | `GET /pessoa` (singular!) | `{itens, itens_totais}` | `pagina`, `tamanho_pagina` |
| Produtos | `GET /produtos` | `{items, totalItems}` (note **inglês**) | `tamanho_pagina ∈ {10,20,50,100,200,500,1000}` |
| Serviços | `GET /servicos` | `{itens, itens_totais}` | sim |
| Vendedores | `GET /venda/vendedores` ⚠️ | **array no top-level** | ❌ retorna tudo |
| Vendas | `GET /venda/busca` ⚠️ | `{itens, paginacao}` | `pagina`, `tamanho_pagina`, **filtros obrigatórios** `data_inicio`, `data_fim` |
| Itens da venda | `GET /venda/{id}/itens` | `{itens, totais}` | `pagina`, `tamanho_pagina` |
| Contas a receber | `GET /financeiro/eventos-financeiros/contas-a-receber/buscar` ⚠️ | `{itens, paginacao}` | **`data_vencimento_de` obrigatório** + `data_vencimento_ate` |
| Contas a pagar | `GET /financeiro/eventos-financeiros/contas-a-pagar/buscar` ⚠️ | `{itens, paginacao}` | mesmo padrão |

⚠️ = endpoints frequentemente documentados com paths errados (alternativos `/v1/vendedor`, `/v1/venda`, `/v1/financeiro/contas-a-*` retornam 404 ou 502).

## Schemas reais (descobertos)

### `/venda/busca`

```json
{
  "id": "5b3e4725-d69c-4539-9c6b-cb655a58dd6e",
  "data": "2026-01-30",                         // ← issued_at
  "tipo": "SALE",
  "itens": "PRODUCT",                            // ← STRING, não array! Tipo dos itens
  "total": 0,                                    // ← sempre 0 no resumo; valor real está em /venda/{id}/itens
  "numero": 1,
  "versao": 1,
  "cliente": {                                   // ← objeto aninhado
    "id": "96541ac4-fe75-4678-a8d9-70a0dd0e6e7d",
    "nome": "VENDAS EM ESPECIE",
    "email": null,
    "uuid_legado": "d3dbc2b0-46da-49f2-9a56-fa1a3a2a4187"
  },
  "situacao": {                                  // ← objeto, não string
    "nome": "APROVADO",                          // APROVADO | CANCELADO | ESPERANDO_APROVACAO
    "descricao": "Aprovado"
  },
  "criado_em": "2026-02-03T10:23:04.346",
  "id_legado": 738161041,
  "data_alteracao": "2026-02-03T10:23:05.108",
  "condicao_pagamento": true
}
```

**Filtros aceitos**: `data_inicio`, `data_fim`, `termo_busca`, `campo_ordenado_ascendente`, `status` (`WAITING_APPROVED|APPROVED|CANCELED|ALL`).

### `/venda/{id}/itens`

```json
{
  "itens": [
    {"id": "...", "idProduto": "...", "quantidade": 5, "valorUnitario": "10.50", "valorTotal": "52.50"}
  ],
  "totais": {
    "total_produtos": 52.50,
    "total_servicos": 0,
    "total_nao_consolidados": 0
  }
}
```

### `/venda/vendedores`

```json
[
  {"id": "ce3343b2-29a2-44ef-a986-2c1d52f24643", "nome": "ALANE CRISTINA"},
  {"id": "c95bfb39-7e1b-4681-9a86-afd2515e9457", "nome": "Dieyson Dieyson"}
]
```

**Array no top-level**, sem `itens` envelope. Cliente HTTP precisa lidar com isso (no nosso código: `ContaAzulClient._extract_items` aceita list direto).

### `/financeiro/.../contas-a-receber/buscar` (e a-pagar)

```json
{
  "id": "7ead458c-eff9-44b8-8313-15597d03d4f4",
  "pago": 259.0,
  "total": 259.0,                                // ← amount está aqui (não em `valor`)
  "status": "ACQUITTED",                          // ACQUITTED | PENDING | OVERDUE | CANCELED
  "status_traduzido": "RECEBIDO",                 // RECEBIDO | EM_ABERTO | ATRASADO | CANCELADO
  "cliente": {                                    // pode ser {id: null, nome: null} (recebimento à vista anônimo)
    "id": null,
    "nome": null
  },
  "fornecedor": {                                 // apenas em contas-a-pagar
    "id": "...",
    "nome": "..."
  },
  "nao_pago": 0.0,
  "descricao": "PIX TRANSF ANGELA 02/06",
  "categorias": [                                 // ← ARRAY (mapeie [0].id)
    {"id": "3c81438f-...", "nome": "Receita com serviços"}
  ],
  "data_criacao": "2025-12-04T10:35:23.716842",
  "renegociacao": null,
  "data_alteracao": "2025-12-04T10:35:23.716842",  // ← use como paid_at quando status=ACQUITTED
  "data_vencimento": "2025-06-02",
  "data_competencia": "2025-06-02",
  "centros_de_custo": []
  // Note: NÃO há `data_pagamento` explícito
}
```

**Filtros obrigatórios**: `data_vencimento_de`, `data_vencimento_ate`. Outros: `data_competencia_de/_ate`, `data_pagamento_de/_ate`, `data_alteracao_de/_ate`, `valor_de/_ate`, `status`, `ids_contas_financeiras`, `ids_categorias`, `ids_centros_de_custo`, `ids_clientes`.

### `/produtos`

```json
{
  "id": "d4afcc36-2cc3-4a2c-b1ef-053ac3426bc6",
  "ean": "7908000409669",
  "nome": "ALÇA CLIPER - TURQUESA",
  "tipo": "PRODUCT",
  "saldo": 7,                                    // ← estoque atual
  "codigo": "1026550448",                        // ← SKU
  "movido": false,
  "status": "ATIVO",                             // ATIVO | INATIVO
  "id_legado": 460911644,
  "custo_medio": 56.7,                           // ← custo (não `valorCusto`)
  "valor_venda": 0,                              // ← preço (frequentemente 0 quando não cadastrado)
  "nivel_estoque": "PADRAO",
  "estoque_maximo": 0,
  "estoque_minimo": 0,
  "produtos_variacao": [],
  "contagem_agregacao": 0,
  "ultima_atualizacao": "2025-11-26T11:02:31.397889Z",
  "integracao_ecommerce_ativada": false
}
```

### `/pessoa`

```json
{
  "nome": "ALEXANDRE MAGNO SANTOS DE CARVALHO JUNIOR",
  "uuid": "54fbae56-ea58-410d-8596-d6aa1f4c1fc8",  // ← usar como external_id (não `id`)
  "ativo": true,
  "email": null,                                    // frequentemente null
  "perfis": ["Cliente"],                            // ["Cliente"] | ["Fornecedor"] | ambos
  "endereco": null,
  "telefone": null,
  "documento": null,                                // CPF/CNPJ — frequentemente null
  "id_legado": 467361472,
  "tipo_pessoa": "FISICA",                          // FISICA | JURIDICA
  "uuid_legado": "c48e313a-6b1b-4441-b50b-fbb76a12de08",
  "inscricao_estadual": null
}
```

## Gotchas conhecidos

### 1. Categorias incompletas em `/categorias`

O endpoint `/categorias` retorna apenas **10 categorias** mesmo com paginação configurada. As categorias reais aparecem **dentro do payload financeiro** (`categorias[]`).

**Solução adotada** (em `apps/sync/orchestrator.py`): durante `sync_financial`, chamamos `_ensure_categories_from_payload(tenant_id, item, kind)` para criar/atualizar `Category` a partir de cada lançamento. Tenant TABUAS passou de 10 para 78 categorias no banco.

### 2. `paid_at` não existe no payload

O financeiro v2 não retorna `data_pagamento`. Quando `status=ACQUITTED` ("pago/recebido"), usamos **`data_alteracao` como proxy** (momento em que o status mudou).

Em `apps/sync/mappers.py:map_financial_entry`:
```python
if paid_at is None and status == "paid":
    paid_at = _to_date(
        payload.get("data_alteracao")
        or payload.get("data_competencia")
    )
```

### 3. Cliente/Fornecedor frequentemente `null`

TABUAS (varejo) recebe pelo financeiro com `cliente: {id: null, nome: null}` em 99% dos lançamentos. Em pagamentos a fornecedores, 50% têm `fornecedor` identificado.

**Implicação**: `top_receivable_customers` é quase sempre vazio para varejo. Por isso a página de Clientes mostra recebimentos onde está, mas o foco da TABUAS é a movimentação por categoria, não por pessoa.

### 4. Status em UPPERCASE com prefixos diferentes

A API mistura padrões:
- Sales: `APROVADO | CANCELADO | ESPERANDO_APROVACAO` (PT-BR UPPERCASE)
- Financeiro: `ACQUITTED | PENDING | OVERDUE | CANCELED` (inglês) + `status_traduzido` (`RECEBIDO | EM_ABERTO | ATRASADO`)

Mapper trata tudo via `_status_text(payload, "situacao", "status")` que extrai `.nome` de objetos aninhados e normaliza para lowercase.

### 5. `itens` na venda é STRING, não array

No payload de listagem do `/venda/busca`, `itens` vem como `"PRODUCT"` ou `"SERVICE"` (tipo). O array real de itens fica em `/venda/{id}/itens`. Nosso `sync_sales` faz a chamada extra por venda.

### 6. Endpoint `/categorias` sem `pagina`/`tamanho_pagina`

Em `apps/sync/orchestrator.py`, `categories` está em `RESOURCES_WITHOUT_PAGINATION` para evitar enviar params que causariam 400. Idem para `salespeople` (`/venda/vendedores` retorna array direto).

### 7. Filtros obrigatórios no financeiro

`data_vencimento_de` é **obrigatório** em `/financeiro/.../buscar`. Se omitido, retorna 400 — `"O parâmetro obrigatório 'data_vencimento_de' não foi informado."`. Em `sync_financial` enviamos sempre uma janela de 365 dias para trás + 365 para frente.

## OAuth2

Endpoint de autorização: `https://auth.contaazul.com/oauth2/authorize`
Token: `https://auth.contaazul.com/oauth2/token`

Scope: `openid profile aws.cognito.signin.user.admin`

App de **desenvolvimento** (portaldevs.contaazul.com) tem `redirect_uri` **fixo** em `https://contaazul.com`. Por isso o BI AZUL suporta `redirect_uri_override` no `ContaAzulConnection` e tem dois caminhos alternativos para extrair o `code` (manual ou via interface dev).

## Como adicionar novo endpoint

1. Mapear o path em `apps/sync/orchestrator.py:RESOURCE_ENDPOINTS`
2. Se não paginar, adicionar em `RESOURCES_WITHOUT_PAGINATION`
3. Adicionar `RawPayload.Resource.*` no model `sync/models.py`
4. Criar mapper `map_<recurso>` em `apps/sync/mappers.py`
5. Adicionar função `sync_<recurso>(tenant_id, client)` no orchestrator
6. Incluir em `order` dentro de `sync_tenant`
7. Adicionar payload de mock em `apps/sync/tests/test_orchestrator.py`
