from aiogram.fsm.state import State, StatesGroup


class EditProfile(StatesGroup):
    first_name = State()
    last_name = State()
    phone = State()
    profile_type = State()
    language = State()


class CommonFlow(StatesGroup):
    inquiry_name = State()
    inquiry_purpose = State()
    inquiry_message = State()
    inquiry_phone = State()
    inquiry_reply = State()
    report_details = State()
    saved_search_name = State()
    viewing_date = State()
    viewing_time = State()
    viewing_note = State()
    viewing_propose_date = State()
    viewing_propose_time = State()
    broadcast_message = State()
    broadcast_region = State()
    reject_reason = State()
    fix_reason = State()
    warning_message = State()
    admin_message = State()
    region_name_uz = State()
    region_name_ru = State()
    region_code = State()
    district_region_id = State()
    district_name_uz = State()
    district_name_ru = State()
    user_search = State()
