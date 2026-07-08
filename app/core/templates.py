from __future__ import annotations

from fastapi.templating import Jinja2Templates

# Single shared Jinja2Templates instance for the server-rendered UI.
#
# Defined in its own module (rather than directly inline in app/main.py) so
# that app/api/ui.py can import it without creating a circular import with
# app/main.py, which itself imports and mounts the UI router. app/main.py
# re-imports this instance so it stays the one canonical place it's wired up.
templates = Jinja2Templates(directory="app/templates")