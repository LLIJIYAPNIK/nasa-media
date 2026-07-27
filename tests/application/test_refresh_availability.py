from datetime import date

from application.epic.refresh_availability import RefreshEpicAvailability
from tests.application.fakes import FakeEpicRepository


class FakeAvailabilityIndex:
    def __init__(self, dates: list[date]) -> None:
        self.dates = dates

    async def fetch_known_dates(self) -> list[date]:
        return self.dates


async def test_refresh_adds_new_dates_and_keeps_existing_ones_untouched():
    repo = FakeEpicRepository()
    await repo.ensure_known_dates([date(2024, 1, 1)])
    use_case = RefreshEpicAvailability(FakeAvailabilityIndex([date(2024, 1, 1), date(2024, 1, 2)]), repo)

    await use_case.execute()

    assert await repo.get_by_date(date(2024, 1, 1)) is not None
    assert await repo.get_by_date(date(2024, 1, 2)) is not None
