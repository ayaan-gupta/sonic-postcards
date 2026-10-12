"""The FastAPI application. `create_app` wires real dependencies; tests can swap any of them."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Form, Header, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.audio.tagger import AudioTagger, YamnetTagger
from app.config import Settings, get_settings
from app.db import Database, migrate
from app.errors import ApiError, RateLimited, TooLarge
from app.geo.places import NominatimPlaceNamer, OfflinePlaceNamer, PlaceNamer
from app.geo.weather import NoWeather, OpenMeteoWeather, WeatherSource
from app.models import ErrorOut, PlaceOut, PostcardList, PostcardOut, QuotaOut, ReportedPostcard, ReportIn, ReportOut
from app.postcard.provider import ImageProvider, make_provider
from app.service import PostcardService
from app.storage import BlobStore, LocalDirStore, S3Store

log = logging.getLogger("sonic")
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")
_IMMUTABLE = "public, max-age=31536000, immutable"


def make_store(settings: Settings) -> BlobStore:
    if settings.storage_backend == "s3":
        return S3Store(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            public_base_url=settings.s3_public_base_url,
        )
    return LocalDirStore(settings.storage_dir)


def make_namer(settings: Settings) -> PlaceNamer:
    offline = OfflinePlaceNamer()
    if settings.geocoder == "nominatim":
        return NominatimPlaceNamer(offline, url=settings.nominatim_url, user_agent=settings.http_user_agent, timeout=settings.http_timeout_seconds)
    return offline


def make_weather(settings: Settings) -> WeatherSource:
    if settings.weather == "open-meteo":
        return OpenMeteoWeather(url=settings.open_meteo_url, user_agent=settings.http_user_agent, timeout=settings.http_timeout_seconds)
    return NoWeather()


def build_service(
    settings: Settings,
    *,
    db: Database,
    store: BlobStore | None = None,
    tagger: AudioTagger | None = None,
    namer: PlaceNamer | None = None,
    weather: WeatherSource | None = None,
    provider: ImageProvider | None = None,
) -> PostcardService:
    return PostcardService(
        settings=settings,
        db=db,
        store=store or make_store(settings),
        tagger=tagger or YamnetTagger(),
        namer=namer or make_namer(settings),
        weather=weather or make_weather(settings),
        provider=provider or make_provider(settings),
    )


def ranged(data: bytes, content_type: str, range_header: str | None, *, cache: str = _IMMUTABLE) -> Response:
    """Serve bytes with single-range support. Safari will not play audio without it."""
    headers = {"Accept-Ranges": "bytes", "Cache-Control": cache}
    match = _RANGE.match(range_header.strip()) if range_header else None
    if match and (match.group(1) or match.group(2)):
        size = len(data)
        if match.group(1):
            start = int(match.group(1))
            end = min(int(match.group(2)), size - 1) if match.group(2) else size - 1
        else:
            start = max(0, size - int(match.group(2)))
            end = size - 1
        if start >= size or start > end:
            return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"})
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        return Response(content=data[start : end + 1], status_code=206, media_type=content_type, headers=headers)
    return Response(content=data, media_type=content_type, headers=headers)


def create_app(settings: Settings | None = None, *, service: PostcardService | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned: Database | None = None
        if service is not None:
            app.state.service = service
        else:
            applied = migrate(settings.database_url)
            if applied:
                log.info("applied migrations: %s", ", ".join(applied))
            owned = Database(settings.database_url)
            owned.open()
            app.state.service = build_service(settings, db=owned)
            if settings.seed_on_start and app.state.service.count() == 0:
                from app.seed import seed_demo

                seeded = seed_demo(app.state.service)
                log.info("seeded %d demo postcards", seeded)
        try:
            yield
        finally:
            if owned is not None:
                owned.close()

    app = FastAPI(title="Sonic Postcards", version="0.1.0", lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    def svc(request: Request) -> PostcardService:
        result: PostcardService = request.app.state.service
        return result

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        headers: dict[str, str] = {}
        if isinstance(exc, RateLimited) and exc.resets_at is not None:
            headers["Retry-After"] = exc.resets_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
        body = {"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}}
        return JSONResponse(status_code=exc.status, content=body, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [".".join(str(part) for part in error["loc"][1:]) or str(error["loc"][0]) for error in exc.errors()]
        message = "Some of what was sent is missing or out of range: " + ", ".join(sorted(set(fields))) + "."
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_request", "message": message, "detail": {"fields": fields}}})

    errors: dict[int | str, dict[str, Any]] = {400: {"model": ErrorOut}, 404: {"model": ErrorOut}}

    @app.get("/api/health")
    def health(request: Request) -> dict[str, object]:
        return {"ok": True, "postcards": svc(request).count(), "image_provider": svc(request).provider.name}

    @app.post("/api/postcards", status_code=201, responses={**errors, 413: {"model": ErrorOut}, 422: {"model": ErrorOut}, 429: {"model": ErrorOut}})
    def create_postcard(
        request: Request,
        audio: Annotated[UploadFile, File(description="The recording, in any container the browser produced")],
        lat: Annotated[float, Form(ge=-90, le=90)],
        lon: Annotated[float, Form(ge=-180, le=180)],
        source: Annotated[Literal["gps", "manual"], Form()] = "manual",
        tz_offset_min: Annotated[int | None, Form()] = None,
        x_device_id: Annotated[str | None, Header()] = None,
    ) -> PostcardOut:
        data = audio.file.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise TooLarge("That recording is too large. Ten seconds is all a postcard needs.")
        return svc(request).create(audio=data, lat=lat, lon=lon, source=source, device_id=x_device_id, tz_offset_min=tz_offset_min)

    @app.get("/api/postcards", response_model=PostcardList)
    def recent_postcards(request: Request, limit: Annotated[int, Query(ge=1, le=60)] = 24) -> PostcardList:
        return PostcardList(items=svc(request).recent(limit))

    @app.get("/api/postcards/{postcard_id}", responses=errors)
    def get_postcard(request: Request, postcard_id: str) -> PostcardOut:
        return svc(request).get(postcard_id)

    @app.get("/api/postcards/{postcard_id}/audio", responses=errors)
    def get_audio(request: Request, postcard_id: str, range_: Annotated[str | None, Header(alias="Range")] = None) -> Response:
        data, url = svc(request).audio(postcard_id)
        if url:
            return RedirectResponse(url, status_code=307)
        assert data is not None
        return ranged(data, "audio/mpeg", range_)

    @app.get("/api/postcards/{postcard_id}/image", responses=errors)
    def get_image(request: Request, postcard_id: str, size: Literal["full", "thumb"] = "full") -> Response:
        data, url, content_type = svc(request).image(postcard_id, size)
        if url:
            return RedirectResponse(url, status_code=307)
        assert data is not None
        return Response(content=data, media_type=content_type, headers={"Cache-Control": _IMMUTABLE})

    @app.get("/api/postcards/{postcard_id}/similar", response_model=PostcardList, responses=errors)
    def similar(
        request: Request,
        postcard_id: str,
        limit: Annotated[int, Query(ge=1, le=20)] = 5,
        lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
        lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
        radius_km: Annotated[float, Query(gt=0, le=20000)] = 50.0,
    ) -> PostcardList:
        near = (lat, lon) if lat is not None and lon is not None else None
        return PostcardList(items=svc(request).similar(postcard_id, limit=limit, near=near, radius_km=radius_km))

    @app.post("/api/postcards/{postcard_id}/report", responses=errors)
    def report(request: Request, postcard_id: str, body: ReportIn, x_device_id: Annotated[str | None, Header()] = None) -> ReportOut:
        return svc(request).report(postcard_id, x_device_id, body.reason)

    @app.get("/api/pins")
    def pins(
        request: Request,
        bbox: Annotated[str, Query(description="west,south,east,north in degrees")] = "-180,-90,180,90",
        zoom: Annotated[float, Query(ge=0, le=24)] = 1.0,
    ) -> Response:
        try:
            west, south, east, north = (float(part) for part in bbox.split(","))
        except ValueError as exc:
            raise ApiError("bbox must be four numbers: west,south,east,north") from exc
        geojson = svc(request).pins(west, south, east, north, zoom)
        return Response(content=geojson, media_type="application/geo+json", headers={"Cache-Control": "no-store"})

    @app.get("/api/nearby", response_model=PostcardList)
    def nearby(
        request: Request,
        lat: Annotated[float, Query(ge=-90, le=90)],
        lon: Annotated[float, Query(ge=-180, le=180)],
        radius_km: Annotated[float, Query(gt=0, le=2000)] = 25.0,
        limit: Annotated[int, Query(ge=1, le=60)] = 30,
        sort: Literal["recent", "nearest"] = "recent",
    ) -> PostcardList:
        return PostcardList(items=svc(request).nearby(lat, lon, radius_km, limit=limit, sort=sort))

    @app.get("/api/place")
    def place(request: Request, lat: Annotated[float, Query(ge=-90, le=90)], lon: Annotated[float, Query(ge=-180, le=180)]) -> PlaceOut:
        return svc(request).place(lat, lon)

    @app.get("/api/quota")
    def quota(request: Request, x_device_id: Annotated[str | None, Header()] = None) -> QuotaOut:
        return svc(request).quota(x_device_id)

    @app.get("/api/admin/reports")
    def admin_reports(request: Request, authorization: Annotated[str | None, Header()] = None) -> list[ReportedPostcard]:
        svc(request).check_admin(authorization)
        return svc(request).reported()

    @app.post("/api/admin/postcards/{postcard_id}/restore", status_code=204)
    def admin_restore(request: Request, postcard_id: str, authorization: Annotated[str | None, Header()] = None) -> Response:
        svc(request).check_admin(authorization)
        svc(request).restore(postcard_id)
        return Response(status_code=204)

    @app.delete("/api/admin/postcards/{postcard_id}", status_code=204)
    def admin_delete(request: Request, postcard_id: str, authorization: Annotated[str | None, Header()] = None) -> Response:
        svc(request).check_admin(authorization)
        svc(request).delete(postcard_id)
        return Response(status_code=204)

    return app


app = create_app()
