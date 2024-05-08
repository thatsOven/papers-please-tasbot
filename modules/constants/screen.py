STORY_BUTTON = (565, 515)
NEW_BUTTON   = (75, 200)
INTRO_BUTTON = (565, 625)

HORN = (345, 175)

PAPER_POS          = (175, 525)
PAPER_SCAN_POS     = (750, 450)
PASSPORT_ALLOW_POS = (975, 490)
PASSPORT_DENY_POS  = (735, 490)

VISA_SLIP_DENY_POS    = PAPER_SCAN_POS
VISA_SLIP_ALLOW_POS   = (975, 450)
INITIAL_BULLETIN_POS  = PAPER_SCAN_POS 
RIGHT_BULLETIN_POS    = (1135, PAPER_SCAN_POS[1])
BULLETIN_NEXT_BUTTON  = (885, 630)
NO_PASSPORT_CLICK_POS = (275, 525)
CLEANUP_POS           = ( 10, 525)

STAMP_ENABLE  = (1130, 340)
STAMP_APPROVE = (1000, 310)
STAMP_DENY    = (735, 310)
STAMP_DISABLE = (595, 350)

BULLETIN_POS   = ( 100, 620)
RULEBOOK_POS   = ( 250, 620)
INSPECT_BUTTON = (1110, 650)
INTERROGATE_BUTTON = (175, 610)
TRANSCRIPTION_POS  = INTERROGATE_BUTTON

RULEBOOK_BOOKMARK_BUTTON = (530, 300)

RULEBOOK = {
    "basic-rules": {
        "pos": (835, 385),
        "entrants-must-have-passport": (620, 345),
        "citizens-must-have-id": (620, 450),
        "foreigners-require-entry-permit": (620, 500),
        "workers-must-have-workpass": (620, 550),
        "diplomats-require-authorization": (850, 400),
        "foreigners-require-idsuppl": (850, 450),
        "asylum-seekers-need-grant": (850, 500),
        "entrant-must-have-vaxcert": (850, 550),
        "no-entry-from-impor": (850, 500),
        "no-entry-from-unitedfed": (850, 550)
    },
    "region-map": {
        "pos": (840, 420),
        "obristan": (670, 320),
        "kolechia": (830, 345),
        "antegria": (600, 405),
        "arstotzka": (910, 475),
        "republia": (640, 490),
        "unitedfed": (550, 540),
        "impor": (690, 565),
        "issuing-cities": (790, 490),
        "diplomatic-seal": (620, 480)
    },
    "documents": {
        "pos": (840, 490),
        "id-card": {
            "pos": (840, 365),
            "districts": (825, 425)
        },
        "entry-permit": {
            "pos": (840, 400),
            "seals": (865, 400),
            "document-must-have-seal": (865, 550)
        },
        "work-pass": {
            "pos": (840, 460),
            "seals": (860, 440),
            "document-must-have-seal": (865, 550)
        },
        "diplomatic-auth": {
            "pos": (840, 490),
            "auth-arstotzka": (865, 440),
            "document-must-have-seal": (865, 550)
        },
        "grant-asylum": {
            "pos": (840, 520),
            "seals": (865, 400),
            "document-must-have-seal": (865, 550)
        }
    }
}

RULEBOOK_DAY_27 = {
    "basic-rules": {
        "pos": (835, 385),
        "entrants-must-have-passport": (620, 345),
        "citizens-must-have-id": (620, 450),
        "workers-must-have-workpass": (620, 500),
        "diplomats-require-authorization": (850, 345),
        "asylum-seekers-need-grant": (850, 400),
        "entrants-must-have-vaxcert": (850, 450),
        "foreigners-require-access-permit": (850, 500),
    },
    "region-map": {
        "pos": (840, 420),
        "obristan": (670, 320),
        "kolechia": (830, 345),
        "antegria": (600, 405),
        "arstotzka": (910, 475),
        "republia": (640, 490),
        "unitedfed": (550, 540),
        "impor": (690, 565),
        "issuing-cities": (790, 490),
        "diplomatic-seal": (620, 480)
    },
    "documents": {
        "pos": (840, 490),
        "id-card": {
            "pos": (840, 365),
            "districts": (825, 425)
        },
        "access-permit": {
            "pos": (840, 400),
            "seals": (865, 400),
            "document-must-have-seal": (865, 550)
        },
        "work-pass": {
            "pos": (840, 430),
            "seals": (860, 440),
            "document-must-have-seal": (865, 550)
        },
        "diplomatic-auth": {
            "pos": (840, 460),
            "auth-arstotzka": (865, 440),
            "document-must-have-seal": (865, 550)
        },
        "grant-asylum": {
            "pos": (840, 490),
            "seals": (865, 400),
            "document-must-have-seal": (865, 550)
        },
        "vax-cert": {
            "pos": (840, 520),
            "polio-vax-required": (865, 520)
        }
    }
}

DIGITS_LENGTH = 8
DIGITS_HEIGHT = 10

PERSON_POS = (175, 350)
PERSON_PASSPORT_POS = (175, 380)

TABLE_AREA        = (365, 240, 1135, 670)
GIVE_AREA         = (  8, 455,  350, 565)
NEXT_BUBBLE_AREA  = (352, 123,  358, 135)
VISA_SLIP_AREA    = (503, 157,  744, 358)
WEIGHT_AREA       = (309, 627,  336, 637)
EXIT_AREAS = (
    (285, 180, 296, 235),
    (400, 160, 415, 235)
)

MATCHING_DATA_MESSAGE_SIZE = (105, 40)

SLEEP_BUTTON = (965, 615)

TRANSCRIPTION_PAGE_TEXT_AREA      = (26, 32, 277, 367)
TRANSCRIPTION_TEXT_Y_SIZE         = 14
TRANSCRIPTION_LINE_OFFSET         = 4
TRANSCRIPTION_TEXTBOX_TEXT_OFFSET = (2, 4)
TRANSCRIPTION_TEXTBOXES_Y_OFFSET  = 4

SLOTS = (
    (1010, 300),
    ( 780, 300),
    ( 480, 300),
    ( 480, 650),
    ( 780, 650),
    (1010, 650)
)

END_TICK_X = 805

DAYS_X = (
    60,
    200,
    340,
    480,
    620,
    750,
    900,
    1040
)

DAYS_Y = (
    210, 
    290,
    370,
    450,
    530
)

CONTINUE_BUTTON   = (570, 430)
EZIC_MESSAGE_OPEN = (745, 380)

WANTED = (
    (1050, 370),
    (1050, 470),
    (1050, 570)
)

TRANQ_GUN_ENABLE_KEY_POS = (1090, 370)
SNIPER_ENABLE_KEYPOS     = (1090, 495)
ATTACKER_GRENADE_DETECT_ZONE = (630, 85, 670, 160)

ATTACKER_WALL_DETECT_ZONE     = (368, 61, 404, 100)
ATTACKER_DETONATE_DETECT_ZONE = (518, 61, 526, 160)

REASON_STAMP = (450, 350)
PASSPORT_REASON_POS = (450, 450)

LEFT_SCAN_SLOT  = (550, 450)
RIGHT_SCAN_SLOT = (980, 450)

CLOCK_POS = (30, 630)

SHUTTER_LEVER = (335, 270)
PASSPORT_CONFISCATE_POS = (470, 665)

PERSON_AREA = (8, 237, 363, 445)
DRAG_TO_WITH_GIVE_AMPLITUDE = (
    PERSON_AREA[2] - PERSON_POS[0] - 100,
    PERSON_AREA[3] - PERSON_POS[1] - 50
)

PEOPLE_COLOR       = ( 27,  27,   27)
CIVILIANS_AREA     = ( 16,  31,  236, 236)
GUARDS_AREA        = (600,  61,  940, 236)
DAY_26_NDBIKE_AREA = (745, 115, 1146, 205)

CLOSE_BUTTON_OFFSET = (1094, 51)
WINDOW_SIZE = (1156, 680)