from PIL import Image

from modules.documents.document import BaseDocument
from modules.faceRecognition    import Face, FaceType

class Person:
    def __init__(self):
        self.appearance: Image.Image | None = None
        self.weight: int | None             = None

    @BaseDocument.field
    def face(self) -> Face:
        return Face.parse(self.appearance, FaceType.PERSON)
    
    def reset(self, appearance: Image.Image | None = None) -> None:
        if hasattr(self, "_cached__face"):
            delattr(self, "_cached__face")

        self.appearance = appearance
        if appearance is None:
            self.weight = None

    def checkValidHeight(self, height: int) -> bool:
        return self.face is None or self.face.height - Face.HEIGHT_TOLERANCE_CM <= height <= self.face.height + Face.HEIGHT_TOLERANCE_CM

    def __repr__(self) -> str:
        return f"""==- Person -==
face:   {self.face}
weight: {self.weight}"""