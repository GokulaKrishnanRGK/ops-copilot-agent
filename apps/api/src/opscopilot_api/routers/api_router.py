from fastapi import APIRouter

from .messages_router import router as messages_router
from .runs_router import router as runs_router
from .sessions_router import router as sessions_router
from .tool_calls_router import router as tool_calls_router

router = APIRouter()
router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
router.include_router(messages_router, prefix="/messages", tags=["messages"])
router.include_router(runs_router, prefix="/runs", tags=["runs"])
router.include_router(tool_calls_router, prefix="/tool-calls", tags=["tool-calls"])
