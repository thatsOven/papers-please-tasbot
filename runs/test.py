from modules.run import Run

from modules.constants.other import Sex

class FaceTest(Run):
    def run(self) -> None:
        self.tas.shutter = False
        self.tas.person.weight = 0
        self.tas.processEditor.setSex(Sex.F)
        self.tas.processEditor.setFace(0, 0, 14, 0, 0, False)
        self.tas.nextPartial()