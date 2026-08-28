"""
Mandate Gateway — Application Runtime Entrypoint
Section S00.4 — Application Runtime Foundation
"""

from apps.api.app import create_app

# Default application instance for ASGI servers
app = create_app()

if __name__ == "__main__":
    print(
        f"Mandate Gateway Runtime Initialized ({app.settings.app_name} - {app.settings.app_env.value})"
    )
