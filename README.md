# YouTube Transcript API

Microserviço REST para obter transcrições de vídeos do YouTube usando Python + FastAPI + youtube-transcript-api.

## 🚀 Características

- ✅ Endpoint de healthcheck
- ✅ Busca de transcrição por `video_id` do YouTube
- ✅ Suporte a múltiplos idiomas com fallback
- ✅ Formato de resposta: texto simples ou JSON com segmentos e timestamps
- ✅ Autenticação opcional via API Key
- ✅ CORS configurável
- ✅ Cache em memória (LRU) para otimização
- ✅ Tratamento robusto de erros
- ✅ Logs estruturados com request_id
- ✅ Pronto para deploy no Coolify

## 📋 Requisitos

- Python 3.11+
- Docker (para build e deploy)

## 🏃 Executando Localmente

### Opção 1: Com uvicorn direto

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar servidor
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Opção 2: Com Docker

```bash
# Build da imagem
docker build -t yt-transcript-api .

# Executar container
docker run -p 8000:8000 \
  -e API_KEY=seu-api-key-opcional \
  -e CORS_ORIGINS="*" \
  -e CACHE_TTL_SECONDS=3600 \
  yt-transcript-api
```

## 🐳 Build Docker

```bash
docker build -t yt-transcript-api .
```

## 🚢 Deploy no Coolify

### 1. Preparação

- Faça push do código para um repositório Git (GitHub, GitLab, etc.)

### 2. Configuração no Coolify

1. **Criar novo recurso** → **Aplicação** → **Docker Compose** ou **Dockerfile**
2. **Conectar repositório Git**
3. **Configurar Dockerfile**:
   - Caminho do Dockerfile: `Dockerfile`
   - Porta: `8000`
4. **Configurar domínio** (opcional):
   - Adicione um domínio personalizado nas configurações
   - O Coolify configurará automaticamente o proxy reverso

### 3. Variáveis de Ambiente

Configure as seguintes variáveis de ambiente no Coolify:

| Variável | Descrição | Padrão | Obrigatório |
|----------|-----------|--------|-------------|
| `API_KEY` | Chave de API para autenticação (deixe vazio para desabilitar) | - | Não |
| `CORS_ORIGINS` | Origens permitidas para CORS (separadas por vírgula ou `*` para todas) | `*` | Não |
| `CACHE_TTL_SECONDS` | Tempo de vida do cache em segundos | `3600` | Não |
| `PORT` | Porta do servidor | `8000` | Não |

**Exemplo de configuração no Coolify:**
```
API_KEY=minha-chave-secreta-123
CORS_ORIGINS=https://meusite.com,https://app.meusite.com
CACHE_TTL_SECONDS=7200
```

### 4. Deploy

- Clique em **Deploy** no Coolify
- Aguarde o build e deploy completarem
- Acesse via URL fornecida pelo Coolify ou domínio configurado

## 📡 Endpoints

### GET /health

Healthcheck do serviço.

**Resposta:**
```json
{
  "ok": true,
  "service": "yt-transcript",
  "version": "1.0.0"
}
```

### GET /transcript/{video_id}

Obtém a transcrição de um vídeo do YouTube.

**Parâmetros:**
- `video_id` (path): ID do vídeo do YouTube (ex: `dQw4w9WgXcQ`)
- `lang` (query, opcional): Idioma preferencial (ex: `pt-BR`, `pt`, `en`, `es`)
- `format` (query, opcional): Formato de resposta - `text` ou `json` (padrão: `json`)

**Headers (se API_KEY configurada):**
- `x-api-key`: Chave de API

**Resposta (format=json):**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "text": "Texto completo da transcrição...",
  "language_used": "pt-BR",
  "segments": [
    {
      "text": "Primeiro segmento",
      "start": 0.0,
      "duration": 3.5
    },
    {
      "text": "Segundo segmento",
      "start": 3.5,
      "duration": 2.8
    }
  ],
  "request_id": "uuid-do-request"
}
```

**Resposta (format=text):**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "text": "Texto completo da transcrição...",
  "request_id": "uuid-do-request"
}
```

## 🔒 Autenticação

Se a variável de ambiente `API_KEY` estiver configurada, todas as requisições ao endpoint `/transcript/{video_id}` devem incluir o header:

```
x-api-key: sua-chave-api
```

Se o header estiver ausente ou incorreto, será retornado `401 Unauthorized`.

## 📝 Exemplos de Uso

### cURL

**Sem autenticação (se API_KEY não configurada):**
```bash
# Healthcheck
curl http://localhost:8000/health

# Obter transcrição em JSON
curl "http://localhost:8000/transcript/dQw4w9WgXcQ?format=json&lang=pt-BR"

# Obter apenas texto
curl "http://localhost:8000/transcript/dQw4w9WgXcQ?format=text"
```

**Com autenticação:**
```bash
curl -H "x-api-key: sua-chave-api" \
  "http://localhost:8000/transcript/dQw4w9WgXcQ?format=json&lang=pt-BR"
```

### n8n (HTTP Request Node)

**Configuração do n8n:**

1. Adicione um nó **HTTP Request**
2. Configure:
   - **Method**: `GET`
   - **URL**: `https://seu-dominio.com/transcript/{{$json.videoId}}`
   - **Query Parameters**:
     - `format`: `json`
     - `lang`: `pt-BR`
   - **Headers** (se API_KEY configurada):
     - `x-api-key`: `sua-chave-api`

**Exemplo de workflow n8n:**

```json
{
  "nodes": [
    {
      "parameters": {
        "method": "GET",
        "url": "https://seu-dominio.com/transcript/dQw4w9WgXcQ",
        "options": {
          "queryParameters": {
            "parameters": [
              {
                "name": "format",
                "value": "json"
              },
              {
                "name": "lang",
                "value": "pt-BR"
              }
            ]
          },
          "headers": {
            "x-api-key": "sua-chave-api"
          }
        }
      },
      "name": "Get Transcript",
      "type": "n8n-nodes-base.httpRequest"
    }
  ]
}
```

### Python

```python
import requests

# Sem autenticação
response = requests.get(
    "http://localhost:8000/transcript/dQw4w9WgXcQ",
    params={"format": "json", "lang": "pt-BR"}
)
data = response.json()
print(data["text"])

# Com autenticação
headers = {"x-api-key": "sua-chave-api"}
response = requests.get(
    "http://localhost:8000/transcript/dQw4w9WgXcQ",
    params={"format": "json"},
    headers=headers
)
```

### JavaScript/Node.js

```javascript
// Sem autenticação
const response = await fetch(
  'http://localhost:8000/transcript/dQw4w9WgXcQ?format=json&lang=pt-BR'
);
const data = await response.json();
console.log(data.text);

// Com autenticação
const response = await fetch(
  'http://localhost:8000/transcript/dQw4w9WgXcQ?format=json',
  {
    headers: {
      'x-api-key': 'sua-chave-api'
    }
  }
);
```

## ⚠️ Tratamento de Erros

O serviço retorna códigos HTTP apropriados para diferentes situações:

| Código | Erro | Descrição |
|--------|------|-----------|
| 400 | `invalid_format` | Formato inválido (deve ser `text` ou `json`) |
| 401 | `unauthorized` | API Key ausente ou inválida |
| 404 | `no_transcript` | Transcrição não disponível para o vídeo |
| 404 | `video_unavailable` | Vídeo indisponível |
| 429 | `rate_limited` | Rate limit do YouTube excedido |
| 500 | `internal_error` | Erro interno do servidor |

**Exemplo de resposta de erro:**
```json
{
  "error": "no_transcript",
  "message": "Sem transcrição/legenda disponível para este vídeo.",
  "request_id": "uuid-do-request"
}
```

## 🔍 Observabilidade

- Todos os requests recebem um `request_id` único (UUID)
- O `request_id` é retornado no header `X-Request-Id` e no corpo da resposta JSON
- Logs estruturados são gerados para cada requisição
- Erros são logados no servidor (sem expor stacktrace ao cliente)

## ⚡ Performance

- **Cache em memória**: Cache LRU com até 256 entradas
- **TTL configurável**: Tempo de vida do cache via `CACHE_TTL_SECONDS` (padrão: 3600s)
- **Otimização**: Requisições repetidas para o mesmo vídeo/idioma são servidas do cache

## 📌 Limitações

1. **Transcrições disponíveis**: Nem todos os vídeos do YouTube possuem transcrições/legendas disponíveis. O serviço retornará `404` nestes casos.

2. **Idiomas**: Se o idioma solicitado não estiver disponível, o serviço tentará:
   - Buscar em idiomas de fallback (`pt-BR`, `pt`, `pt-PT`, `en`)
   - Traduzir automaticamente se disponível

3. **Rate Limiting**: O YouTube pode aplicar rate limiting. O serviço retorna `429` quando isso ocorre.

4. **Vídeos privados/removidos**: Vídeos privados, removidos ou indisponíveis retornarão `404`.

## 🛠️ Desenvolvimento

### Estrutura do Projeto

```
.
├── main.py              # Aplicação FastAPI
├── requirements.txt     # Dependências Python
├── Dockerfile          # Imagem Docker
├── .dockerignore       # Arquivos ignorados no build
└── README.md           # Esta documentação
```

### Testes Locais

```bash
# Testar healthcheck
curl http://localhost:8000/health

# Testar transcrição
curl "http://localhost:8000/transcript/dQw4w9WgXcQ?format=json"
```

## 📄 Licença

Este projeto é fornecido como está, sem garantias.

## 🤝 Contribuindo

Sinta-se à vontade para abrir issues ou pull requests com melhorias!

