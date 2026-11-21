from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    language = State()
    terms = State()
    first_name = State()
    last_name = State()
    phone = State()
    profile_type = State()
