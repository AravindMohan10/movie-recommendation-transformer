from fastapi import APIRouter, Depends, HTTPException
from ..auth import get_current_user
from ..models import User
from ..model_service import get_model_service
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/model-status")
async def get_model_status(current_user: User = Depends(get_current_user)):
    """Debug endpoint to check model service status"""
    try:
        model_service = get_model_service()
        
        status = {
            "model_loaded": model_service.engine is not None,
            "movie_data_count": len(model_service.movie_data),
            "device": str(model_service.device),
            "use_redis": model_service.use_redis,
            "has_redis": model_service.redis_client is not None,
        }
        
        # Try to get a test recommendation
        try:
            test_rec = model_service.get_recommendations(current_user.user_id, 1, 0)
            status["test_recommendation"] = {
                "success": True,
                "count": len(test_rec) if test_rec else 0
            }
        except Exception as rec_error:
            status["test_recommendation"] = {
                "success": False,
                "error": str(rec_error),
                "traceback": traceback.format_exc()
            }
        
        return status
    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/rag-status")
async def get_rag_status(current_user: User = Depends(get_current_user)):
    """RAG + Chroma status (required for CF+RAG recommendations)."""
    try:
        from ..rag_service import get_rag_service

        rag = get_rag_service()
        ok = rag._ensure_index()
        count = rag._collection.count() if (rag._collection is not None) else 0
        chroma_path = str(getattr(rag, "_chroma_path", ""))
        return {
            "available": ok,
            "index_count": count,
            "chroma_path": chroma_path,
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

