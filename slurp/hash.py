import uuid


def strhash(payload: bytes) -> str:
    return str(uuid.UUID(int=abs(hash(payload)), version=4))
