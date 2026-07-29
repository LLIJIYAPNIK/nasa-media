from datetime import date, datetime
from io import BytesIO

import pytest
from PIL import Image

from domain.media.exceptions import MediaNotAvailable
from infrastructure.nasa.apod_client import ApodClient, ApodProvider
from infrastructure.nasa.donki_client import DonkiClient
from infrastructure.nasa.eonet_client import EonetClient
from infrastructure.nasa.epic_availability_client import EpicAvailabilityClient
from infrastructure.nasa.epic_client import EPIC_ARCHIVE_BASE_URL, EpicProvider
from infrastructure.nasa.neows_client import NeoWsClient
from tests.infrastructure.fake_aiohttp import FakeClientSession, FakeResponse


def _fake_png_bytes(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


APOD_URL = "https://api.nasa.gov/planetary/apod"
EPIC_URL = "https://api.nasa.gov/EPIC/api/natural"
DONKI_URL = "https://api.nasa.gov/DONKI/notifications"
NEOWS_URL = "https://api.nasa.gov/neo/rest/v1/feed"
EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"


class FakeTranslator:
    async def translate_to_ru(self, text: str) -> str:
        return f"[ru] {text}"


async def test_apod_provider_builds_payload_with_translated_caption():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={"media_type": "image", "url": "http://img", "title": "Title", "explanation": "Text"}
            )
        }
    )
    provider = ApodProvider(ApodClient(session, "key", APOD_URL, FakeTranslator()))

    payload = await provider.fetch(date(2024, 1, 1))

    assert payload.image_url == "http://img"
    assert "[ru] Title" in payload.caption
    assert "[ru] Text" in payload.caption


async def test_apod_provider_appends_copyright_attribution_when_present():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={
                    "media_type": "image",
                    "url": "http://img",
                    "title": "Title",
                    "explanation": "Text",
                    "copyright": "Jane Photographer",
                }
            )
        }
    )
    provider = ApodProvider(ApodClient(session, "key", APOD_URL, FakeTranslator()))

    payload = await provider.fetch(date(2024, 1, 1))

    assert payload.caption.endswith("© Jane Photographer")


async def test_apod_provider_prefers_hdurl_when_present():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={
                    "media_type": "image",
                    "url": "http://img",
                    "hdurl": "http://img-hd",
                    "title": "Title",
                    "explanation": "Text",
                }
            )
        }
    )
    provider = ApodProvider(ApodClient(session, "key", APOD_URL, FakeTranslator()))

    payload = await provider.fetch(date(2024, 1, 1))

    assert payload.image_url == "http://img-hd"


async def test_apod_provider_raises_when_media_is_not_an_image():
    session = FakeClientSession(
        {
            f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(
                json_data={"media_type": "video", "url": "http://img"}
            )
        }
    )
    provider = ApodProvider(ApodClient(session, "key", APOD_URL, FakeTranslator()))

    with pytest.raises(MediaNotAvailable):
        await provider.fetch(date(2024, 1, 1))


async def test_apod_provider_raises_when_nasa_has_no_data_for_date():
    session = FakeClientSession({f"{APOD_URL}?date=2024-01-01&api_key=key": FakeResponse(json_data={"code": 404})})
    provider = ApodProvider(ApodClient(session, "key", APOD_URL, FakeTranslator()))

    with pytest.raises(MediaNotAvailable):
        await provider.fetch(date(2024, 1, 1))


async def test_epic_provider_builds_animation_from_every_returned_frame():
    day = date(2024, 1, 1)
    session = FakeClientSession(
        {
            f"{EPIC_URL}/date/2024-01-01?api_key=key": FakeResponse(
                json_data=[{"image": "frame1"}, {"image": "frame2"}]
            ),
            f"{EPIC_ARCHIVE_BASE_URL}/2024/01/01/png/frame1.png?api_key=key": FakeResponse(body=_fake_png_bytes("red")),
            f"{EPIC_ARCHIVE_BASE_URL}/2024/01/01/png/frame2.png?api_key=key": FakeResponse(
                body=_fake_png_bytes("blue")
            ),
        }
    )
    provider = EpicProvider(session, "key", EPIC_URL)

    payload = await provider.fetch(day)

    gif = Image.open(BytesIO(payload.gif_bytes))
    assert gif.format == "GIF"
    assert gif.n_frames == 2


async def test_epic_provider_raises_when_no_frames_returned():
    session = FakeClientSession({f"{EPIC_URL}/date/2024-01-01?api_key=key": FakeResponse(json_data=[])})
    provider = EpicProvider(session, "key", EPIC_URL)

    with pytest.raises(MediaNotAvailable):
        await provider.fetch(date(2024, 1, 1))


async def test_epic_availability_client_parses_and_sorts_dates():
    session = FakeClientSession(
        {
            f"{EPIC_URL}/all?api_key=key": FakeResponse(
                json_data=[{"date": "2024-01-02 00:00:00"}, {"date": "2024-01-01 00:00:00"}]
            )
        }
    )
    client = EpicAvailabilityClient(session, "key", EPIC_URL)

    dates = await client.fetch_known_dates()

    assert dates == [date(2024, 1, 1), date(2024, 1, 2)]


async def test_donki_client_parses_message_type_and_issue_time():
    session = FakeClientSession(
        {
            f"{DONKI_URL}?startDate=2024-01-01&endDate=2024-01-01&type=all&api_key=key": FakeResponse(
                json_data=[
                    {"messageType": "FLR", "messageIssueTime": "2024-01-01T10:00:00Z"},
                    {"messageType": "Report", "messageIssueTime": "2024-01-01T12:00:00Z"},
                ]
            )
        }
    )
    client = DonkiClient(session, "key", DONKI_URL)

    highlights = await client.fetch_for_day(date(2024, 1, 1))

    assert len(highlights) == 2
    assert highlights[0].message_type == "FLR"
    assert highlights[1].message_type == "Report"


async def test_donki_client_returns_empty_list_when_no_notifications():
    session = FakeClientSession(
        {f"{DONKI_URL}?startDate=2024-01-01&endDate=2024-01-01&type=all&api_key=key": FakeResponse(json_data=[])}
    )
    client = DonkiClient(session, "key", DONKI_URL)

    highlights = await client.fetch_for_day(date(2024, 1, 1))

    assert highlights == []


async def test_donki_client_fetch_for_range_covers_multiple_days():
    session = FakeClientSession(
        {
            f"{DONKI_URL}?startDate=2024-01-01&endDate=2024-01-07&type=all&api_key=key": FakeResponse(
                json_data=[
                    {"messageType": "FLR", "messageIssueTime": "2024-01-02T10:00:00Z"},
                    {"messageType": "GST", "messageIssueTime": "2024-01-05T08:00:00Z"},
                ]
            )
        }
    )
    client = DonkiClient(session, "key", DONKI_URL)

    highlights = await client.fetch_for_range(date(2024, 1, 1), date(2024, 1, 7))

    assert len(highlights) == 2
    assert {highlight.message_type for highlight in highlights} == {"FLR", "GST"}


async def test_neows_client_parses_asteroids_for_the_day():
    session = FakeClientSession(
        {
            f"{NEOWS_URL}?start_date=2024-01-01&end_date=2024-01-01&api_key=key": FakeResponse(
                json_data={
                    "near_earth_objects": {
                        "2024-01-01": [
                            {
                                "name": "Test Asteroid",
                                "estimated_diameter": {
                                    "meters": {"estimated_diameter_min": 10.5, "estimated_diameter_max": 20.5}
                                },
                                "close_approach_data": [{"miss_distance": {"kilometers": "123456.7", "lunar": "0.32"}}],
                                "is_potentially_hazardous_asteroid": True,
                            }
                        ]
                    }
                }
            )
        }
    )
    client = NeoWsClient(session, "key", NEOWS_URL)

    asteroids = await client.fetch_for_day(date(2024, 1, 1))

    assert len(asteroids) == 1
    asteroid = asteroids[0]
    assert asteroid.name == "Test Asteroid"
    assert asteroid.diameter_min_m == 10.5
    assert asteroid.diameter_max_m == 20.5
    assert asteroid.miss_distance_km == 123456.7
    assert asteroid.miss_distance_lunar == 0.32
    assert asteroid.is_hazardous is True


async def test_neows_client_returns_empty_list_when_day_missing():
    session = FakeClientSession(
        {
            f"{NEOWS_URL}?start_date=2024-01-01&end_date=2024-01-01&api_key=key": FakeResponse(
                json_data={"near_earth_objects": {}}
            )
        }
    )
    client = NeoWsClient(session, "key", NEOWS_URL)

    asteroids = await client.fetch_for_day(date(2024, 1, 1))

    assert asteroids == []


def _neows_object(name: str, diameter_max: float) -> dict:
    return {
        "name": name,
        "estimated_diameter": {"meters": {"estimated_diameter_min": 5.0, "estimated_diameter_max": diameter_max}},
        "close_approach_data": [{"miss_distance": {"kilometers": "100000.0", "lunar": "0.26"}}],
        "is_potentially_hazardous_asteroid": False,
    }


async def test_neows_client_fetch_for_range_flattens_asteroids_across_days():
    session = FakeClientSession(
        {
            f"{NEOWS_URL}?start_date=2024-01-01&end_date=2024-01-07&api_key=key": FakeResponse(
                json_data={
                    "near_earth_objects": {
                        "2024-01-01": [_neows_object("First", 20.0)],
                        "2024-01-05": [_neows_object("Second", 40.0)],
                    }
                }
            )
        }
    )
    client = NeoWsClient(session, "key", NEOWS_URL)

    asteroids = await client.fetch_for_range(date(2024, 1, 1), date(2024, 1, 7))

    assert {asteroid.name for asteroid in asteroids} == {"First", "Second"}


async def test_eonet_client_does_not_send_api_key():
    session = FakeClientSession({f"{EONET_URL}?status=open&limit=20": FakeResponse(json_data={"events": []})})
    client = EonetClient(session, EONET_URL)

    await client.fetch_recent()

    assert session.requested_urls == [f"{EONET_URL}?status=open&limit=20"]
    assert "api_key" not in session.requested_urls[0]


def _storm_geometry_point(day: int, lon: float = -80.0, lat: float = 25.0, **extra) -> dict:
    return {"date": f"2024-01-{day:02d}T00:00:00Z", "coordinates": [lon, lat], **extra}


async def test_eonet_client_picks_max_geometry_date_per_event():
    session = FakeClientSession(
        {
            f"{EONET_URL}?status=open&limit=20": FakeResponse(
                json_data={
                    "events": [
                        {
                            "id": "EONET_1",
                            "title": "Tropical Storm",
                            "categories": [{"id": "severeStorms", "title": "Severe Storms"}],
                            "geometry": [
                                _storm_geometry_point(1),
                                _storm_geometry_point(3, lon=-81.0, lat=26.0, magnitudeValue=65.0, magnitudeUnit="kts"),
                                _storm_geometry_point(2),
                            ],
                        }
                    ]
                }
            )
        }
    )
    client = EonetClient(session, EONET_URL)

    highlights = await client.fetch_recent()

    assert len(highlights) == 1
    highlight = highlights[0]
    assert highlight.title == "Tropical Storm"
    assert highlight.category == "Severe Storms"
    assert highlight.event_date == datetime.fromisoformat("2024-01-03T00:00:00+00:00")
    # Магнитуда берётся с последней по дате точки геометрии (EONET хранит
    # её там, не на событии целиком, см. docs/tz/TZ_karta_sobytiya_EONET.md).
    assert highlight.magnitude_value == 65.0
    assert highlight.magnitude_unit == "kts"
    assert highlight.geometry[-1].lon == -81.0
    assert highlight.geometry[-1].lat == 26.0


async def test_eonet_client_skips_events_without_geometry_dates():
    session = FakeClientSession(
        {
            f"{EONET_URL}?status=open&limit=20": FakeResponse(
                json_data={"events": [{"title": "No dates", "categories": [], "geometry": []}]}
            )
        }
    )
    client = EonetClient(session, EONET_URL)

    highlights = await client.fetch_recent()

    assert highlights == []


async def test_eonet_client_skips_geometry_points_without_coordinates():
    session = FakeClientSession(
        {
            f"{EONET_URL}?status=open&limit=20": FakeResponse(
                json_data={
                    "events": [
                        {
                            "id": "EONET_2",
                            "title": "Malformed point",
                            "categories": [],
                            "geometry": [{"date": "2024-01-01T00:00:00Z"}, _storm_geometry_point(2)],
                        }
                    ]
                }
            )
        }
    )
    client = EonetClient(session, EONET_URL)

    highlights = await client.fetch_recent()

    assert len(highlights) == 1
    assert len(highlights[0].geometry) == 1
    assert highlights[0].event_date == datetime.fromisoformat("2024-01-02T00:00:00+00:00")


async def test_eonet_client_parses_full_event_fields():
    session = FakeClientSession(
        {
            f"{EONET_URL}?status=open&limit=20": FakeResponse(
                json_data={
                    "events": [
                        {
                            "id": "EONET_21829",
                            "title": "Wildfire Fairpoint",
                            "description": "3 Miles W from Fairpoint, SD",
                            "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_21829",
                            "closed": None,
                            "categories": [{"id": "wildfires", "title": "Wildfires"}],
                            "sources": [{"id": "IRWIN", "url": "https://irwin.doi.gov/observer/incidents/1"}],
                            "geometry": [_storm_geometry_point(1, magnitudeValue=510.0, magnitudeUnit="acres")],
                        }
                    ]
                }
            )
        }
    )
    client = EonetClient(session, EONET_URL)

    highlights = await client.fetch_recent()

    assert len(highlights) == 1
    highlight = highlights[0]
    assert highlight.id == "EONET_21829"
    assert highlight.description == "3 Miles W from Fairpoint, SD"
    assert highlight.link == "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_21829"
    assert highlight.closed_at is None
    assert highlight.categories == ["Wildfires"]
    assert highlight.sources[0].label == "IRWIN"
    assert highlight.sources[0].url == "https://irwin.doi.gov/observer/incidents/1"
    assert highlight.magnitude_value == 510.0
    assert highlight.magnitude_unit == "acres"


async def test_eonet_client_parses_closed_event():
    session = FakeClientSession(
        {
            f"{EONET_URL}?status=open&limit=20": FakeResponse(
                json_data={
                    "events": [
                        {
                            "id": "EONET_3",
                            "title": "Closed storm",
                            "closed": "2024-01-05T00:00:00Z",
                            "categories": [],
                            "sources": [],
                            "geometry": [_storm_geometry_point(1)],
                        }
                    ]
                }
            )
        }
    )
    client = EonetClient(session, EONET_URL)

    highlights = await client.fetch_recent()

    assert highlights[0].closed_at == datetime.fromisoformat("2024-01-05T00:00:00+00:00")
