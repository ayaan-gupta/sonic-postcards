"""Everything the HTTP layer can ask for, with the dependencies injected.

The pipeline for a new postcard runs top to bottom in `create`: quota,
decode and level, tag, reject speech, snap the location, name the place,
paint, store, insert.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from psycopg.types.json import Jsonb

from app.audio.clip import ClipError, prepare_clip
from app.audio.motifs import MOTIF_BY_SLUG, Tag, pick_motifs
from app.audio.tagger import AudioTagger, Label, Tagging
from app.config import Settings
from app.db import Connection, Database, as_array
from app.errors import AdminDisabled, ApiError, BadClip, NotFound, RateLimited, SpeechRejected, Unauthorized
from app.geo.grid import GridPoint, snap
from app.geo.places import Place, PlaceNamer
from app.geo.weather import WeatherSource
from app.models import (
    LabelOut,
    PlaceOut,
    PostcardOut,
    QuotaOut,
    ReportedPostcard,
    ReportOut,
    TagOut,
    cell_of,
)
from app.postcard.brief import PostcardBrief, TimeOfDay, time_of_day
from app.postcard.provider import ImageProvider
from app.postcard.render import render_postcard
from app.storage import BlobStore

_ID_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
_DEVICE_ID = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_WINDOW = timedelta(hours=24)

COLUMNS = (
    "id, created_at, lat_md, lon_md, place_name, country_code, country_name, local_date, local_hour, "
    "time_of_day, labels, motifs, speech_prob, weather, clip_key, image_key, image_provider, prompt, seeded, hidden"
)


def new_id() -> str:
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(10))


def local_clock(now: datetime, point: GridPoint, tz_offset_min: int | None) -> tuple[date, int]:
    """Local date and hour. Uses the browser's UTC offset when given, else solar time from longitude."""
    if tz_offset_min is None or not -720 <= tz_offset_min <= 840:
        tz_offset_min = round(point.lon / 15.0 * 60.0)
    local = now.astimezone(UTC) + timedelta(minutes=tz_offset_min)
    return local.date(), local.hour


@dataclass(frozen=True)
class NewPostcard:
    """A fully analysed postcard, ready to be painted and stored."""

    point: GridPoint
    source: Literal["gps", "manual", "seed"]
    place: Place
    local_date: date
    local_hour: int
    tagging: Tagging
    tags: list[Tag]
    weather: dict[str, object] | None
    device_hash: str
    clip_key: str
    seeded: bool = False
    created_at: datetime | None = None
    postcard_id: str | None = None


class PostcardService:
    def __init__(
        self,
        *,
        settings: Settings,
        db: Database,
        store: BlobStore,
        tagger: AudioTagger,
        namer: PlaceNamer,
        weather: WeatherSource,
        provider: ImageProvider,
    ) -> None:
        self.settings = settings
        self.db = db
        self.store = store
        self.tagger = tagger
        self.namer = namer
        self.weather = weather
        self.provider = provider
        self._render_locks = [threading.Lock() for _ in range(16)]

    # -- identity and quota ------------------------------------------------------

    def device_hash(self, device_id: str | None) -> str:
        if not device_id or not _DEVICE_ID.match(device_id):
            raise ApiError("A device id is required to post or report.", header="X-Device-Id")
        digest = hashlib.sha256(f"{self.settings.device_salt}:{device_id}".encode()).hexdigest()
        return digest[:40]

    def _usage(self, conn: Connection, device_hash: str, now: datetime) -> tuple[int, datetime | None]:
        row = conn.execute(
            "SELECT count(*) AS used, min(created_at) AS oldest FROM upload_events "
            "WHERE device_hash = %s AND created_at > %s",
            (device_hash, now - _WINDOW),
        ).fetchone()
        assert row is not None
        oldest: datetime | None = row["oldest"]
        return int(row["used"]), (oldest + _WINDOW if oldest else None)

    def quota(self, device_id: str | None, now: datetime | None = None) -> QuotaOut:
        device = self.device_hash(device_id)
        limit = self.settings.daily_postcard_limit
        with self.db.connection() as conn:
            used, resets_at = self._usage(conn, device, now or datetime.now(UTC))
        return QuotaOut(limit=limit, used=used, remaining=max(0, limit - used), resets_at=resets_at if used >= limit else None)

    # -- creating ----------------------------------------------------------------

    def analyse(self, audio: bytes) -> tuple[bytes, Tagging]:
        """Pipeline steps 1 to 4. Returns the stored MP3 and what the tagger heard."""
        try:
            clip = prepare_clip(audio, clip_seconds=self.settings.clip_seconds, min_seconds=self.settings.min_clip_seconds)
        except ClipError as exc:
            raise BadClip(exc.code, exc.message) from exc
        tagging = self.tagger.tag(clip.analysis)
        if tagging.speech_probability > self.settings.speech_threshold:
            raise SpeechRejected(tagging.speech_probability, self.settings.speech_threshold)
        return clip.playback_mp3, tagging

    def create(
        self,
        *,
        audio: bytes,
        lat: float,
        lon: float,
        source: Literal["gps", "manual"],
        device_id: str | None,
        tz_offset_min: int | None = None,
        now: datetime | None = None,
    ) -> PostcardOut:
        now = now or datetime.now(UTC)
        device = self.device_hash(device_id)
        limit = self.settings.daily_postcard_limit
        with self.db.connection() as conn:
            used, resets_at = self._usage(conn, device, now)
        if used >= limit:
            raise RateLimited(limit, resets_at)

        try:
            point = snap(lat, lon)  # the raw coordinate is not used again after this line
        except ValueError as exc:
            raise ApiError(str(exc)) from exc
        mp3, tagging = self.analyse(audio)

        postcard_id = new_id()
        clip_key = f"clips/{postcard_id}.mp3"
        local_date, local_hour = local_clock(now, point, tz_offset_min)
        observed = self.weather.current(point)
        record = NewPostcard(
            point=point,
            source=source,
            place=self.namer.name(point),
            local_date=local_date,
            local_hour=local_hour,
            tagging=tagging,
            tags=pick_motifs(tagging.labels),
            weather=observed.as_json() if observed else None,
            device_hash=device,
            clip_key=clip_key,
            created_at=now,
            postcard_id=postcard_id,
        )
        self.store.put(clip_key, mp3, "audio/mpeg")
        try:
            return self.insert(record, render=True, enforce_limit=True)
        except BaseException:
            self.store.delete(clip_key)
            raise

    def brief_for(self, row: dict[str, Any]) -> PostcardBrief:
        weather = row["weather"] or {}
        tod: TimeOfDay = row["time_of_day"]
        return PostcardBrief(
            postcard_id=row["id"],
            motifs=list(row["motifs"]),
            labels=[item["name"] for item in row["labels"]],
            time_of_day=tod,
            place_name=row["place_name"],
            country_name=row["country_name"],
            local_date=row["local_date"],
            weather=weather.get("condition") if isinstance(weather, dict) else None,
        )

    def insert(self, record: NewPostcard, *, render: bool, enforce_limit: bool = False) -> PostcardOut:
        """Paint (optionally), store the images and write the row."""
        postcard_id = record.postcard_id or new_id()
        created_at = record.created_at or datetime.now(UTC)
        row: dict[str, Any] = {
            "id": postcard_id,
            "created_at": created_at,
            "lat_md": record.point.lat_md,
            "lon_md": record.point.lon_md,
            "location_source": record.source,
            "place_name": record.place.name,
            "country_code": record.place.country_code,
            "country_name": record.place.country_name,
            "local_date": record.local_date,
            "local_hour": record.local_hour,
            "time_of_day": time_of_day(record.local_hour),
            "labels": [{"name": label.name, "score": label.score} for label in record.tagging.labels],
            "motifs": [tag.slug for tag in record.tags],
            "speech_prob": record.tagging.speech_probability,
            "embedding": record.tagging.embedding,
            "weather": record.weather,
            "clip_key": record.clip_key,
            "image_key": None,
            "image_provider": self.provider.name,
            "prompt": "",
            "device_hash": record.device_hash,
            "seeded": record.seeded,
            "hidden": False,
        }
        brief = self.brief_for(row)
        row["prompt"] = brief.prompt()
        written: list[str] = []
        if render:
            rendered = render_postcard(brief, self.provider, self.settings.assets_dir)
            row["image_key"] = f"postcards/{postcard_id}.png"
            row["image_provider"] = rendered.provider
            self.store.put(row["image_key"], rendered.png, "image/png")
            self.store.put(f"postcards/{postcard_id}.webp", rendered.thumb_webp, "image/webp")
            written = [row["image_key"], f"postcards/{postcard_id}.webp"]
        try:
            with self.db.connection() as conn:
                if enforce_limit:
                    # Two uploads from one device must not both pass the check above.
                    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (record.device_hash,))
                    used, resets_at = self._usage(conn, record.device_hash, created_at)
                    if used >= self.settings.daily_postcard_limit:
                        raise RateLimited(self.settings.daily_postcard_limit, resets_at)
                    conn.execute(
                        "INSERT INTO upload_events (device_hash, created_at) VALUES (%s, %s)",
                        (record.device_hash, created_at),
                    )
                insert_row(conn, row)
        except BaseException:
            for key in written:
                self.store.delete(key)
            raise
        return self.to_out(row)

    # -- reading -----------------------------------------------------------------

    def to_out(self, row: dict[str, Any], *, distance_m: float | None = None, similarity: float | None = None) -> PostcardOut:
        point = GridPoint(lat_md=row["lat_md"], lon_md=row["lon_md"])
        base = f"/api/postcards/{row['id']}"
        tags = [
            TagOut(slug=slug, name=MOTIF_BY_SLUG[slug].name, score=_motif_score(slug, row["labels"]))
            for slug in row["motifs"]
            if slug in MOTIF_BY_SLUG
        ]
        return PostcardOut(
            id=row["id"],
            created_at=row["created_at"],
            lat=point.lat,
            lon=point.lon,
            cell=cell_of(point),
            place_name=row["place_name"],
            country_code=row["country_code"],
            country_name=row["country_name"],
            local_date=row["local_date"],
            local_hour=row["local_hour"],
            time_of_day=row["time_of_day"],
            tags=tags,
            labels=[LabelOut(name=item["name"], score=item["score"]) for item in row["labels"][:8]],
            speech_probability=round(float(row["speech_prob"]), 4),
            weather=row["weather"],
            audio_url=f"{base}/audio",
            image_url=f"{base}/image",
            thumb_url=f"{base}/image?size=thumb",
            image_provider=row["image_provider"],
            prompt=row["prompt"],
            seeded=row["seeded"],
            distance_m=round(distance_m, 1) if distance_m is not None else None,
            similarity=round(similarity, 4) if similarity is not None else None,
        )

    def _row(self, conn: Connection, postcard_id: str, *, include_hidden: bool = False) -> dict[str, Any]:
        row = conn.execute(f"SELECT {COLUMNS} FROM postcards WHERE id = %s", (postcard_id,)).fetchone()  # noqa: S608
        if row is None or (row["hidden"] and not include_hidden):
            raise NotFound("That postcard does not exist, or it was taken down.")
        return row

    def get(self, postcard_id: str) -> PostcardOut:
        with self.db.connection() as conn:
            return self.to_out(self._row(conn, postcard_id))

    def recent(self, limit: int = 24) -> list[PostcardOut]:
        with self.db.connection() as conn:
            rows = conn.execute(
                f"SELECT {COLUMNS} FROM postcards WHERE NOT hidden ORDER BY created_at DESC LIMIT %s",  # noqa: S608
                (limit,),
            ).fetchall()
        return [self.to_out(row) for row in rows]

    def pins(self, west: float, south: float, east: float, north: float, zoom: float) -> str:
        """GeoJSON for the map, built by Postgres and passed through as text.

        Up to `max_pins` postcards come back one feature each and the browser
        clusters them. Beyond that the database groups them on a grid sized
        to the zoom level, so the payload stays bounded however many exist.
        """
        south, north = max(-90.0, min(south, north)), min(90.0, max(south, north))
        if east - west >= 360.0:
            west, east = -180.0, 180.0
        else:
            west = (west + 180.0) % 360.0 - 180.0
            east = (east + 180.0) % 360.0 - 180.0
        if west <= east:
            where = "geom && ST_MakeEnvelope(%(w)s, %(s)s, %(e)s, %(n)s, 4326)"
        else:  # the box crosses the antimeridian
            where = (
                "(geom && ST_MakeEnvelope(%(w)s, %(s)s, 180, %(n)s, 4326)"
                " OR geom && ST_MakeEnvelope(-180, %(s)s, %(e)s, %(n)s, 4326))"
            )
        params = {"w": west, "s": south, "e": east, "n": north, "max": self.settings.max_pins}
        with self.db.connection() as conn:
            total_row = conn.execute(f"SELECT count(*) AS n FROM postcards WHERE NOT hidden AND {where}", params).fetchone()  # noqa: S608
            assert total_row is not None
            total = int(total_row["n"])
            if total <= self.settings.max_pins:
                query = f"""
                    SELECT json_build_object(
                      'type', 'FeatureCollection', 'mode', 'pins', 'total', %(total)s::int,
                      'features', coalesce(json_agg(json_build_object(
                        'type', 'Feature',
                        'geometry', json_build_object('type', 'Point', 'coordinates',
                          json_build_array((lon_md / 1000.0)::float8, (lat_md / 1000.0)::float8)),
                        'properties', json_build_object('id', id, 'motif', motifs[1], 'count', 1)
                      )), '[]'::json)
                    )::text AS geojson
                    FROM postcards WHERE NOT hidden AND {where}
                """  # noqa: S608
            else:
                params["cell"] = 360.0 / (2.0 ** max(0.0, min(zoom, 22.0))) / 6.0
                query = f"""
                    WITH cells AS (
                      SELECT count(*) AS n, avg(lon_md) / 1000.0 AS lon, avg(lat_md) / 1000.0 AS lat,
                             mode() WITHIN GROUP (ORDER BY motifs[1]) AS motif, min(id) AS any_id
                      FROM postcards WHERE NOT hidden AND {where}
                      GROUP BY ST_SnapToGrid(geom, %(cell)s)
                    )
                    SELECT json_build_object(
                      'type', 'FeatureCollection', 'mode', 'cells', 'total', %(total)s::int,
                      'features', coalesce(json_agg(json_build_object(
                        'type', 'Feature',
                        'geometry', json_build_object('type', 'Point', 'coordinates',
                          json_build_array(round(lon::numeric, 4)::float8, round(lat::numeric, 4)::float8)),
                        'properties', json_build_object('id', CASE WHEN n = 1 THEN any_id END, 'motif', motif, 'count', n)
                      )), '[]'::json)
                    )::text AS geojson
                    FROM cells
                """  # noqa: S608
            params["total"] = total
            row = conn.execute(query, params).fetchone()
        assert row is not None
        geojson: str = row["geojson"]
        return geojson

    def nearby(self, lat: float, lon: float, radius_km: float, *, limit: int = 30, sort: Literal["recent", "nearest"] = "recent") -> list[PostcardOut]:
        point = self._snap(lat, lon)  # queries are snapped too, so logs never hold an exact position
        order = "created_at DESC" if sort == "recent" else "distance_m, created_at DESC"
        with self.db.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {COLUMNS}, ST_Distance(geom::geography, origin.g) AS distance_m
                FROM postcards, (SELECT ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography AS g) AS origin
                WHERE NOT hidden AND ST_DWithin(geom::geography, origin.g, %(radius)s)
                ORDER BY {order} LIMIT %(limit)s
                """,  # noqa: S608
                {"lon": point.lon, "lat": point.lat, "radius": radius_km * 1000.0, "limit": limit},
            ).fetchall()
        return [self.to_out(row, distance_m=float(row["distance_m"])) for row in rows]

    def similar(self, postcard_id: str, *, limit: int = 5, near: tuple[float, float] | None = None, radius_km: float = 50.0) -> list[PostcardOut]:
        """Nearest clips by cosine distance, optionally only those within a radius of `near`."""
        with self.db.connection() as conn:
            source = conn.execute("SELECT embedding FROM postcards WHERE id = %s AND NOT hidden", (postcard_id,)).fetchone()
            if source is None:
                raise NotFound("That postcard does not exist, or it was taken down.")
            params: dict[str, Any] = {"q": source["embedding"], "id": postcard_id, "limit": limit}
            geo = ""
            if near is not None:
                point = self._snap(*near)
                geo = "AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, %(radius)s)"
                params.update(lon=point.lon, lat=point.lat, radius=radius_km * 1000.0)
            # Keep walking the HNSW graph until enough rows survive the filters.
            conn.execute("SET LOCAL hnsw.iterative_scan = strict_order")
            conn.execute("SET LOCAL hnsw.ef_search = 100")
            rows = conn.execute(
                f"""
                SELECT {COLUMNS}, 1 - (embedding <=> %(q)s) AS similarity
                FROM postcards
                WHERE id <> %(id)s AND NOT hidden {geo}
                ORDER BY embedding <=> %(q)s LIMIT %(limit)s
                """,  # noqa: S608
                params,
            ).fetchall()
        return [self.to_out(row, similarity=float(row["similarity"])) for row in rows]

    def place(self, lat: float, lon: float) -> PlaceOut:
        point = self._snap(lat, lon)
        place = self.namer.name(point)
        return PlaceOut(lat=point.lat, lon=point.lon, cell=cell_of(point), place_name=place.name, country_name=place.country_name)

    @staticmethod
    def _snap(lat: float, lon: float) -> GridPoint:
        try:
            return snap(lat, lon)
        except ValueError as exc:
            raise ApiError(str(exc)) from exc

    # -- files -------------------------------------------------------------------

    def audio(self, postcard_id: str) -> tuple[bytes | None, str | None]:
        """The clip's bytes, or a URL to redirect to when the store is public."""
        with self.db.connection() as conn:
            row = self._row(conn, postcard_id)
        url = self.store.public_url(row["clip_key"])
        if url:
            return None, url
        return self.store.get(row["clip_key"]), None

    def image(self, postcard_id: str, size: Literal["full", "thumb"] = "full") -> tuple[bytes | None, str | None, str]:
        """The postcard image: bytes or a redirect URL, plus its content type.

        Seeded pins are not painted until someone looks at them. The first
        request paints and stores the image; a lock keeps two simultaneous
        first requests from doing the work twice.
        """
        with self.db.connection() as conn:
            row = self._row(conn, postcard_id)
        if row["image_key"] is None:
            lock = self._render_locks[hash(postcard_id) % len(self._render_locks)]
            with lock:
                with self.db.connection() as conn:
                    row = self._row(conn, postcard_id)
                if row["image_key"] is None:
                    rendered = render_postcard(self.brief_for(row), self.provider, self.settings.assets_dir)
                    key = f"postcards/{postcard_id}.png"
                    self.store.put(key, rendered.png, "image/png")
                    self.store.put(f"postcards/{postcard_id}.webp", rendered.thumb_webp, "image/webp")
                    with self.db.connection() as conn:
                        conn.execute(
                            "UPDATE postcards SET image_key = %s, image_provider = %s WHERE id = %s",
                            (key, rendered.provider, postcard_id),
                        )
                    row["image_key"] = key
        key = row["image_key"] if size == "full" else f"postcards/{postcard_id}.webp"
        content_type = "image/png" if size == "full" else "image/webp"
        url = self.store.public_url(key)
        if url:
            return None, url, content_type
        return self.store.get(key), None, content_type

    # -- moderation --------------------------------------------------------------

    def report(self, postcard_id: str, device_id: str | None, reason: str) -> ReportOut:
        device = self.device_hash(device_id)
        with self.db.connection() as conn:
            self._row(conn, postcard_id, include_hidden=True)
            conn.execute(
                "INSERT INTO reports (postcard_id, device_hash, reason) VALUES (%s, %s, %s) "
                "ON CONFLICT ON CONSTRAINT one_report_per_device DO NOTHING",
                (postcard_id, device, reason),
            )
            row = conn.execute(
                "UPDATE postcards SET hidden = hidden OR "
                "(SELECT count(*) FROM reports WHERE postcard_id = %(id)s) >= %(threshold)s "
                "WHERE id = %(id)s RETURNING hidden",
                {"id": postcard_id, "threshold": self.settings.report_hide_threshold},
            ).fetchone()
        assert row is not None
        return ReportOut(reported=True, hidden=bool(row["hidden"]))

    def check_admin(self, authorization: str | None) -> None:
        expected = self.settings.admin_token
        if not expected:
            raise AdminDisabled("Set ADMIN_TOKEN to enable the moderation endpoints.")
        given = authorization.removeprefix("Bearer ").strip() if authorization else ""
        if not hmac.compare_digest(given.encode(), expected.encode()):
            raise Unauthorized("A valid admin token is required.")

    def reported(self) -> list[ReportedPostcard]:
        with self.db.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT {", ".join("p." + column.strip() for column in COLUMNS.split(","))},
                       count(r.id) AS report_count, array_agg(DISTINCT r.reason) AS reasons
                FROM postcards p JOIN reports r ON r.postcard_id = p.id
                GROUP BY p.id ORDER BY count(r.id) DESC, max(r.created_at) DESC LIMIT 200
                """  # noqa: S608
            ).fetchall()
        return [
            ReportedPostcard(postcard=self.to_out(row), reports=int(row["report_count"]), reasons=list(row["reasons"]), hidden=bool(row["hidden"]))
            for row in rows
        ]

    def restore(self, postcard_id: str) -> None:
        with self.db.connection() as conn:
            self._row(conn, postcard_id, include_hidden=True)
            conn.execute("DELETE FROM reports WHERE postcard_id = %s", (postcard_id,))
            conn.execute("UPDATE postcards SET hidden = false WHERE id = %s", (postcard_id,))

    def delete(self, postcard_id: str) -> None:
        """Remove the row and its files. A clip shared by seeded pins stays until the last one goes."""
        with self.db.connection() as conn:
            row = self._row(conn, postcard_id, include_hidden=True)
            conn.execute("DELETE FROM postcards WHERE id = %s", (postcard_id,))
            shared = conn.execute("SELECT 1 FROM postcards WHERE clip_key = %s LIMIT 1", (row["clip_key"],)).fetchone()
        if shared is None:
            self.store.delete(row["clip_key"])
        if row["image_key"]:
            self.store.delete(row["image_key"])
            self.store.delete(f"postcards/{postcard_id}.webp")

    def count(self) -> int:
        with self.db.connection() as conn:
            row = conn.execute("SELECT count(*) AS n FROM postcards").fetchone()
        assert row is not None
        return int(row["n"])


def _motif_score(slug: str, labels: list[dict[str, Any]]) -> float:
    motif = MOTIF_BY_SLUG[slug]
    scores = [float(item["score"]) for item in labels if item["name"] in motif.classes]
    return round(max(scores), 4) if scores else 0.0


def insert_row(conn: Connection, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO postcards (
          id, created_at, lat_md, lon_md, location_source, place_name, country_code, country_name,
          local_date, local_hour, time_of_day, labels, motifs, speech_prob, embedding, weather,
          clip_key, image_key, image_provider, prompt, device_hash, seeded, hidden
        ) VALUES (
          %(id)s, %(created_at)s, %(lat_md)s, %(lon_md)s, %(location_source)s, %(place_name)s, %(country_code)s,
          %(country_name)s, %(local_date)s, %(local_hour)s, %(time_of_day)s, %(labels)s, %(motifs)s, %(speech_prob)s,
          %(embedding)s, %(weather)s, %(clip_key)s, %(image_key)s, %(image_provider)s, %(prompt)s, %(device_hash)s,
          %(seeded)s, %(hidden)s
        )
        """,
        {
            **row,
            "labels": Jsonb(row["labels"]),
            "weather": Jsonb(row["weather"]) if row["weather"] is not None else None,
            "embedding": as_array(row["embedding"]),
        },
    )


def labels_from(items: list[dict[str, Any]]) -> list[Label]:
    return [Label(name=item["name"], score=float(item["score"])) for item in items]
