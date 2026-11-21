from aiogram.fsm.state import State, StatesGroup


class NewListing(StatesGroup):
    listing_type = State()
    property_type = State()
    region = State()
    district = State()
    neighborhood = State()
    area = State()
    rooms = State()
    floor = State()
    total_floors = State()
    built_year = State()
    condition = State()
    renovation = State()
    furnished = State()
    description = State()
    price = State()
    price_unit = State()
    contact_phone = State()
    extra = State()
    family = State()
    students = State()
    long_term = State()
    deposit = State()
    utilities = State()
    guests = State()
    location = State()
    images = State()
    video = State()
    confirm = State()
    edit_choice = State()
    edit_value = State()


class EditListing(StatesGroup):
    price = State()
