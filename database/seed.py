from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    District,
    Listing,
    ListingStatus,
    ListingType,
    PriceUnit,
    PropertyType,
    Region,
    User,
)

PROPERTY_TYPES = [
    ("apartment", "Kvartira", "Квартира"),
    ("house", "Hovli", "Дом"),
    ("new_building", "Yangi qurilgan uy", "Новостройка"),
    ("land", "Yer maydoni", "Земельный участок"),
    ("commercial", "Tijorat binosi", "Коммерческое здание"),
    ("dacha", "Dacha", "Дача"),
    ("office", "Ofis", "Офис"),
    ("shop", "Do'kon", "Магазин"),
    ("warehouse", "Ombor", "Склад"),
    ("production", "Ishlab chiqarish binosi", "Производственное здание"),
    ("restaurant", "Restoran uchun joy", "Помещение под ресторан"),
    ("non_residential_land", "Noturar yer maydoni", "Нежилая земля"),
]

REGIONS = [
    (
        "tashkent_city",
        "Toshkent shahri",
        "Город Ташкент",
        [
            ("Chilonzor tumani", "Чиланзарский район"),
            ("Yakkasaroy tumani", "Яккасарайский район"),
            ("Yunusobod tumani", "Юнусабадский район"),
            ("Mirzo Ulug'bek tumani", "Мирзо-Улугбекский район"),
            ("Mirobod tumani", "Мирободский район"),
            ("Sergeli tumani", "Сергелийский район"),
            ("Olmazor tumani", "Олмазорский район"),
            ("Uchtepa tumani", "Учтепинский район"),
            ("Shayxontohur tumani", "Шайхантахурский район"),
            ("Bektemir tumani", "Бектемирский район"),
            ("Hamza tumani", "Хамзинский район"),
            ("Zangiota tumani", "Зангиатинский район"),
        ],
    ),
    (
        "tashkent_region",
        "Toshkent viloyati",
        "Ташкентская область",
        [
            ("Angren shahri", "Город Ангрен"),
            ("Chirchiq shahri", "Город Чирчик"),
            ("Olmaliq shahri", "Город Алмалык"),
            ("Yangiyo'l shahri", "Город Янгиюль"),
            ("Bekobod shahri", "Город Бекабад"),
            ("Angren tumani", "Ангренский район"),
            ("Bekobod tumani", "Бекабадский район"),
            ("Bostonli tumani", "Бостанлыкский район"),
            ("Chinaz tumani", "Чиназский район"),
            ("Piskent tumani", "Пискентский район"),
            ("Quyichirchiq tumani", "Нижнечирчикский район"),
            ("Tayloq tumani", "Тайлокский район"),
            ("Yangiobod tumani", "Янгиободский район"),
            ("Zangiota tumani", "Зангиатинский район"),
        ],
    ),
    (
        "samarkand",
        "Samarqand viloyati",
        "Самаркандская область",
        [
            ("Samarqand shahri", "Город Самарканд"),
            ("Bulung'ur tumani", "Булунгурский район"),
            ("Jomboy tumani", "Джамбойский район"),
            ("Kattaqo'rg'on tumani", "Катакурганский район"),
            ("Nurobod tumani", "Нурободский район"),
            ("Oqdaryo tumani", "Акдарьинский район"),
            ("Pastdarg'om tumani", "Пастдаргомский район"),
            ("Paxtachi tumani", "Пахтачийский район"),
            ("Payariq tumani", "Паярикский район"),
            ("Qo'shrabot tumani", "Кошрабатский район"),
            ("Saqlovchi tumani", "Сакловчинский район"),
            ("Tayloq tumani", "Тайлокский район"),
            ("Urgut tumani", "Ургутский район"),
        ],
    ),
    (
        "andijan",
        "Andijon viloyati",
        "Андижанская область",
        [
            ("Andijon shahri", "Город Андижан"),
            ("Asaka shahri", "Город Асака"),
            ("Xonobod shahri", "Город Хонабад"),
            ("Andijon tumani", "Андижанский район"),
            ("Baliqchi tumani", "Баликчинский район"),
            ("Bo'ston tumani", "Бостонский район"),
            ("Izboskan tumani", "Избасканский район"),
            ("Jalaquduq tumani", "Джалакудукский район"),
            ("Marhamat tumani", "Мархаматский район"),
            ("Oltinko'l tumani", "Олтинкульский район"),
            ("Paxtobod tumani", "Пахтабадский район"),
            ("Qo'rg'ontepa tumani", "Кургантепинский район"),
            ("Shahrixon tumani", "Шахриханский район"),
            ("Ulug'nor tumani", "Улугнорский район"),
        ],
    ),
    (
        "fergana",
        "Farg'ona viloyati",
        "Ферганская область",
        [
            ("Farg'ona shahri", "Город Фергана"),
            ("Quvasoy shahri", "Город Кувасай"),
            ("Marg'ilon shahri", "Город Маргилан"),
            ("Oltiariq tumani", "Олтиарикский район"),
            ("Bag'dod tumani", "Багдадский район"),
            ("Buvayda tumani", "Бувайдинский район"),
            ("Dang'ara tumani", "Дангаринский район"),
            ("Farg'ona tumani", "Ферганский район"),
            ("Qo'shtepa tumani", "Коштепинский район"),
            ("Rishton tumani", "Риштанский район"),
            ("So'x tumani", "Сохский район"),
            ("Toshloq tumani", "Ташлакский район"),
            ("Uchko'prik tumani", "Учкуприкский район"),
            ("Yozyovon tumani", "Ёзовонский район"),
        ],
    ),
    (
        "namangan",
        "Namangan viloyati",
        "Наманганская область",
        [
            ("Namangan shahri", "Город Наманган"),
            ("Chortoq shahri", "Город Чартак"),
            ("Kosonobod shahri", "Город Косанабад"),
            ("Chust tumani", "Чустский район"),
            ("Koson tumani", "Косонский район"),
            ("Mingbuloq tumani", "Мингбулакский район"),
            ("Namangan tumani", "Наманганский район"),
            ("Norin tumani", "Нарынский район"),
            ("Pop tumani", "Папский район"),
            ("To'raqo'rg'on tumani", "Туракурганский район"),
            ("Uchqo'rg'on tumani", "Учкурганский район"),
            ("Yangiqo'rg'on tumani", "Янгикурганский район"),
        ],
    ),
    (
        "bukhara",
        "Buxoro viloyati",
        "Бухарская область",
        [
            ("Buxoro shahri", "Город Бухара"),
            ("Buxoro tumani", "Бухарский район"),
            ("G'ijduvon tumani", "Гиждуванский район"),
            ("Jondor tumani", "Джондорский район"),
            ("Kogon tumani", "Когонский район"),
            ("Peshku tumani", "Пешкунский район"),
            ("Qorako'l tumani", "Каракульский район"),
            ("Qorovulbozor tumani", "Караулбазарский район"),
            ("Romitan tumani", "Ромитанский район"),
            ("Shofirkon tumani", "Шафирканский район"),
            ("Vobkent tumani", "Вабкентский район"),
        ],
    ),
    (
        "khorezm",
        "Xorazm viloyati",
        "Хорезмская область",
        [
            ("Urganch shahri", "Город Ургенч"),
            ("Xiva shahri", "Город Хива"),
            ("Bog'ot tumani", "Багатский район"),
            ("Gurlan tumani", "Гурленский район"),
            ("Hazorasp tumani", "Хазараспский район"),
            ("Shovot tumani", "Шаватский район"),
            ("Urganch tumani", "Ургенчский район"),
            ("Vazir tumani", "Вазирский район"),
            ("Yangiariq tumani", "Янгиарыкский район"),
            ("Yangibozor tumani", "Янгибазарский район"),
        ],
    ),
    (
        "navoiy",
        "Navoiy viloyati",
        "Навойийская область",
        [
            ("Navoiy shahri", "Город Навои"),
            ("Zarafshon shahri", "Город Зарафшан"),
            ("Karmana tumani", "Карманинский район"),
            ("Konimex tumani", "Конимехский район"),
            ("Navbahor tumani", "Навбахорский район"),
            ("Nurota tumani", "Нуратинский район"),
            ("Qiziltepa tumani", "Кызылтепинский район"),
            ("Tomdi tumani", "Тамдынский район"),
            ("Uchquduq tumani", "Учкудукский район"),
            ("Xatirchi tumani", "Хатирчинский район"),
        ],
    ),
    (
        "jizzakh",
        "Jizzax viloyati",
        "Джизакская область",
        [
            ("Jizzax shahri", "Город Джизак"),
            ("Arnasoy tumani", "Арнасайский район"),
            ("Baxmal tumani", "Бахмальский район"),
            ("Dostlik tumani", "Достукский район"),
            ("Forish tumani", "Форишский район"),
            ("G'allyazor tumani", "Галляаральский район"),
            ("Mirzacho'l tumani", "Мирзачульский район"),
            ("Paxtakor tumani", "Пахтакорский район"),
            ("Sharof Rashidov tumani", "Шараф Рашидовский район"),
            ("Zomin tumani", "Зааминский район"),
        ],
    ),
    (
        "sirdaryo",
        "Sirdaryo viloyati",
        "Сырдарьинская область",
        [
            ("Guliston shahri", "Город Гулистан"),
            ("Yangiyer shahri", "Город Янгиер"),
            ("Shirin shahri", "Город Ширин"),
            ("Boyovut tumani", "Боёвутский район"),
            ("Farod tumani", "Фародский район"),
            ("Guliston tumani", "Гулистанский район"),
            ("Mirzabuloq tumani", "Мирзабулакский район"),
            ("Oqoltin tumani", "Аколтинский район"),
            ("Sardoba tumani", "Сардобинский район"),
            ("Sirdaryo tumani", "Сырдарьинский район"),
            ("Xovos tumani", "Хавасский район"),
        ],
    ),
    (
        "kashkadarya",
        "Qashqadaryo viloyati",
        "Кашкадарьинская область",
        [
            ("Qarshi shahri", "Город Карши"),
            ("Shahrisabz shahri", "Город Шахрисабз"),
            ("Chiroqchi tumani", "Чирокчинский район"),
            ("Dehqonobod tumani", "Дехканабадский район"),
            ("G'uzor tumani", "Гузарский район"),
            ("Kasbi tumani", "Касбийский район"),
            ("Kitob tumani", "Китобский район"),
            ("Koson tumani", "Косонский район"),
            ("Mirishkor tumani", "Миришкорский район"),
            ("Muborak tumani", "Мубарекский район"),
            ("Nishon tumani", "Нишонский район"),
            ("Qamashi tumani", "Камашинский район"),
            ("Qarshi tumani", "Каршинский район"),
            ("Shahrisabz tumani", "Шахрисабзский район"),
            ("Yakkabog' tumani", "Яккабагский район"),
        ],
    ),
    (
        "surkhandarya",
        "Surxondaryo viloyati",
        "Сурхандарьинская область",
        [
            ("Termiz shahri", "Город Термез"),
            ("Angor tumani", "Ангарский район"),
            ("Bandixon tumani", "Бандихонский район"),
            ("Boysun tumani", "Байсунский район"),
            ("Denov tumani", "Денауский район"),
            ("Jarqo'rg'on tumani", "Джаркурганский район"),
            ("Qiziriq tumani", "Кизирикский район"),
            ("Qorako'l tumani", "Каракульский район"),
            ("Sariosiyo tumani", "Сариасийский район"),
            ("Shorabod tumani", "Шорабадский район"),
            ("Termiz tumani", "Термезский район"),
            ("Uzun tumani", "Узунский район"),
            ("Yangibozor tumani", "Янгибазарский район"),
        ],
    ),
    (
        "karakalpakstan",
        "Qoraqalpog'iston Respublikasi",
        "Республика Каракалпакстан",
        [
            ("Nukus shahri", "Город Нукус"),
            ("Amudaryo tumani", "Амударьинский район"),
            ("Beruniy tumani", "Берунийский район"),
            ("Bo'zatov tumani", "Бозатауский район"),
            ("Chimboy tumani", "Чимбайский район"),
            ("Ellikkala tumani", "Элликкалинский район"),
            ("Kegeyli tumani", "Кегейлийский район"),
            ("Mo'ynoq tumani", "Муйнакский район"),
            ("Nukus tumani", "Нукусский район"),
            ("Qonliko'l tumani", "Конликульский район"),
            ("Qorao'zak tumani", "Караузякский район"),
            ("Shumanay tumani", "Шуманайский район"),
            ("Taxtakopir tumani", "Тахтакупырский район"),
            ("To'rtko'l tumani", "Турткульский район"),
            ("Xo'jayli tumani", "Ходжейлийский район"),
        ],
    ),
]


async def seed_reference_data(session: AsyncSession) -> None:
    existing_types = set((await session.scalars(select(PropertyType.code))).all())
    for index, (code, name_uz, name_ru) in enumerate(PROPERTY_TYPES):
        if code not in existing_types:
            session.add(
                PropertyType(
                    code=code,
                    name_uz=name_uz,
                    name_ru=name_ru,
                    sort_order=index,
                )
            )

    existing_regions = set((await session.scalars(select(Region.code))).all())
    for code, name_uz, name_ru, districts in REGIONS:
        if code in existing_regions:
            continue
        region = Region(code=code, name_uz=name_uz, name_ru=name_ru)
        session.add(region)
        await session.flush()
        for district_uz, district_ru in districts:
            session.add(
                District(
                    region_id=region.id,
                    name_uz=district_uz,
                    name_ru=district_ru,
                )
            )
    await session.flush()


async def seed_sample_sale_houses(session: AsyncSession) -> None:
    existing = set(
        (
            await session.scalars(
                select(Listing.title).where(Listing.title.like("Namuna uy %"))
            )
        ).all()
    )
    owner_id = (await session.scalars(select(User.id).order_by(User.id).limit(1))).first()
    property_type_id = (
        await session.scalars(select(PropertyType.id).where(PropertyType.code == "house"))
    ).first()
    region = (
        await session.execute(select(Region).where(Region.code == "tashkent_city"))
    ).scalar_one_or_none()
    if owner_id is None or property_type_id is None or region is None:
        return
    districts = (
        await session.scalars(
            select(District)
            .where(District.region_id == region.id)
            .order_by(District.id)
            .limit(10)
        )
    ).all()
    now = datetime.now(timezone.utc)
    for index, district in enumerate(districts, start=1):
        title = f"Namuna uy {index}"
        if title in existing:
            continue
        session.add(
            Listing(
                user_id=owner_id,
                listing_type=ListingType.SALE,
                property_type_id=property_type_id,
                region_id=region.id,
                district_id=district.id,
                title=title,
                description="Namuna: sotiladigan hovli",
                price=Decimal(120_000 + index * 15_000),
                price_unit=PriceUnit.TOTAL,
                area=Decimal(80 + index * 5),
                rooms=3 + index % 3,
                floor=2,
                total_floors=2,
                built_year=2015 + index,
                condition="good",
                status=ListingStatus.ACTIVE,
                published_at=now,
                expires_at=now + timedelta(days=365),
                contact_phone="",
            )
        )
    await session.flush()
