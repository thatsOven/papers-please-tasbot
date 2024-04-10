from collections import namedtuple
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Iterable

Point = namedtuple("Point", "x y")
Area = namedtuple("Area", "left top right bottom")


class DayCoordinates(Sequence):
    """Coordinates for day buttons on the save screen"""
    def __init__(self, dayX: Iterable[int], dayY: Iterable[int]):
        self._Point = [[Point(x, y) for x in dayX] for y in dayY]

    def __getitem__(self, day: int | tuple[int, int]) -> list[Point] | Point:
        if isinstance(day, int):
            return self._Point[day]
        if isinstance(day, tuple) and len(day) == 2:
            return self._Point[day[0]][day[1]]
        raise IndexError(f'bad day coordinates index {day}')

    def __len__(self) -> iter:
        return len(self._Point)


ZERO_POINT = Point(105, 60)

# Main Menu
MAIN_STORY = Point(284, 246)
MAIN_ENDLESS = Point(284, 271)
MAIN_QUIT = Point(551, 20)
MAIN_SETTINGS = Point(23, 296)

# Endless
ENDLESS_BACK = Point(63, 290)
ENDLESS_PLAY = Point(284, 290)
ENDLESS_LEADERBOARD = Point(516, 290)
ENDLESS_TIMED = Point(134, 99)
ENDLESS_PERFECTION = Point(284, 99)
ENDLESS_ENDURANCE = Point(434, 99)
ENDLESS_PAPERS_0 = Point(135, 206)
ENDLESS_PAPERS_1 = Point(237, 206)
ENDLESS_PAPERS_2 = Point(338, 206)
ENDLESS_PAPERS_3 = Point(438, 206)
ENDLESS_OVER_OKAY = Point(284, 218)

# Save Menu
# TODO Fill out day save coordinates
SAVE_DAYS_X = (
    36,
    200,
    340,
    480,
    620,
    750,
    900,
    1040
)
SAVE_DAYS_Y = (
    90,
    290,
    370,
    450,
    530
)
SAVE_DAYS = DayCoordinates(SAVE_DAYS_X, SAVE_DAYS_Y)
SAVE_NEW = SAVE_DAYS[0][0]
SAVE_BACK = Point(284, 299)
SAVE_PIXEL = Point(1, 41)

# Cutscene
CUTSCENE_INTRO_NEXT = Point(284, 299)
WALK_TO_WORK = Point(284, 299)

# Outside Booth
OUTSIDE_GROUND = Point(477, 14)
OUTSIDE_HORN = Point(174, 74)
OUTSIDE_SPEAKER_NEXT = Area(172, 46, 175, 52)

# Booth Entrant Area
BOOTH_WALL_CHECK = Point(72, 206)
BOOTH_ENTRANT = Point(87, 184)
BOOTH_SHUTTER_TOGGLE = Point(171, 121)
BOOTH_SHUTTER_CHECK = Point(147, 198)

# Left Booth Desk
BOOTH_LEFT_PAPERS = Point(89, 255)

# Right Booth Desk
BOOTH_STAMP_BAR_TOGGLE = Point(566, 158)
BOOTH_PASSPORT_FLING = Point(280, 235)
BOOTH_PASSPORT_STAMP_POSITION = Point(428, 233)
BOOTH_PASSPORT_REGRAB = Point(442, 227)
BOOTH_PASSPORT_FLING_CORRECTION = Point(363, 302)
STAMP_APPROVE = Point(487, 140)
STAMP_DENY = Point(366, 140)

# Night
NIGHT_SLEEP_TEXT_AREA = Area(513, 281, 544, 293)
NIGHT_SLEEP_CLICK = Point(497, 287)
NIGHT_TICK_AREA = Area(180, 90, 300, 300)
NIGHT_TICK_CLICK_OFFSET = Point(216, 6)

# TODO All the rest of the coordinates below
PAPER_SCAN_POS = Point(750, 450)

VISA_SLIP_DENY_POS = PAPER_SCAN_POS
VISA_SLIP_ALLOW_POS = Point(975, 450)
INITIAL_BULLETIN_POS = PAPER_SCAN_POS
RIGHT_BULLETIN_POS = Point(1135, PAPER_SCAN_POS.y)
BULLETIN_NEXT_BUTTON = Point(885, 630)
NO_PASSPORT_CLICK_POS = Point(275, 525)
CLEANUP_POS = Point(10, 525)

STAMP_ENABLE = Point(1130, 340)
STAMP_DISABLE = Point(595, 350)

BULLETIN_POS = Point(100, 620)
RULEBOOK_POS = Point(250, 620)
INSPECT_BUTTON = Point(1110, 650)
INTERROGATE_BUTTON = Point(175, 610)
TRANSCRIPTION_POS = INTERROGATE_BUTTON

RULEBOOK_BOOKMARK_BUTTON = Point(530, 300)


@dataclass(frozen=True, slots=True)
class RuleBook:
    @dataclass(frozen=True, slots=True)
    class _BasicRules:
        pos: Point[int, int]
        entrants_must_have_passport: Point = None
        citizens_must_have_id: Point = None
        foreigners_require_entry_permit: Point = None
        workers_must_have_workpass: Point = None
        diplomats_require_authorization: Point = None
        foreigners_require_idsuppl: Point = None
        asylum_seekers_need_grant: Point = None
        entrant_must_have_vaxcert: Point = None
        no_entry_from_impor: Point = None
        no_entry_from_unitedfed: Point = None
        foreigners_require_access_permit: Point = None

    @dataclass(frozen=True, slots=True)
    class _RegionMap:
        pos: Point
        obristan: Point = None
        kolechia: Point = None
        antegria: Point = None
        arstotzka: Point = None
        republia: Point = None
        unitedfed: Point = None
        impor: Point = None
        issuing_cities: Point = None
        diplomatic_seal: Point = None

    @dataclass(frozen=True, slots=True)
    class _Documents:
        @dataclass(frozen=True, slots=True)
        class _IdCard:
            pos: Point
            districts: Point = None

        @dataclass(frozen=True, slots=True)
        class _DocumentWithSeal:
            pos: Point
            seals: Point = None
            document_must_have_seal: Point = None

        @dataclass(frozen=True, slots=True)
        class _DiplomaticAuth:
            pos: Point
            auth_arstotzka: Point = None
            document_must_have_seal: Point = None

        @dataclass(frozen=True, slots=True)
        class _VaxCert:
            pos: Point
            polio_vax_required: Point = None

        pos: Point
        id_card: _IdCard = None
        entry_permit: _DocumentWithSeal = None
        access_permit: _DocumentWithSeal = None
        work_pass: _DocumentWithSeal = None
        diplomatic_auth: _DiplomaticAuth = None
        grant_asylum: _DocumentWithSeal = None
        vax_cert: _VaxCert = None

    basic_rules: _BasicRules
    region_map: _RegionMap
    documents: _Documents


RULEBOOK = RuleBook(
    RuleBook._BasicRules(
        pos=Point(835, 385),
        entrants_must_have_passport=Point(620, 345),
        citizens_must_have_id=Point(620, 450),
        foreigners_require_entry_permit=Point(620, 500),
        workers_must_have_workpass=Point(620, 550),
        diplomats_require_authorization=Point(850, 400),
        foreigners_require_idsuppl=Point(850, 450),
        asylum_seekers_need_grant=Point(850, 500),
        entrant_must_have_vaxcert=Point(850, 550),
        no_entry_from_impor=Point(850, 500),
        no_entry_from_unitedfed=Point(850, 550)
    ),
    RuleBook._RegionMap(
        pos=Point(840, 420),
        obristan=Point(670, 320),
        kolechia=Point(830, 345),
        antegria=Point(600, 405),
        arstotzka=Point(910, 475),
        republia=Point(640, 490),
        unitedfed=Point(550, 540),
        impor=Point(690, 565),
        issuing_cities=Point(790, 490),
        diplomatic_seal=Point(620, 480)
    ),
    RuleBook._Documents(
        pos=Point(840, 490),
        id_card=RuleBook._Documents._IdCard(
            pos=Point(840, 365),
            districts=Point(825, 425)
        ),
        entry_permit=RuleBook._Documents._DocumentWithSeal(
            pos=Point(840, 400),
            seals=Point(865, 400),
            document_must_have_seal=Point(865, 550)
        ),
        work_pass=RuleBook._Documents._DocumentWithSeal(
            pos=Point(840, 460),
            seals=Point(860, 440),
            document_must_have_seal=Point(865, 550)
        ),
        diplomatic_auth=RuleBook._Documents._DiplomaticAuth(
            pos=Point(840, 490),
            auth_arstotzka=Point(865, 440),
            document_must_have_seal=Point(865, 550)
        ),
        grant_asylum=RuleBook._Documents._DocumentWithSeal(
            pos=Point(840, 520),
            seals=Point(865, 400),
            document_must_have_seal=Point(865, 550)
        )
    )
)

RULEBOOK_DAY_27 = RuleBook(
    RuleBook._BasicRules(
        pos=Point(835, 385),
        entrants_must_have_passport=Point(620, 345),
        citizens_must_have_id=Point(620, 450),
        workers_must_have_workpass=Point(620, 500),
        diplomats_require_authorization=Point(850, 345),
        asylum_seekers_need_grant=Point(850, 400),
        entrant_must_have_vaxcert=Point(850, 450),
        foreigners_require_access_permit=Point(850, 500)
    ),
    RuleBook._RegionMap(
        pos=Point(840, 420),
        obristan=Point(670, 320),
        kolechia=Point(830, 345),
        antegria=Point(600, 405),
        arstotzka=Point(910, 475),
        republia=Point(640, 490),
        unitedfed=Point(550, 540),
        impor=Point(690, 565),
        issuing_cities=Point(790, 490),
        diplomatic_seal=Point(620, 480)
    ),
    RuleBook._Documents(
        pos=Point(840, 490),
        id_card=RuleBook._Documents._IdCard(
            pos=Point(840, 365),
            districts=Point(825, 425)
        ),
        access_permit=RuleBook._Documents._DocumentWithSeal(
            pos=Point(840, 400),
            seals=Point(865, 400),
            document_must_have_seal=Point(865, 550)
        ),
        work_pass=RuleBook._Documents._DocumentWithSeal(
            pos=Point(840, 430),
            seals=Point(860, 440),
            document_must_have_seal=Point(865, 550)
        ),
        diplomatic_auth=RuleBook._Documents._DiplomaticAuth(
            pos=Point(840, 460),
            auth_arstotzka=Point(865, 440),
            document_must_have_seal=Point(865, 550)
        ),
        grant_asylum=RuleBook._Documents._DocumentWithSeal(
            pos=Point(840, 490),
            seals=Point(865, 400),
            document_must_have_seal=Point(865, 550)
        ),
        vax_cert=RuleBook._Documents._VaxCert(
            pos=Point(840, 520),
            polio_vax_required=Point(865, 520)
        )
    )
)

DIGITS_LENGTH = 8
DIGITS_HEIGHT = 10

PERSON_POS = Point(175, 350)
PERSON_PASSPORT_POS = Point(175, 380)

TABLE_AREA = Area(365, 240, 1135, 670)
GIVE_AREA = Area(0, 455, 350, 565)
HORN_MESSAGE_AREA = Area(290, 115, 445, 160)
VISA_SLIP_AREA = Area(503, 157, 744, 358)
WEIGHT_AREA = Area(309, 627, 336, 637)
EXIT_AREAS = (
    Area(285, 180, 296, 235),
    Area(400, 160, 415, 235)
)

MATCHING_DATA_MESSAGE_SIZE = Point(105, 40)

PASSPORT_TABLE_OFFSET = Point(255, 49)

SLEEP_BUTTON = Point(965, 495)

TRANSCRIPTION_PAGE_TEXT_AREA = Area(261, 43, 512, 378)
TRANSCRIPTION_TEXT_Y_SIZE = 14
TRANSCRIPTION_LINE_OFFSET = 4
TRANSCRIPTION_TEXTBOX_TEXT_OFFSET = Point(2, 4)
TRANSCRIPTION_TEXTBOXES_Y_OFFSET = 4

SLOTS = (
    Point(1010, 300),
    Point(780, 300),
    Point(480, 300),
    Point(480, 650),
    Point(780, 650),
    Point(1010, 650)
)

END_TICK_X = 805

CONTINUE_BUTTON = Point(570, 430)
EZIC_MESSAGE_OPEN = Point(745, 380)

WANTED = (
    Point(1050, 370),
    Point(1050, 470),
    Point(1050, 570)
)

TRANQ_GUN_ENABLE_KEY_POS = Point(1090, 370)
SNIPER_ENABLE_KEYPOS = Point(1090, 495)
ATTACKER_GRENADE_DETECT_ZONE = Area(630, 85, 670, 160)

ATTACKER_WALL_DETECT_ZONE = Area(368, 61, 404, 100)
ATTACKER_DETONATE_DETECT_ZONE = Area(518, 61, 526, 160)

REASON_STAMP = Point(450, 350)
PASSPORT_REASON_POS = Point(450, 450)

LEFT_SCAN_SLOT = Point(550, 450)
RIGHT_SCAN_SLOT = Point(980, 450)

CLOCK_POS = Point(30, 630)

SHUTTER_LEVER = Point(335, 270)
PASSPORT_CONFISCATE_POS = Point(470, 665)

PERSON_AREA = Area(8, 237, 363, 445)
DRAG_TO_WITH_GIVE_AMPLITUDE = Point(
    PERSON_AREA.right - PERSON_POS.x - 100,
    PERSON_AREA.bottom - PERSON_POS.y - 50
)

DRAG_TO_WITH_GIVE_THETA_INC = Point(0.75, 0.5)
DRAG_TO_WITH_GIVE_POS_OFFS = Point(0, 20)

CIVILIANS_AREA = Area(16, 31, 236, 236)
GUARDS_AREA = Area(600, 61, 940, 236)
