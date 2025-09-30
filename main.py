from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configuration.config import Config
from src.api.router import router, setup_config_store

# Force import of strategies to register them
import src.strategies  # pylint: disable=unused-import

app = FastAPI(title="SEAD Entity Reconciliation Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(router)


@app.on_event("startup")
async def startup():
    try:

        await setup_config_store()

        # configure_logging(cfg.get("logging") or {})

        # dsn: str = create_db_uri(**cfg.get("options:database"))
        # app.state.conn = await psycopg.AsyncConnection.connect(dsn)
        # app.state.config = cfg

        # cfg.add({"runtime:connection": app.state.conn})
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    try:
        if hasattr(app.state, "conn") and app.state.conn:
            await app.state.conn.close()
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error closing database connection: {e}")
