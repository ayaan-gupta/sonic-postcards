"""Place names and weather: the offline defaults, and the online providers against recorded answers."""

from __future__ import annotations

import json

import httpx

from app.geo.grid import snap
from app.geo.places import NominatimPlaceNamer, OfflinePlaceNamer, coordinate_label
from app.geo.weather import NoWeather, OpenMeteoWeather, condition_from_wmo
from tests.conftest import FIXTURES


def test_offline_namer_prefers_the_city_people_would_say(namer: OfflinePlaceNamer) -> None:
    assert len(namer) > 30_000
    cases = {(35.6762, 139.7503): "Tokyo", (48.8566, 2.3522): "Paris", (40.7128, -74.006): "New York City", (-33.8568, 151.2153): "Sydney", (64.1466, -21.9426): "Reykjavik"}
    for (lat, lon), expected in cases.items():
        place = namer.name(snap(lat, lon))
        assert place.name == expected and place.source == "geonames" and place.country_name
    # Far from any town the name says so, and in the open ocean it is the coordinates.
    assert namer.name(snap(66.6, 26.9)).name.startswith("Near ")
    ocean = namer.name(snap(-40.0, -120.0))
    assert ocean.source == "coordinates" and ocean.name == coordinate_label(snap(-40.0, -120.0)) == "40.00°S 120.00°W"


def test_nominatim_parses_a_recorded_answer_and_sends_only_the_grid_point(namer: OfflinePlaceNamer) -> None:
    recorded = json.loads((FIXTURES / "nominatim_kyoto.json").read_text())
    seen: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json=recorded)

    online = NominatimPlaceNamer(namer, url="https://nominatim.example/reverse", user_agent="test", client=httpx.Client(transport=httpx.MockTransport(handler)))
    place = online.name(snap(35.011635, 135.768029))
    assert (place.name, place.country_code, place.country_name, place.source) == ("Kyoto", "JP", "Japan", "nominatim")
    assert seen[0].params["lat"] == "35.010" and seen[0].params["lon"] == "135.770"


def test_nominatim_falls_back_to_the_offline_table_when_it_fails(namer: OfflinePlaceNamer) -> None:
    for response in (httpx.Response(503), httpx.Response(200, json={"error": "Unable to geocode"}), httpx.Response(200, text="not json")):
        online = NominatimPlaceNamer(namer, url="https://nominatim.example/reverse", user_agent="test", client=httpx.Client(transport=httpx.MockTransport(lambda _, r=response: r)))
        assert online.name(snap(35.0116, 135.7681)).source == "geonames"


def test_open_meteo_parses_a_recorded_answer_and_fails_quietly() -> None:
    recorded = json.loads((FIXTURES / "open_meteo_kyoto.json").read_text())
    weather = OpenMeteoWeather(url="https://meteo.example/forecast", user_agent="test", client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=recorded))))
    observed = weather.current(snap(35.0116, 135.7681))
    assert observed is not None and observed.condition == "clear" and observed.temperature_c == 15.9 and observed.source == "open-meteo"
    down = OpenMeteoWeather(url="https://meteo.example/forecast", user_agent="test", client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))))
    assert down.current(snap(35.0, 135.0)) is None
    assert NoWeather().current(snap(35.0, 135.0)) is None
    assert [condition_from_wmo(code) for code in (0, 3, 45, 53, 63, 75, 95, 999)] == ["clear", "cloudy", "fog", "drizzle", "rain", "snow", "storm", "cloudy"]
