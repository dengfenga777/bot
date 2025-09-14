How to integrate another project

1) Create a subpackage under this folder, e.g. `myproj/`.

2) Expose Telegram handlers
   - File: `myproj/handlers.py`
   - Define variables ending with `_handler`, e.g.:
     ```python
     from telegram.ext import CommandHandler
     async def hello(update, context):
         await update.effective_chat.send_message("hello")
     hello_handler = CommandHandler("hello", hello)
     ```

3) Expose FastAPI routers
   - File: `myproj/router.py`
   - Define variable `router` of type `fastapi.APIRouter`
     ```python
     from fastapi import APIRouter
     router = APIRouter(prefix="/api/myproj", tags=["myproj"])
     @router.get("/ping")
     def ping():
         return {"ok": True}
     ```

4) Configuration
   - Add any new config keys into `src/app/config.py` and map them from `.env`.

5) Dependencies
   - Add Python deps into `requirements.txt` (or `pyproject.toml`).
   - If there is a frontend, merge routes/components into `webapp-frontend` as needed.

On start, the app auto-loads any `handlers.py` and `router.py` from every subpackage here.

