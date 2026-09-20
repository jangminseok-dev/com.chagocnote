from enum import Enum


class Provider(str, Enum):
    KAKAO = "kakao"
    APPLE = "apple"
    GOOGLE = "google"
    DEV = "dev"
