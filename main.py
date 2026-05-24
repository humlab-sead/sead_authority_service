from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Force import of strategies to register them
from src.api.identity_router import identity_router
from src.api.router import router
from src.configuration import ConfigProvider, get_config_provider, setup_config_store, shutdown_connection_pool

app = FastAPI(title="SEAD Entity Reconciliation Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(router)
app.include_router(identity_router)


@app.on_event("startup")
async def startup():
    try:
        logger.info("Starting up application...")
        await setup_config_store()

        # Verify configuration is working
        provider: ConfigProvider = get_config_provider()
        if not provider.is_configured():
            raise RuntimeError("Configuration setup failed")

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    try:
        if get_config_provider().is_configured():

            await shutdown_connection_pool()
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error closing database connection pool: {e}")
