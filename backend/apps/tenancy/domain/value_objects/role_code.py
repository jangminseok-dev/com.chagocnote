from enum import Enum


class RoleCode(str, Enum):
    OWNER = "owner"
    STAFF = "staff"
