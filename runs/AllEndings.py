from tas      import Run
from enum     import Enum
import time, numpy as np

from modules.constants.screen import *
from modules.constants.delays import *
from modules.utils            import *

class Day23Mode(Enum):
    DEFAULT, TRANQ_RED, KILL_RED = range(3)

class Day28Mode(Enum):
    KILL_CIVILIAN, TRANQ_CIVILIAN, KILL_GUARD, TRANQ_GUARD, DEFAULT = range(5)

class Day31ShootMode(Enum):
    NO, YES, SAVE_WALL = range(3)

class Day31EscapeMode(Enum):
    NO, ALONE, WIFE = range(3)

class AllEndings(Run):
    def credits(self):
        return "** All Endings speedrun **\nStrategy: HowToCantaloupe\nCode: thatsOven"

    DAY_12 = date(1982, 12,  4) 
    DAY_23 = date(1982, 12, 15) 
    DAY_30 = date(1982, 12, 22)
    DAY_31 = date(1982, 12, 23) 

    def day1(self):
        self.tas.daySetup()

        # process exactly 12 entrants
        self.tas.passportOnlyAllow()
        self.tas.passportOnlyDeny()
        self.tas.passportOnlyDeny()

        self.tas.day1Check()

        # "it was a mistake to open this checkpoint"
        self.tas.nextPartial() 
        time.sleep(4)

        for _ in range(7):
            self.tas.day1Check()

        self.tas.waitForSleepButton()

        # deny food and heat
        self.tas.waitForAllTicks()
        self.tas.clickOnTick("food")
        self.tas.clickOnTick("heat")
        
        self.tas.dayEnd()

    def day2(self, *, ending1):
        self.tas.daySetup()

        if ending1:
            self.tas.passportOnlyDeny()
            self.tas.passportOnlyAllow()
            self.tas.day2Check(wrong = True)
            self.tas.passportOnlyDeny()
            self.tas.day2Check(wrong = True)
        else:
            self.tas.passportOnlyAllow()
            self.tas.passportOnlyDeny()
            self.tas.passportOnlyDeny()
            self.tas.passportOnlyAllow()
            self.tas.passportOnlyDeny()

        self.tas.passportOnlyDeny() 

        # process last person and wait
        self.tas.checkHorn = True
        self.tas.day2Check(wrong = ending1)
        self.tas.waitForSleepButton()
        
        if not ending1:
            self.tas.waitForAllTicks()
            self.tas.clickOnTick("food")
            self.tas.clickOnTick("heat")
            self.tas.clickOnTick("medicineSon")
        
        self.tas.dayEnd()

    def day3(self):
        self.tas.daySetup()

        self.tas.multiDocAction(True)
        self.tas.passportOnlyDeny()
        self.tas.multiDocAction(True)
        self.tas.day3Check()
        self.tas.multiDocAction(True)
        self.tas.multiDocAction(False)
        self.tas.day3Check()

        # jorji with no passport
        self.tas.nextPartial()
        time.sleep(4)
        self.tas.noPassport(backToIndex = False)

        self.tas.day3Check()

        self.tas.checkHorn = True
        while self.tas.day3Check(): pass

        # deny food, heat, and medicines, except for wife
        self.tas.waitForAllTicks()
        self.tas.clickOnTick("food")
        self.tas.clickOnTick("heat")
        self.tas.clickOnTick("medicineMIL")
        self.tas.clickOnTick("medicineSon")

        self.tas.dayEnd()

    def day4(self):
        self.tas.daySetup()

        self.tas.multiDocAction(True)
        for _ in range(3):
            self.tas.day4Check()
            self.tas.multiDocAction(False)
        
        # jorji with fake passport, allow so he doesn't come back later
        self.tas.passportOnlyAllow() 

        self.tas.day4Check()

        self.tas.checkHorn = True
        while self.tas.day4Check(): pass

        # deny food, heat, and medicines, except for wife
        self.tas.waitForAllTicks()
        self.tas.clickOnTick("food")
        self.tas.clickOnTick("heat")
        self.tas.clickOnTick("medicineMIL")
        self.tas.clickOnTick("medicineUncle")

        self.tas.dayEnd()

    def day5(self):
        self.tas.daySetup()

        self.tas.multiDocAction(False)
        self.tas.day4Check()
        self.tas.multiDocAction(True)
        self.tas.day4Check()
        self.tas.multiDocAction(True)
        self.tas.day4Check()
        self.tas.day4Check()
        self.tas.multiDocAction(True)
        self.tas.passportOnlyDeny()

        self.tas.checkHorn = True
        while self.tas.day4Check(): pass

        self.tas.waitForAllTicks()
        self.tas.clickOnTick("upgradeBooth")

        self.tas.dayEnd()

    def day6(self):
        self.tas.daySetup()

        self.tas.multiDocAction(True)
        self.tas.multiDocAction(True)
        for _ in range(4):
            self.tas.multiDocAction(False)
        self.tas.multiDocAction(True)
        self.tas.multiDocAction(False)
        self.tas.multiDocAction(True) # attack

        self.tas.checkHorn = True
        self.tas.day6Check() # last check before attack for money
        
        self.tas.waitForSleepButton()
        self.tas.dayEnd()

    def day7(self):
        self.tas.daySetup()

        for _ in range(3):
            self.tas.multiDocAction(False)
            self.tas.day6Check()
            self.tas.day6Check()

        self.tas.checkHorn = True
        while self.tas.day6Check(): pass

        self.tas.dayEnd()

    def day8(self):
        self.tas.daySetup()

        self.tas.multiDocAction(True)
        for _ in range(3):
            self.tas.day8Check()

        self.tas.next() # ezic person (gives note)

        for _ in range(3):
            self.tas.day8Check()
            
        self.tas.multiDocAction(True)

        self.tas.checkHorn = True
        while self.tas.day8Check(): pass

        self.tas.dayEnd()

    def setupFastChecks(self):
        self.tas.doConfiscate     = False
        self.tas.allowWrongWeight = True
        self.tas.newData          = False

    def day9(self):
        self.tas.daySetup()
        self.tas.prepareItem(SLOTS[2]) # prepare ezic paper

        # calensk
        self.tas.nextPartial()
        self.tas.weight = 0 # not None so the next check doesn't trip
        time.sleep(4)

        self.tas.multiDocAction(False)
        self.tas.multiDocAction(False)
            
        # agent (gives real and fake documents)
        self.tas.nextPartial()
        for i in range(2):
            while np.array_equal(self.tas.lastGiveArea, np.asarray(self.tas.getScreen().crop(GIVE_AREA))): pass
            time.sleep(0.25)
            self.tas.moveTo(PAPER_POS)
            self.tas.dragTo(SLOTS[-2 - i])

        self.tas.multiDocAction(False)
        self.tas.multiDocAction(False)

        # imposter (we give them fake documents)
        self.tas.next()
        self.tas.moveTo(SLOTS[-3])
        self.tas.dragToWithGive(PERSON_POS)

        self.tas.multiDocAction(False)
        
        # corman drex
        self.tas.next()
        tmp = self.tas.lastGiveArea 
        self.tas.moveTo(SLOTS[-1])
        self.tas.dragTo(PERSON_POS) # give them ezic paper
        self.tas.waitForGiveAreaChange() # wait for them to give message
        self.tas.ezicMessenger(nextCheck = False) # "read" it and give it back
        self.tas.waitForGiveAreaChange() # wait for them to give paper
        self.tas.prepareItem(PAPER_POS) # move to temp slot
        # process their papers
        self.tas.lastGiveArea = tmp
        self.tas.multiDocAction(True, nextCheck = False) 

        self.tas.checkHorn = True
        self.setupFastChecks()
        while self.tas.day8Check(): pass

        self.tas.dayEnd()

    def day10(self):
        self.tas.daySetup()

        # supervisor (just wait, basically)
        self.tas.waitForGiveAreaChange(sleep = False)
        self.tas.waitForDoorChange()

        self.tas.day8Check()
        self.tas.day8Check()

        # this is actually scripted to be wrong,
        # but letting them through saves time with calensk later on
        self.tas.multiDocAction(True, force = True) 

        self.tas.day8Check()
        self.tas.day8Check()

        # ezic (again, just wait)
        self.tas.next()

        self.tas.day8Check()
        self.tas.day8Check()

        self.tas.checkHorn = True
        while self.tas.day8Check(): pass

        self.tas.dayEnd()

    def day11(self):
        self.tas.daySetup()

        self.tas.multiDocAction(False)
        self.tas.multiDocAction(False)
        self.tas.multiDocAction(False)

        # calensk (just wait)
        self.tas.nextPartial()
        time.sleep(4)
        
        self.tas.multiDocAction(False)
        self.tas.passportOnlyDeny() # ezic
        self.tas.multiDocAction(False)
        self.tas.multiDocAction(False)
        self.tas.ezicMessenger()

        self.tas.checkHorn = True
        self.setupFastChecks()
        while self.tas.day8Check(): pass

        self.tas.waitForAllTicks()
        self.tas.clickOnTick("ezicGift") # burn money
        self.tas.clickOnTick("upgradeBooth")

        self.tas.dayEnd()

    def day12(self, *, ending3, burn):
        self.tas.daySetup()

        # vonel asks about ezic
        self.tas.lastGiveArea = np.asarray(self.tas.getScreen().crop(GIVE_AREA))
        for _ in range(2):
            self.tas.waitForGiveAreaChange(update = False)
            self.tas.moveTo(PAPER_POS)
            self.tas.dragTo(PAPER_SCAN_POS)

        # give vonel ezic thingy and wait
        if ending3:
            self.tas.moveTo(SLOTS[2])
            self.tas.dragTo(CLEANUP_POS)

            self.tas.moveTo(SLOTS[2])
            before = np.asarray(self.tas.getScreen().crop(GIVE_AREA))
            self.tas.dragTo(PAPER_POS)
            self.tas.giveAllGiveAreaDocs(before, delay = True)

            self.tas.waitForGiveAreaChange(sleep = False)
            return
        
        # give vonel back badge and drawing
        before = np.asarray(self.tas.getScreen().crop(GIVE_AREA))
        self.tas.dragTo(PAPER_POS)
        self.tas.moveTo(PAPER_SCAN_POS)
        self.tas.dragTo(PAPER_POS)
        self.tas.giveAllGiveAreaDocs(before)
        self.tas.waitForDoorChange()

        self.tas.multiDocAction(False)
        self.tas.multiDocAction(False)
        self.tas.multiDocAction(True)
        for _ in range(3):
            self.tas.multiDocAction(False)
        self.tas.multiDocAction(True)
        self.tas.multiDocAction(True) # attack

        self.tas.checkHorn = True
        self.tas.day8Check() # last check before attack for money

        self.tas.waitForSleepButton()

        if burn:
            self.tas.waitForAllTicks()
            self.tas.clickOnTick("food")
            self.tas.clickOnTick("heat")
            if burn: self.tas.clickOnTick("ezicGift")

        self.tas.dayEnd()

    def day13(self, *, safe):
        self.tas.daySetup()

        for _ in range(2):
            if safe: self.tas.day13Check()
            else:    self.tas.multiDocAction(False)

        # calensk (just wait)
        self.tas.nextPartial()
        time.sleep(4)

        for _ in range(2):
            if safe: self.tas.day13Check()
            else:    self.tas.multiDocAction(False)

        self.tas.passportOnlyDeny() # filipe hasse

        self.tas.multiDocAction(True)
        if safe: self.tas.day13Check()
        else:    self.tas.multiDocAction(False)

        self.setupFastChecks()
        self.tas.day13Check()

        self.tas.checkHorn = True
        while self.tas.day13Check(): pass

        self.tas.dayEnd()

    def day14(self, *, messenger, ezic, safe):
        self.tas.daySetup()

        self.tas.knownCriminal(self.tas.day13Check)

        if safe: self.tas.day13Check()
        else:    self.tas.multiDocAction(False)

        if messenger: self.tas.ezicMessenger()
        elif safe:    self.tas.day13Check()
        else:         self.tas.multiDocAction(False)
            
        if safe: 
            self.tas.day13Check()
            self.tas.day13Check()
        else:    
            self.tas.multiDocAction(True)
            self.tas.multiDocAction(False)
            
        self.tas.knownCriminal(self.tas.day13Check)

        # person with two passports
        self.tas.next()
        self.tas.prepareItem(PAPER_POS) # put first passport on the side
        self.tas.passportOnlyDeny(nextCheck = False) # stamp second passport and give
        self.tas.giveAllGiveAreaDocs(self.tas.lastGiveArea) # give id card back

        if safe: self.tas.day13Check()
        else:    self.tas.multiDocAction(False)

        self.tas.multiDocAction(ezic, force = True) # ezic agent

        self.tas.checkHorn = True
        self.setupFastChecks()
        while self.tas.day13Check(): pass

        self.tas.dayEnd()

    def day15(self, *, ending4):
        self.tas.daySetup()
        if ending4: return

        self.tas.multiDocAction(False)
        self.tas.day15Bomb()
        self.tas.multiDocAction(False)
        self.tas.multiDocAction(True)
        self.tas.multiDocAction(False)

        # ezic
        self.tas.nextPartial()
        self.tas.lastGiveArea = np.asarray(self.tas.getScreen().crop(GIVE_AREA))
        # give them coded papers
        for _ in range(2):
            self.tas.moveTo((510, 375)) 
            self.tas.dragTo(PAPER_POS)
        self.tas.giveAllGiveAreaDocs(self.tas.lastGiveArea)
        # wait for message
        self.tas.waitForGiveAreaChange()
        # "read" it and give it back
        self.tas.ezicMessenger(nextCheck = False)

        self.tas.multiDocAction(False)
        self.tas.multiDocAction(False)

        self.tas.checkHorn = True
        self.setupFastChecks()
        while self.tas.day13Check(): pass

        self.tas.dayEnd()

    def day16(self):
        self.tas.daySetup()
        self.tas.prepareItem((395, 355)) # tranq gun initial position on this day

        # calensk (just wait)
        self.tas.nextPartial()
        self.tas.weight = 0 # not None so the next check doesn't trip
        time.sleep(4)

        self.tas.multiDocAction(False)
        self.tas.multiDocAction(False)
        self.tas.passportOnlyAllow() # person with bribe
        self.tas.multiDocAction(False)
        self.tas.multiDocAction(True)
        self.tas.multiDocAction(False)

        # attack
        self.tas.next()
        self.tas.getTranqGun()
        self.tas.click((380, 115))
        self.tas.click((385, 115))

        self.tas.waitForSleepButton()

        self.tas.dayEnd()

    def day17(self, *, ezic):
        self.tas.daySetup()

        # sergiu (just wait)
        self.tas.nextPartial()
        self.tas.weight = 0 # not None so the next check doesn't trip
        time.sleep(4)

        self.tas.day13Check()
        self.tas.ezicMessenger()

        for _ in range(3):
            self.tas.day13Check()

        self.tas.multiDocAction(True) # journalist 
        self.tas.day13Check()
        
        if ezic: self.tas.passportOnlyAllow()
        else:    self.tas.passportOnlyDeny()

        self.tas.checkHorn = True
        while self.tas.day13Check(): pass

        self.tas.dayEnd()

    def day18(self):
        self.tas.daySetup()
        self.tas.prepareItem((395, 275)) # tranq gun initial position on this day

        for _ in range(7):
            # forced cause denying has longer dialogue
            self.tas.multiDocAction(True, force = True) 

        # attack
        self.tas.next()
        self.tas.getTranqGun()
        # wait for them to throw grenade (poor sergiu :c)
        self.tas.waitForAreaChange(ATTACKER_GRENADE_DETECT_ZONE)
        time.sleep(2) 
        self.tas.click(centerOf(ATTACKER_GRENADE_DETECT_ZONE)) # shoot

        self.tas.waitForSleepButton()

        self.tas.dayEnd()

    def day19(self):
        self.tas.daySetup()

        self.tas.day18Check()
        self.tas.noPictureCheck(self.tas.day18Check)
        self.tas.day18Check()
        self.tas.multiDocAction(True)
        for _ in range(3):
            self.tas.day18Check()
        self.tas.noPictureCheck(self.tas.day18Check)
        self.tas.day18Check()

        self.tas.checkHorn = True
        while self.tas.day18Check(): pass

        self.tas.dayEnd()

    def day20(self, *, banner, poison4):
        self.tas.daySetup()

        if banner:
            # put arskickers pennant on wall
            self.tas.click(SHUTTER_LEVER)
            time.sleep(SHUTTER_OPEN_TIME)
            self.tas.moveTo((550, 260))
            self.tas.dragTo(PERSON_POS)

        # supervisor (just wait, basically)
        self.tas.waitForGiveAreaChange(sleep = False)
        self.tas.waitForDoorChange()

        self.tas.multiDocAction(True)

        # ezic with poison
        self.tas.ezicMessenger()
        self.tas.waitForGiveAreaChange()
        self.tas.prepareItem(PAPER_POS)

        if not poison4:
            for _ in range(5):
                self.tas.multiDocAction(True)
            
        # give poison
        self.tas.poison = True
        self.tas.multiDocAction(False) # this leads to a citation but the cutscene is shorter

        self.tas.waitForSleepButton()

        self.tas.dayEnd()

    def day21(self):
        self.tas.daySetup()
        self.tas.prepareItem((395, 280)) # tranq gun initial position on this day

        for _ in range(3):
            self.tas.multiDocAction(True)

        self.tas.multiDocAction(False) # red stamp person (gives 10 credits - 5 for citation, whatever it's good)
        self.tas.multiDocAction(True)

        # watch person
        self.tas.skipGive = True
        self.tas.passportOnlyDeny()
        tmp = self.tas.lastGiveArea
        time.sleep(1)
        for i in range(2):
            self.tas.waitForGiveAreaChange()
            self.tas.moveTo(PAPER_POS)
            self.tas.dragTo(SLOTS[-1 - i])
        self.tas.giveAllGiveAreaDocs(tmp, delay = True)
        # give watch back
        self.tas.moveTo(SLOTS[-1])
        self.tas.dragToWithGive(PERSON_POS)

        self.tas.multiDocAction(True)

        # attack
        self.tas.next()
        self.tas.getTranqGun()

        for pos in self.tas.detectPeople(GUARDS_AREA, tranq = True):
            self.tas.click(offsetPoint(pos, (-5, 0)))

        self.tas.waitForSleepButton()        
        self.tas.dayEnd()

    def day22(self, *, pennantOnWall):
        self.tas.daySetup()

        # prepare pennant
        if pennantOnWall:
            self.tas.prepareItem(PERSON_POS) 
        else:
            self.tas.prepareItem((530, 265))

        for _ in range(3):
            self.tas.multiDocAction(True)

        # filipe hasse
        self.tas.next()
        self.tas.moveTo(PAPER_POS)
        self.tas.dragTo(PASSPORT_ALLOW_POS)
        # wait for dialogue
        tmp = self.tas.lastGiveArea
        self.tas.waitForGiveAreaChange()
        # take money 
        self.tas.moveTo(PAPER_POS)
        self.tas.dragTo(SLOTS[-2])
        # allow and give them pennant and id card
        self.tas.allowAndGive()
        self.tas.moveTo(SLOTS[-1])
        self.tas.dragTo(PERSON_POS)
        self.tas.giveAllGiveAreaDocs(tmp)

        for _ in range(5):
            self.tas.multiDocAction(True)

        self.tas.checkHorn = True
        self.setupFastChecks()
        while self.tas.day21Check(): pass

        self.tas.dayEnd()
    
    def day23(self, *, mode: Day23Mode):
        self.tas.daySetup()

        if mode != Day23Mode.KILL_RED:
            self.tas.prepareItem((395, 255)) # tranq gun initial position on this day

        self.tas.multiDocAction(True)
        self.tas.ezicMessenger()
        if mode == Day23Mode.KILL_RED:
            self.tas.waitForGiveAreaChange() # ezic gives sniper key
            self.tas.prepareItem(PAPER_POS)

        for _ in range(5):
            self.tas.multiDocAction(True)

        # attack
        self.tas.next()
        if mode == Day23Mode.KILL_RED:
            self.tas.getSniper()
            self.tas.click((395, 115)) # shoot attacker
        else: 
            self.tas.getTranqGun()
            time.sleep(0.25)
            self.tas.click((385, 115)) # shoot attacker

        if mode == Day23Mode.DEFAULT:
            self.tas.waitForSleepButton()
            self.tas.dayEnd()
        else:
            self.tas.click((148, 130)) # shoot red person

    def day24(self):
        self.tas.daySetup()

        for _ in range(3):
            self.tas.multiDocAction(True)

        self.tas.ezicMessenger()

        for _ in range(5):
            self.tas.multiDocAction(True)

        self.tas.checkHorn = True
        self.setupFastChecks()
        while self.tas.day21Check(): pass

        self.tas.dayEnd()

    def day25(self, *, shae, bills):
        self.tas.daySetup()

        for _ in range(4):
            self.tas.day21Check()

        self.tas.noPictureCheck(self.tas.day21Check) # love note person (there's extra delay so checking takes right time)

        for _ in range(3):
            self.tas.day21Check()

        # shae piersovska
        if shae: self.tas.multiDocAction(True)
        else:
            self.tas.detain = True    
            self.tas.noPictureCheck(self.tas.day21Check)

        self.tas.checkHorn = True
        while self.tas.day21Check(): pass

        if not bills:
            self.tas.waitForAllTicks()
            self.tas.clickOnTick("food")
            self.tas.clickOnTick("heat")
            self.tas.clickOnTick("upgradeBooth")

        self.tas.dayEnd()

    def day26(self, *, ending12, bills):
        self.tas.daySetup()
        if ending12: return

        self.tas.prepareItem((395, 275)) # tranq gun initial position on this day

        self.tas.multiDocAction(True)
        self.tas.multiDocAction(True)
        self.tas.passportOnlyDeny()

        for _ in range(4):
            self.tas.multiDocAction(True)

        # attack
        self.tas.next()
        self.tas.getTranqGun()
        # shoot attackers
        self.tas.click((470, 125))
        self.tas.click((705, 145))
        self.tas.click((620, 195))
        
        self.tas.waitForSleepButton()

        if not bills:
            self.tas.waitForAllTicks()
            self.tas.clickOnTick("food")
            self.tas.clickOnTick("heat")

        self.tas.dayEnd()

    def day27(self, *, ezic, bills):
        self.tas.daySetup()

        self.tas.day27Check()
        self.tas.day27Check()
        self.tas.ezicMessenger()
        for _ in range(3):
            self.tas.day27Check()

        self.tas.confiscate = ezic
        self.tas.multiDocAction(True)

        self.tas.day27Check()

        # ezic agent
        self.tas.nextPartial()
        if ezic:
            # open passport drawer
            self.tas.click(PASSPORT_CONFISCATE_POS)
            time.sleep(PASSPORT_DRAWER_OPEN_TIME)
            # give passport to ezic agent
            self.tas.moveTo(self.waitFor(AllEndings.TAS.PASSPORT_KORDON_KALLO))
            self.tas.dragToWithGive(PERSON_PASSPORT_POS)
            # wait for them to give it back
            self.tas.waitForGiveAreaChange(sleep = False) 
            # close drawer
            self.tas.click(PASSPORT_CONFISCATE_POS) 
            time.sleep(PASSPORT_DRAWER_CLOSE_TIME)
            # allow
            self.tas.passportOnlyAllow(nextCheck = False) 
        else:
            time.sleep(4)

        self.tas.checkHorn = True
        while self.tas.day27Check(): pass

        if not bills:
            self.tas.waitForAllTicks()
            self.tas.clickOnTick("food")
            self.tas.clickOnTick("heat")
            self.tas.clickOnTick("medicineWife")

        self.tas.dayEnd()

    def day28(self, *, mode, bills):
        self.tas.daySetup()

        sniper = mode in (Day28Mode.KILL_CIVILIAN, Day28Mode.KILL_GUARD)
        if sniper: self.tas.prepareItem((395, 255)) # sniper key initial position in this day
        else:      self.tas.prepareItem((395, 275)) # tranq gun key initial position in this day

        for _ in range(6):
            self.tas.multiDocAction(True)

        # attack
        self.tas.next()
        if sniper: self.tas.getSniper()
        else:      self.tas.getTranqGun()

        match mode:
            case Day28Mode.KILL_CIVILIAN:
                for pos in self.tas.detectPeople(CIVILIANS_AREA):
                    self.tas.click(pos)
            case Day28Mode.TRANQ_CIVILIAN:
                for pos in self.tas.detectPeople(CIVILIANS_AREA, tranq = True):
                    self.tas.click(pos)
            case Day28Mode.KILL_GUARD | Day28Mode.TRANQ_GUARD:
                self.tas.click((900, 123)) # shoot center guard
            case Day28Mode.DEFAULT:
                # shoot intruder
                self.tas.click((820, 190)) 
                self.tas.click((815, 190)) 
                self.tas.click((810, 190)) 

                self.tas.waitForSleepButton()

                if not bills:
                    self.tas.waitForAllTicks()
                    self.tas.clickOnTick("food")
                    self.tas.clickOnTick("heat")
                    self.tas.clickOnTick("medicineWife")

                self.tas.dayEnd()

    def day29(self, *, getObri):
        self.tas.daySetup()

        # vonel (just wait)
        self.tas.waitForDoorChange()

        self.tas.day27Check()
        
        # jorji
        self.tas.multiDocAction(True)
        # wait for him to give passport
        self.tas.waitForGiveAreaChange() 
        # give him back flier
        self.tas.moveTo(PAPER_POS)
        self.tas.dragToWithGive(PERSON_PASSPORT_POS) 
        # close drawer
        self.tas.click(PASSPORT_CONFISCATE_POS) 

        self.tas.day27Check()
        self.tas.day27Check()

        self.tas.confiscate = getObri
        self.tas.day27Check()

        self.tas.day27Check()

        # father (just wait)
        self.tas.next()
        time.sleep(4)

        self.tas.day27Check()

        self.tas.checkHorn = True
        while self.tas.day27Check(): pass

        self.tas.dayEnd()

    def day30(self, *, familyPic, givePhoto):
        self.tas.daySetup()

        if familyPic:
            # put family picture on wall
            self.tas.click(SHUTTER_LEVER)
            time.sleep(SHUTTER_OPEN_TIME)
            self.tas.moveTo((550, 270))
            self.tas.dragTo(PERSON_POS)
            return
        
        # supervisor (just wait)
        self.tas.waitForDoorChange()
        time.sleep(4)
        self.tas.waitForDoorChange()

        self.tas.day27Check()

        # simon wens
        if givePhoto:
            # give daughter picture
            self.tas.next()
            self.tas.moveTo((435, 400))
            self.tas.dragTo(PERSON_POS)

            self.tas.next()
            # close drawer
            self.tas.click(PASSPORT_CONFISCATE_POS) 
            time.sleep(PASSPORT_DRAWER_CLOSE_TIME)
            self.tas.day27Check(nextCheck = False)
        else: 
            self.tas.knownCriminal(self.tas.day27Check)
            self.tas.day27Check()

        self.tas.day27Check()
        self.tas.day27Check()

        # father
        self.tas.nextPartial()
        if givePhoto: time.sleep(4) # just wait
        else:
            # give picture back
            self.tas.moveTo((435, 400))
            self.tas.dragToWithGive(PERSON_POS)

        self.tas.day27Check()
        self.tas.day27Check()

        self.tas.checkHorn = True
        while self.tas.day27Check(): pass

        self.tas.dayEnd()

    def day31(self, *, shootMode, escapeMode, ezic):
        self.tas.daySetup()

        if shootMode != Day31ShootMode.NO:
            self.tas.prepareItem((395, 295)) # tranq gun key initial position in this day

        self.tas.multiDocAction(True)

        if ezic: self.tas.ezicMessenger()
        else:    self.tas.multiDocAction(True)

        self.tas.multiDocAction(True)
        self.tas.multiDocAction(True)
        self.tas.next() # jorji (just wait)
        self.tas.multiDocAction(True)
        self.tas.multiDocAction(True)

        # attack
        self.tas.next()
        if shootMode != Day31ShootMode.NO: 
            self.tas.getTranqGun()
            self.tas.click((685, 195)) # shoot bottom attacker

        match shootMode:
            case Day31ShootMode.SAVE_WALL:
                # shoot other attacker (two shots to be safe)
                self.tas.click((570, 95)) 
                self.tas.click((565, 95))
            case Day31ShootMode.YES:
                # shoot after wall is gone
                time.sleep(1)
                self.tas.waitForAreaChange(ATTACKER_WALL_DETECT_ZONE)     # wait for attacker to reach wall
                self.tas.waitForAreaChange(ATTACKER_DETONATE_DETECT_ZONE) # wait for attacker to go back and detonate
                time.sleep(3)
                self.tas.click(centerOf(ATTACKER_DETONATE_DETECT_ZONE))
        
        self.tas.waitForSleepButton()

        if escapeMode != Day31EscapeMode.NO:
            self.tas.waitForAllTicks()

            match escapeMode:
                case Day31EscapeMode.ALONE:
                    self.tas.clickOnTick("escapeSelf")
                case Day31EscapeMode.WIFE:
                    self.tas.clickOnTick("escapeSelfPlusOne")

        self.tas.dayEnd()

    def run(self):
        self.tas.newGame()
        self.day1()
        self.day2(ending1 = True)
        self.tas.ending1()

        self.tas.restartFrom((DAYS_X[1], DAYS_Y[0]), AllEndings.TAS.DAY_2)
        self.day2(ending1 = False)
        self.day3()
        self.day4()
        self.day5()
        self.day6()
        self.day7()
        self.day8()
        self.day9()
        self.day10()
        self.day11()
        self.day12(ending3 = True, burn = False)
        self.tas.ending3()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[0]), AllEndings.DAY_12)
        self.day12(ending3 = False, burn = False)
        self.day13(safe = True)
        self.day14(safe = True, messenger = True, ezic = False)
        self.day15(ending4 = True)
        self.tas.ending4()

        self.tas.restartFrom((DAYS_X[-4], DAYS_Y[0]), AllEndings.DAY_12)
        self.day12(ending3 = False, burn = True)
        self.day13(safe = False)
        self.day14(safe = False, messenger = False, ezic = True)
        self.day15(ending4 = False)
        self.day16()
        self.day17(ezic = True)
        self.day18()
        self.day19()
        self.day20(banner = True, poison4 = False)
        self.day21()
        self.day22(pennantOnWall = True)
        self.day23(mode = Day23Mode.KILL_RED)
        self.tas.ending9()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[1]), AllEndings.DAY_23) 
        self.day23(mode = Day23Mode.TRANQ_RED)
        self.tas.ending10()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[1]), AllEndings.DAY_23) 
        self.day23(mode = Day23Mode.DEFAULT)
        self.day24()
        self.day25(shae = False, bills = True)
        self.day26(ending12 = True, bills = True)
        self.tas.ending12()

        self.tas.restartFrom((DAYS_X[-2], DAYS_Y[1]), AllEndings.TAS.DAY_25)
        self.day25(shae = True, bills = False)
        self.day26(ending12 = False, bills = False)
        self.day27(ezic = True, bills = False)
        self.day28(mode = Day28Mode.KILL_CIVILIAN, bills = True)
        self.tas.ending5() 

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.TAS.DAY_28)
        self.day28(mode = Day28Mode.TRANQ_CIVILIAN, bills = True)
        self.tas.ending6()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.TAS.DAY_28)
        self.day28(mode = Day28Mode.KILL_GUARD, bills = True)
        self.tas.ending7()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.TAS.DAY_28)
        self.day28(mode = Day28Mode.TRANQ_GUARD, bills = True)
        self.tas.ending8()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.TAS.DAY_28)
        self.day28(mode = Day28Mode.DEFAULT, bills = False)
        self.tas.ending2()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.TAS.DAY_28)
        self.day28(mode = Day28Mode.DEFAULT, bills = True)
        self.day29(getObri = False)
        self.day30(familyPic = True, givePhoto = False)
        self.tas.ending11()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.DAY_30)
        self.day30(familyPic = False, givePhoto = False)
        self.day31(shootMode = Day31ShootMode.SAVE_WALL, escapeMode = Day31EscapeMode.ALONE, ezic = True)
        self.tas.ending16()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.DAY_31)
        self.day31(shootMode = Day31ShootMode.SAVE_WALL, escapeMode = Day31EscapeMode.NO, ezic = True)
        self.tas.ending14()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.DAY_31)
        self.day31(shootMode = Day31ShootMode.YES, escapeMode = Day31EscapeMode.NO, ezic = True)
        self.tas.ending15()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[2]), AllEndings.DAY_31)
        self.day31(shootMode = Day31ShootMode.NO, escapeMode = Day31EscapeMode.NO, ezic = True)
        self.tas.ending19()

        self.tas.restartFrom((DAYS_X[-5], DAYS_Y[2]), AllEndings.TAS.DAY_27)
        self.day27(ezic = False, bills = True)
        self.day28(mode = Day28Mode.DEFAULT, bills = True)
        self.day29(getObri = True)
        self.day30(familyPic = False, givePhoto = True)
        self.day31(shootMode = Day31ShootMode.SAVE_WALL, escapeMode = Day31EscapeMode.WIFE, ezic = False)
        self.tas.ending18()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[3]), AllEndings.DAY_31)
        self.day31(shootMode = Day31ShootMode.YES, escapeMode = Day31EscapeMode.NO, ezic = False)
        self.tas.ending13()

        self.tas.restartFrom((DAYS_X[-1], DAYS_Y[3]), AllEndings.DAY_31)
        self.day31(shootMode = Day31ShootMode.SAVE_WALL, escapeMode = Day31EscapeMode.NO, ezic = False)
        self.tas.ending17()

        self.tas.story()
        # scroll back
        for _ in range(2):
            self.tas.moveTo((DAYS_X[ 0], DAYS_Y[4]))
            self.tas.dragTo((DAYS_X[-1], DAYS_Y[4]))
        self.tas.restartFrom((DAYS_X[4], DAYS_Y[1]), AllEndings.TAS.DAY_14, story = False)
        self.day14(safe = False, messenger = False, ezic = False)
        self.day15(ending4 = False)
        self.day16()
        self.day17(ezic = False)
        self.day18()
        self.day19()
        self.day20(banner = False, poison4 = True)
        self.day21()
        self.day22(pennantOnWall = False)
        self.day23(mode = Day23Mode.DEFAULT)
        self.day24()
        self.day25(shae = True, bills = True)
        self.day26(ending12 = False, bills = True)
        self.day27(ezic = False, bills = True)
        self.day28(mode = Day28Mode.DEFAULT, bills = True)
        self.day29(getObri = False)
        self.day30(familyPic = False, givePhoto = False)
        self.day31(shootMode = Day31ShootMode.SAVE_WALL, escapeMode = Day31EscapeMode.NO, ezic = False)
        self.tas.ending20()