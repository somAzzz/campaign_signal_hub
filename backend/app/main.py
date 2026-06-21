from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import campaigns, exports, signals, uploads
from app.core.config import settings
from app.services.persistence import load_snapshot, save_snapshot
from app.services.seed import seed_demo_data


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
    app.include_router(uploads.router, prefix="/api/campaigns", tags=["uploads"])
    app.include_router(signals.router, prefix="/api", tags=["signals"])
    app.include_router(exports.router, prefix="/api/campaigns", tags=["exports"])

    @app.on_event("startup")
    def _seed_demo() -> None:
        if not load_snapshot():
            seed_demo_data()
            save_snapshot()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
