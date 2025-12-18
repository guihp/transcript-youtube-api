"""
Microserviço de transcrição do YouTube
FastAPI + youtube-transcript-api
"""
import os
import uuid
import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests,
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações do ambiente
API_KEY = os.getenv("API_KEY", "").strip()
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").strip()
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
PORT = int(os.getenv("PORT", "8000"))

# Cache simples em memória
cache: dict = {}
CACHE_MAX_SIZE = 256

app = FastAPI(
    title="YouTube Transcript API",
    description="Microserviço para obter transcrições de vídeos do YouTube",
    version="1.0.0"
)

# CORS
cors_origins = CORS_ORIGINS.split(",") if CORS_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_cache_key(video_id: str, lang: str) -> str:
    """Gera chave única para cache"""
    return f"{video_id}:{lang}"


def get_from_cache(key: str) -> Optional[dict]:
    """Recupera do cache se ainda válido"""
    if key not in cache:
        return None
    
    entry = cache[key]
    if datetime.now() > entry["expires_at"]:
        del cache[key]
        return None
    
    return entry["data"]


def set_cache(key: str, data: dict):
    """Armazena no cache com TTL"""
    # Limpar cache se exceder tamanho máximo (LRU simples)
    if len(cache) >= CACHE_MAX_SIZE:
        # Remove a entrada mais antiga
        oldest_key = min(cache.keys(), key=lambda k: cache[k]["expires_at"])
        del cache[oldest_key]
    
    cache[key] = {
        "data": data,
        "expires_at": datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)
    }


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="x-api-key")):
    """Middleware para verificar API Key se configurada"""
    if API_KEY:
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized"}
            )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Adiciona request_id a cada requisição"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    logger.info(f"Request {request_id}: {request.method} {request.url.path}")
    
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
async def healthcheck():
    """Endpoint de healthcheck"""
    return {
        "ok": True,
        "service": "yt-transcript",
        "version": "1.0.0"
    }


@app.get("/transcript/{video_id}")
async def get_transcript(
    video_id: str,
    lang: Optional[str] = Query(None, description="Idioma preferencial (ex: pt-BR, pt, en)"),
    format: str = Query("json", description="Formato de resposta: 'text' ou 'json'"),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    request: Request
):
    """
    Obtém transcrição de um vídeo do YouTube
    
    - **video_id**: ID do vídeo do YouTube
    - **lang**: Idioma preferencial (padrão: pt-BR, pt, pt-PT, en)
    - **format**: 'text' para apenas texto, 'json' para texto + segmentos
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # Verificar API Key se configurada
    if API_KEY:
        if not x_api_key or x_api_key != API_KEY:
            logger.warning(f"Request {request_id}: Unauthorized access attempt")
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized"}
            )
    
    # Validar formato
    if format not in ["text", "json"]:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_format", "message": "Formato deve ser 'text' ou 'json'"}
        )
    
    # Determinar idiomas a tentar
    if lang:
        languages = [lang]
    else:
        languages = ["pt-BR", "pt", "pt-PT", "en"]
    
    # Verificar cache
    cache_key = get_cache_key(video_id, ",".join(languages))
    cached_result = get_from_cache(cache_key)
    if cached_result:
        logger.info(f"Request {request_id}: Cache hit for video {video_id}")
        result = cached_result.copy()
        result["request_id"] = request_id
        
        # Ajustar formato se necessário
        if format == "text":
            return {
                "video_id": result["video_id"],
                "text": result["text"],
                "request_id": request_id
            }
        return result
    
    # Buscar transcrição
    try:
        logger.info(f"Request {request_id}: Fetching transcript for video {video_id} with languages {languages}")
        
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Tentar obter transcrição nos idiomas preferidos
        transcript = None
        language_used = None
        
        # Tentar encontrar transcrição nos idiomas preferidos
        for preferred_lang in languages:
            try:
                transcript = transcript_list.find_transcript([preferred_lang])
                language_used = preferred_lang
                break
            except (NoTranscriptFound, TranscriptsDisabled):
                # Se não encontrar no idioma, tentar traduzir
                try:
                    # Pegar primeiro idioma disponível e traduzir
                    available_transcripts = list(transcript_list)
                    if available_transcripts:
                        transcript = available_transcripts[0].translate(preferred_lang)
                        language_used = preferred_lang
                        break
                except:
                    continue
            except:
                continue
        
        if not transcript:
            raise NoTranscriptFound(video_id, languages, None)
        
        # Obter dados da transcrição
        transcript_data = transcript.fetch()
        
        # Montar texto completo
        full_text = " ".join([item["text"] for item in transcript_data])
        
        # Preparar resposta
        result = {
            "video_id": video_id,
            "text": full_text,
            "language_used": language_used or "unknown",
            "request_id": request_id
        }
        
        if format == "json":
            # Formatar segmentos
            segments = []
            for item in transcript_data:
                segments.append({
                    "text": item["text"],
                    "start": item["start"],
                    "duration": item.get("duration", 0)
                })
            result["segments"] = segments
        
        # Armazenar no cache
        set_cache(cache_key, result)
        
        logger.info(f"Request {request_id}: Successfully fetched transcript for video {video_id}")
        
        # Retornar conforme formato solicitado
        if format == "text":
            return {
                "video_id": result["video_id"],
                "text": result["text"],
                "request_id": request_id
            }
        
        return result
        
    except TranscriptsDisabled:
        logger.warning(f"Request {request_id}: Transcripts disabled for video {video_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "no_transcript",
                "message": "Sem transcrição/legenda disponível para este vídeo.",
                "request_id": request_id
            }
        )
    except NoTranscriptFound:
        logger.warning(f"Request {request_id}: No transcript found for video {video_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "no_transcript",
                "message": "Sem transcrição/legenda disponível para este vídeo.",
                "request_id": request_id
            }
        )
    except VideoUnavailable:
        logger.warning(f"Request {request_id}: Video unavailable: {video_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "video_unavailable",
                "message": "Vídeo indisponível.",
                "request_id": request_id
            }
        )
    except TooManyRequests:
        logger.error(f"Request {request_id}: Rate limited for video {video_id}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "Rate limit do YouTube. Tente novamente mais tarde.",
                "request_id": request_id
            }
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Request {request_id}: Internal error for video {video_id}: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Erro interno.",
                "detail": error_msg[:100] if error_msg else "Erro desconhecido",
                "request_id": request_id
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

