from aiogram.fsm.state import State, StatesGroup


class ApodCurrentDateForm(StatesGroup):
    current_date = State()


class ApodDateRangeForm(StatesGroup):
    start_date = State()
    end_date = State()


class EpicDateForm(StatesGroup):
    date = State()
