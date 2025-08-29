"""
FastAPI server module

Implements HTTP service and API endpoints
"""

import asyncio
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from . import __version__
from .config import config
from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorResponse,
    ErrorDetail,
    HealthResponse,
    ModelsResponse,
    ModelInfo
)
from .openai_adapter import openai_adapter

# Configure logging (will be updated when config is set)
logging.basicConfig(
    level=logging.INFO,  # Default level, will be updated in CLI
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gemini_cli_proxy')

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Ensure logging level is applied after uvicorn starts
    logging.getLogger('gemini_cli_proxy').setLevel(getattr(logging, config.log_level.upper()))
    
    logger.info(f"Starting Gemini CLI Proxy v{__version__}")
    logger.info(f"Configuration: port={config.port}, rate_limit={config.rate_limit}/min, concurrency={config.max_concurrency}")
    logger.debug(f"Debug logging is enabled (log_level={config.log_level})")
    yield
    logger.info("Shutting down Gemini CLI Proxy")


# Create FastAPI application
app = FastAPI(
    title="Gemini CLI Proxy",
    description="OpenAI-compatible API wrapper for Gemini CLI",
    version=__version__,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception occurred while processing request: {exc}")
    logger.error(f"Exception details: {traceback.format_exc()}")
    
    error_response = ErrorResponse(
        error=ErrorDetail(
            message="Internal server error",
            type="internal_error",
            code="500"
        )
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(version=__version__)


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models():
    """List available models"""
    models = [
        ModelInfo(id=model_id) for model_id in config.supported_models
    ]
    
    return ModelsResponse(data=models)


@app.post("/v1/v1beta/models/{model_name:path}:streamGenerateContent")
@limiter.limit(f"{config.rate_limit}/minute")
async def google_chat_completions_stream(
    model_name: str,
    request: Request
):
    """
    Google-compatible streaming chat completion endpoint
    
    Translates Google's streamGenerateContent to OpenAI's chat completion stream
    """
    logger.info(f"Received Google-style stream request for model: {model_name}")
    
    try:
        # Get request body
        google_request_body = await request.json()
        
        # Transform Google request to OpenAI request
        messages = []
        if "contents" in google_request_body:
            for content in google_request_body["contents"]:
                role = content.get("role", "user")
                if role == "model":
                    role = "assistant"
                
                text_parts = [part.get("text", "") for part in content.get("parts", []) if "text" in part]
                full_content = "".join(text_parts)
                
                if full_content:
                    messages.append({"role": role, "content": full_content})

        # Create OpenAI-compatible request
        chat_request_data = {
            "model": model_name,
            "messages": messages,
            "stream": True
        }
        
        # Add other potential parameters if they exist and are compatible
        if "generationConfig" in google_request_body:
            gen_config = google_request_body["generationConfig"]
            if "temperature" in gen_config:
                chat_request_data["temperature"] = gen_config["temperature"]
            if "topP" in gen_config:
                chat_request_data["top_p"] = gen_config["topP"]
            if "maxOutputTokens" in gen_config:
                chat_request_data["max_tokens"] = gen_config["maxOutputTokens"]

        chat_request = ChatCompletionRequest(**chat_request_data)
        
        logger.info(f"Translated to OpenAI-style request: model={chat_request.model}, stream={chat_request.stream}")

        # Validate model
        if chat_request.model not in config.supported_models:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error=ErrorDetail(
                        message=f"Unsupported model: {chat_request.model}. Supported models: {', '.join(config.supported_models)}",
                        type="invalid_request_error",
                        param="model"
                    )
                ).model_dump()
            )
        
        # Use the existing streaming logic
        return await openai_adapter.chat_completion_stream(chat_request)

    except HTTPException:
        raise
    except asyncio.TimeoutError:
        logger.error("Gemini CLI command execution timeout (from Google-style endpoint)")
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message="Gemini CLI command execution timeout",
                    type="bad_gateway",
                    code="502"
                )
            ).model_dump()
        )
    except RuntimeError as e:
        logger.error(f"Gemini CLI execution error (from Google-style endpoint): {e}")
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message=str(e),
                    type="bad_gateway",
                    code="502"
                )
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error processing Google-style stream request: {e}")
        logger.error(f"Exception details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message="Internal server error",
                    type="internal_error",
                    code="500"
                )
            ).model_dump()
        )


@app.post("/v1/chat/completions")
@limiter.limit(f"{config.rate_limit}/minute")
async def chat_completions(
    chat_request: ChatCompletionRequest,
    request: Request
):
    """
    Chat completion endpoint
    
    Implements OpenAI-compatible chat completion API
    """
    logger.info(f"Received chat completion request: model={chat_request.model}, stream={chat_request.stream}")
    
    try:
        # Validate model
        if chat_request.model not in config.supported_models:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error=ErrorDetail(
                        message=f"Unsupported model: {chat_request.model}. Supported models: {', '.join(config.supported_models)}",
                        type="invalid_request_error",
                        param="model"
                    )
                ).model_dump()
            )
        
        # Handle streaming request
        if chat_request.stream:
            return await openai_adapter.chat_completion_stream(chat_request)
        
        # Handle non-streaming request
        response = await openai_adapter.chat_completion(chat_request)
        return response
        
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        logger.error("Gemini CLI command execution timeout")
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message="Gemini CLI command execution timeout",
                    type="bad_gateway",
                    code="502"
                )
            ).model_dump()
        )
    except RuntimeError as e:
        logger.error(f"Gemini CLI execution error: {e}")
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message=str(e),
                    type="bad_gateway",
                    code="502"
                )
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Error processing chat completion request: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message="Internal server error",
                    type="internal_error",
                    code="500"
                )
            ).model_dump()
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
