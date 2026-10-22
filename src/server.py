"""The whole app on one port: the API under /api and the built web app (web/dist) everywhere
else. Run it with `uv run src/server.py`; the Dockerfile does the same."""
import argparse
import os

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

import api

DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")


class WebApp(StaticFiles):
    """web/dist, answering index.html for a path that isn't a file there, so a reload of
    /app/speak reaches React Router instead of a 404."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


def make_app(dist=DIST):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)  # the API's own are at /api/docs
    app.mount("/api", api.app)  # first, so an unknown /api path is the API's JSON 404, not the web app

    @app.get("/health")
    def health():
        return api.health()

    if os.path.isdir(dist):
        app.mount("/", WebApp(directory=dist, html=True))
    return app


app = make_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    if not os.path.isdir(DIST):
        print(f"no {DIST}: serving the API only (build the web app with `npm run build` in web/)")
    # Behind a proxy (TRUST_PROXY on) uvicorn takes the client and https from its X-Forwarded-*
    # headers; otherwise it ignores them, so nobody can fake them on a direct connection.
    trust = api.trust_proxy()
    uvicorn.run(app, host=args.host, port=args.port, proxy_headers=trust, forwarded_allow_ips="*" if trust else None)
