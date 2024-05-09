from dateutil.relativedelta import relativedelta
from enum import Enum

WINDOW_TITLES = ("Papers Please", "PapersPlease")
PROCESS_NAME  = "PapersPlease.exe"

DRAG_TO_WITH_GIVE_THETA_INC = (0.75, 0.5)
DRAG_TO_WITH_GIVE_POS_OFFS  = (0, 20)

TEXT_RECOGNITION_TOLERANCE = 4

PASSPORT_TEXT_COLOR = ( 87,  72,  72) 
OBRISTAN_TEXT_COLOR = (237, 224, 216)

TRANSCRIPTION_BG_COLOR   = (210, 237, 236)
TRANSCRIPTION_TEXT_COLOR = PASSPORT_TEXT_COLOR

UPPERCASE_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWERCASE_LETTERS = "abcdefghijklmnopqrstuvwxyz"
DIGITS            = "0123456789"

# space is first cause end of text will be full of spaces, we want to recognize them first
# lowercase characters are next because they're the most common character
# uppercase characters show up like twice
PASSPORT_NAME_CHARS = " " + LOWERCASE_LETTERS + UPPERCASE_LETTERS + ",-'" # commas show up once in passport names, dashes and apostrophes show up rarely
PASSPORT_CITY_CHARS = " " + LOWERCASE_LETTERS + UPPERCASE_LETTERS + "."   # dots show up once at most in cities
PASSPORT_NUM_CHARS  = " " + UPPERCASE_LETTERS + DIGITS + "-"
DATE_CHARS          = DIGITS + "."

PERMIT_PASS_CHARS      = " " + UPPERCASE_LETTERS # in permits and passes, everything is caps
WORK_PASS_FIELD_CHARS  = PERMIT_PASS_CHARS + "-"
PERMIT_PASS_NAME_CHARS = WORK_PASS_FIELD_CHARS + "'"
DISEASE_CHARS          = WORK_PASS_FIELD_CHARS + "."
PERMIT_PASS_CHARS_NUM  = PERMIT_PASS_CHARS + DIGITS

ID_LAST_NAME_CHARS = PERMIT_PASS_CHARS + ",-'"

DIPLOMATIC_AUTH_ACCESS_TO_CHARS = PERMIT_PASS_CHARS + ","

HEIGHT_CHARS = DIGITS + "cm"
WEIGHT_CHARS = DIGITS + "kg"

TRANSCRIPTION_CHARS = PASSPORT_CITY_CHARS + DIGITS + "'?!"

class Sex(Enum):
    # as much as i don't like this, the game has two of these :c
    # so i'm using booleans cause cleaner/faster code
    M, F = False, True 

class TASException(Exception): ...

PERMIT_DURATIONS = {
    "VALID"   : relativedelta(years  = 4), # }
    "UNKNOWN" : relativedelta(years  = 3), # }- just for comparison purposes
    "FOREVER" : relativedelta(years  = 2), # } 
    "2 DAYS"  : relativedelta(days   = 2),
    "14 DAYS" : relativedelta(weeks  = 2),
    "1 MONTH" : relativedelta(months = 1),
    "2 MONTHS": relativedelta(months = 2),
    "3 MONTHS": relativedelta(months = 3),
    "6 MONTHS": relativedelta(months = 6),
    "1 YEAR"  : relativedelta(years  = 1)
}

RANDOM_STAY = ("I stay", "I remain for", "It will be")
I_DONT_PLAN_TO_LEAVE = "I don't plan to leave."
ASK_PURPOSE  = "What is the purpose of your trip?"
ASK_DURATION = "Duration of stay?" 

STAY_DURATIONS = {
    **dict.fromkeys((
        "forever.", "until I die."
    ), PERMIT_DURATIONS["FOREVER"]),
    **dict.fromkeys((
        "just 2 days.", "couple days."
    ), PERMIT_DURATIONS["2 DAYS"]),
    **dict.fromkeys((
        "just 14 days.", "couple weeks.", "only two weeks."
    ), PERMIT_DURATIONS["14 DAYS"]),
    **dict.fromkeys((
        "30 days.", "a few weeks.", "one month."
    ), PERMIT_DURATIONS["1 MONTH"]),
    **dict.fromkeys((
        "60 days.", "8 weeks.", "couple months.", "two months."
    ), PERMIT_DURATIONS["2 MONTHS"]),
    **dict.fromkeys((
        "90 days.", "12 weeks.", "three months.", "a few months."
    ), PERMIT_DURATIONS["3 MONTHS"]),
    **dict.fromkeys((
        "six months.", "half a year."
    ), PERMIT_DURATIONS["6 MONTHS"]),
    **dict.fromkeys((
        "one year.", "full year.", "a year."
    ), PERMIT_DURATIONS["1 YEAR"])
}

class Purpose(Enum):
    TRANSIT, VISIT, WORK, IMMIGRATION, DIPLOMAT, ASYLUM, UNKNOWN = (
        "TRANSIT", "VISIT", "WORK", "IMMIGRATE", "DIPLOMAT", "ASYLUM", ""
    )

PURPOSES = {
    **dict.fromkeys((
        "Visiting.", "Just visiting.", "I am visiting relatives.", "Visiting friends.", 
        "I come for visit.", "Only to visit.", "I will visit friends."
    ), Purpose.VISIT),
    **dict.fromkeys((
        "Transit.", "I pass through.", "Transit through the country.", 
        "I am transiting to elsewhere.", "Transit through Arstotzka.",
        "Passing through.", "I am in transit."
    ), Purpose.TRANSIT),
    **dict.fromkeys((
        "Work.", "I come to work.", "I have job here.", "I plan to work."
    ), Purpose.WORK),
    **dict.fromkeys((
        "Immigrating.", "I am immigrating to Arstotzka.", "I will move here.",
        "I am coming to live with my wife.", "I am coming to live with my husband.",
        "I am immigrating to Arstotzka"
    ), Purpose.IMMIGRATION),
    **dict.fromkeys((
        "I am diplomatic envoy.", "I was called to diplomatic discussions.",
        "My presence was requested."
    ), Purpose.DIPLOMAT),
    **dict.fromkeys((
        "Asylum.", "I am seeking asylum.", "I come for political asylum."
    ), Purpose.ASYLUM)
}

ASK_MISSING_DOC = {
    **dict.fromkeys((
        "Where is the entry permit?", "You have no entry permit.", 
        "The entry permit is missing.",
        # from scripted entrants:
        "You are missing an entry permit.", "An entry permit is required.",
        "Tickets are no longer accepted.", "Where is your entry permit?",
        "You do not have the required documentation.",
        "You are missing required papers.", "Your press pass is worthless for entry.",
        "This pass means nothing.", "You are missing some papers.", 
        "Where is entry permit?", "Your papers are missing.",
        "You do not have the right documents.", "Ticket is not enough any more."
    ), "EntryPermit"),
    **dict.fromkeys((
        "Where is the work pass?", "You have no work pass.", 
        "The work pass is missing."
    ), "WorkPass"),
    **dict.fromkeys((
        "Where is your id card?", "I need your id card.",
        # from scripted entrants:
        "Your Arstotzkan id card is missing."
    ), "ArstotzkanID"),
    **dict.fromkeys((
        "You must carry an id supplement.", "Where is your id supplement?"
    ), "IDSupplement"),
    **dict.fromkeys((
        "You have no grant for asylum.", "Where is your asylum grant?"
    ), "GrantOfAsylum"),
    **dict.fromkeys((
        "Where is the access permit?", "You have no access permit.", 
        "The access permit is missing.",
        # from scripted entrants:
        "Entry permit and supplement are no longer accepted."
    ), "AccessPermit"),
    **dict.fromkeys((
        "You cannot enter without a ticket.", "Foreigners must present an entry ticket.", 
        "Where is your entry ticket?"
    ), "EntryTicket"),
    **dict.fromkeys((
        "Where is the vaccine certification?", "Where is your proof of vaccination?", 
        "All entrants must be vaccinated."
    ), "VaxCert"),
}

MISSING_DOC_GIVEN = set((
    "Here it is.", "Sorry. I have it here.", "I have it here.", "Here."
))

DETAIN_PHRASES = set((
    "There is no record of this name.", "I cannot verify your alias.",
    "I cannot verify your identity.", "Your identity does not match.",
    "Your fingerprints do not match our records.", "I cannot verify your fingerprints.",
    "Your thumb print does not match.", "This print does not match.",
    "This document is missing its seal.", "There is no seal here.",
    "I do not see the required seal here.", "This document is forged.",
    "This is a forgery.", "This seal is forged.", "This seal is not correct.",
    "This grant is not sealed properly.", "There is zero tolerance for contraband.",
    "You have made a mistake coming here.", "You have interesting face.",
    "Maybe you should not have come.", "We have some questions for you.",
    "This issuing city is incorrect.", "Your passport has false information.",
    "There is a problem with your documentation.", "This card contains false information.",
    "These dates do not match.", "These numbers do not match.", "There is a discrepancy here.",
    "There are two different numbers here.", "Your diplomatic authorization does not cover Arstotzka.",
    "You have no diplomatic rights here.", "This authorization does not include Arstotzka.",
    # from scripted entrants:
    "Your face is in wanted bulletin.", "You are Dari Ludum?", "You are Vince Lestrade?",
    "Can I have note back now?", "Funny to see you here.", "Just when starting to look for criminals."
))

FINGERPRINT_PHRASES = set((
    "These names do not match.", "This does not look like you.", "Your picture. It is different.",
    "Your appearance has changed.", "Your height is different.", "This information does not look correct.",
    "This is incorrect.", "This does not sound like you.", "You do not match this description."
))

SEARCH_PHRASES = set((
    "You are a man?", "It says here that you are male.", "You are a woman?", 
    "Your passport says you are female.", "Are you a woman or a man?", "You are male or female?",
    "You have been selected for a random search.", 
    # from scripted entrants:
    "Your weight is different.", "I see a difference here."
))

OTHER_DISCREPANCY_PHRASES = set((
    "You cannot enter using an expired document.", "No entry from Obristan.", "No entry from Kolechia.",
    "No entry from United Federation.", "No entry from Antegria.", "No entry from Republia.",
    "No entry from Arstotzka.", "No entry from Impor.", "This ticket is for another day.", 
    "You cannot enter today.", "The date on this ticket is wrong.", 
    "You are not authorized to work this long.", "This work pass expires before your visit.", 
    "This vaccine has expired.", "This vaccine is no longer active.",
    "You are missing the required vaccination.", "This vaccine certificate is insufficient."
)
# these ones are currently here because we don't support fingerprinting or searching.
# should be removed in the future if those actions get supported
) | FINGERPRINT_PHRASES | SEARCH_PHRASES 

NO_PURPOSE_SCRIPTED_ENTRANT_PHRASES = {
    **dict.fromkeys((
        "Old friend hello!", "Hey it is me!", "Hello my guy!", "Again I am here!",
        "Ok, I am back!", "Is good to see you again!", "I read newspaper."
    ), (Purpose.TRANSIT, PERMIT_DURATIONS["VALID"])),
    "Today is beautiful day, my friend.": (Purpose.IMMIGRATION, PERMIT_DURATIONS["FOREVER"]),
    "Did you see my husband?": (Purpose.UNKNOWN, PERMIT_DURATIONS["UNKNOWN"]),
    "Do you know Sergiu?": (Purpose.UNKNOWN, PERMIT_DURATIONS["UNKNOWN"]),
    "I write report on conditions in Arstotzka.": (Purpose.UNKNOWN, PERMIT_DURATIONS["UNKNOWN"]),
    "I cover big story.": (Purpose.UNKNOWN, PERMIT_DURATIONS["UNKNOWN"]),
    "I have only passport but hear me out.": (Purpose.UNKNOWN, PERMIT_DURATIONS["UNKNOWN"]),
    "As promised, I am back with right papers now.": (Purpose.VISIT, PERMIT_DURATIONS["VALID"]),
    "Red stamp.": (Purpose.WORK, PERMIT_DURATIONS["VALID"]),
    "I come for medical reasons.": (Purpose.UNKNOWN, PERMIT_DURATIONS["UNKNOWN"]),
    "I will leave this here.": (Purpose.UNKNOWN, PERMIT_DURATIONS["UNKNOWN"]),
    "What? I do not know. To visit?": (Purpose.VISIT, PERMIT_DURATIONS["2 DAYS"]),
    "I am so happy that the border has opened.": (Purpose.VISIT, PERMIT_DURATIONS["6 MONTHS"]),
    "It is not my choice. I hate this damn country.": (Purpose.TRANSIT, PERMIT_DURATIONS["2 DAYS"]),
    "I have heard the border will close.": (Purpose.UNKNOWN, PERMIT_DURATIONS["UNKNOWN"]),
}

class Description(Enum): 
    (
        SHORT_HAIR, GOOD_VISION, BALDING, GLASSES, LARGE_MUSTACHE,
        BALD, LARGE_CURLY_LOCKS, CROPPED_HAIR, OVERWEIGHT, NO_GLASSES,
        DARK_HAIR, MUSTACHE, SHAVED_HEAD, GOATEE, PERFECT_VISION, MOHAWK,
        SHORT_CROPPED_HAIR, LONG_WAVY_HAIR, HUGE_AFRO, THICK_GLASSES,
        CURLY_HAIR, SHORT_STRAIGHT_HAIR, SHORT_LIGHT_HAIR, WIDOWS_PEAK,
        CLEAN_SHAVEN, TALL_FOREHEAD, TOTALLY_BALD, KILLER_SIDEBURNS,
        LIGHT_HAIR, BOBBED_HAIR, LONG_CURLY_HAIR, SHORT_CURLY_HAIR,
        LARGE_SIDEBURNS, FLAT_TOP_HAIR, PENCIL_MUSTACHE, UNKEMPT_CURLY_HAIR,
        LONG_STRAIGHT_HAIR, WAVY_HAIR, SMALL_HEAD, AFRO, SLIM_FIGURE,
        VERY_SHORT_HAIR, CURLY_BOBBED_HAIR, SHORT_WAVY_HAIR, LONG_HAIR,
        STRAIGHT_HAIR, ROUND_FACE, BEARD
    ) = (
        "SHORT HAIR", "GOOD VISION", "BALDING", "GLASSES", "LARGE MUSTACHE",
        "BALD", "LARGE CURLY LOCKS", "CROPPED HAIR", "OVERWEIGHT", "NO GLASSES",
        "DARK HAIR", "MUSTACHE", "SHAVED HEAD", "GOATEE", "PERFECT VISION", "MOHAWK",
        "SHORT CROPPED HAIR", "LONG WAVY HAIR", "HUGE AFRO", "THICK GLASSES", 
        "CURLY HAIR", "SHORT STRAIGHT HAIR", "SHORT LIGHT HAIR", "WIDOW'S PEAK",
        "CLEAN SHAVEN", "TALL FOREHEAD", "TOTALLY BALD", "KILLER SIDEBURNS",
        "LIGHT HAIR", "BOBBED HAIR", "LONG CURLY HAIR", "SHORT CURLY HAIR",
        "LARGE SIDEBURNS", "FLAT-TOP HAIR", "PENCIL MUSTACHE", "UNKEMPT CURLY HAIR",
        "LONG STRAIGHT HAIR", "WAVY HAIR", "SMALL HEAD", "AFRO", "SLIM FIGURE",
        "VERY SHORT HAIR", "CURLY BOBBED HAIR", "SHORT WAVY HAIR", "LONG HAIR",
        "STRAIGHT HAIR", "ROUND FACE", "BEARD"
    )