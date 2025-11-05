# PUBLIC_INTERFACE
def run():
    """Entrypoint to run the FastAPI app with uvicorn, honoring configured HOST/PORT."""
    import uvicorn
    from src.api.main import create_app
    from src.api.config import get_settings

    settings = get_settings()
    host, port = settings.get_uvicorn_config()
    uvicorn.run(create_app(), host=host, port=port, reload=False)

if __name__ == "__main__":
    run()
