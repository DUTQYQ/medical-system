from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.database import now


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)


class Credentials(StrictModel):
    phone: str = Field(pattern=r'^1\d{10}$')
    password: str = Field(min_length=8, max_length=72)

    @field_validator('password')
    @classmethod
    def password_size(cls, value):
        if len(value.encode()) > 72:
            raise ValueError('密码 UTF-8 字节长度不能超过 72')
        return value


class Register(Credentials):
    name: str = Field(min_length=1, max_length=50)
    role: Literal['ELDER', 'FAMILY', 'CARE', 'ADMIN'] = 'ELDER'


class ProfileInput(StrictModel):
    name: str = Field(min_length=1, max_length=50)
    user_id: int | None = Field(default=None, gt=0)
    source_profile_id: int | None = Field(default=None, gt=0)
    gender: Literal['M', 'F'] | None = None
    birthday: date | None = None
    height: float | None = Field(default=None, gt=0, lt=1000)
    weight: float | None = Field(default=None, gt=0, lt=1000)
    blood_type: str | None = Field(default=None, max_length=5)
    allergy: str | None = Field(default=None, max_length=255)
    medical_history: str | None = Field(default=None, max_length=500)
    chronic_tags: list[str] = Field(default_factory=list, max_length=30)
    emergency_contact: str | None = Field(default=None, max_length=50)
    emergency_phone: str | None = Field(default=None, max_length=20)

    @field_validator('birthday')
    @classmethod
    def past_birthday(cls, value):
        if value and value > now().date():
            raise ValueError('出生日期不能在未来')
        return value


class HealthInput(StrictModel):
    profile_id: int = Field(gt=0)
    type: Literal['BLOOD_PRESSURE', 'BLOOD_SUGAR', 'HEART_RATE', 'SLEEP', 'STEP']
    values: dict
    measured_at: datetime
    remark: str = Field(default='', max_length=255)

    @field_validator('measured_at')
    @classmethod
    def measurement_date(cls, value):
        if value.tzinfo:
            raise ValueError('测量时间须采用中国本地时间，不带时区后缀')
        if value > now():
            raise ValueError('测量时间不能在未来')
        return value


class BindInput(StrictModel):
    phone: str = Field(pattern=r'^1\d{10}$')
    profile_id: int | None = Field(default=None, gt=0)
    relation: str = Field(min_length=1, max_length=20)
    note: str = Field(default='', max_length=255)


class ConfirmBind(StrictModel):
    action: Literal['APPROVE', 'REJECT']
    note: str = Field(default='', max_length=255)


class HandleInput(StrictModel):
    result: str = Field(min_length=1, max_length=500)
    action: Literal['CONTACTED', 'ARRANGED_VISIT', 'SENT_HOSPITAL', 'OBSERVE']


class StatusInput(StrictModel):
    status: Literal['PROCESSING', 'IGNORED']


class EnabledInput(StrictModel):
    enabled: bool


class RoleInput(StrictModel):
    role: Literal['CARE', 'ADMIN']


class ThresholdInput(StrictModel):
    level0_range: str = Field(min_length=1, max_length=100)
    level1_range: str = Field(min_length=1, max_length=100)
    level2_range: str = Field(min_length=1, max_length=100)
    level3_range: str = Field(min_length=1, max_length=100)
    enabled: bool = True


class KnowledgeInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(default='', max_length=50)
    content: str = Field(min_length=1, max_length=100000)
    enabled: bool = True


class MeInput(StrictModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, pattern=r'^1\d{10}$')
    avatar: str | None = Field(default=None, max_length=255)


class PasswordInput(StrictModel):
    old_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


class ConsentInput(StrictModel):
    accepted: bool
    version: str = Field(default='1.0', min_length=1, max_length=20)


class AssignmentInput(StrictModel):
    care_user_id: int = Field(gt=0)
    profile_id: int = Field(gt=0)
    enabled: bool = True


class IndicatorInput(StrictModel):
    name: str = Field(min_length=1, max_length=50)
    unit: str = Field(min_length=1, max_length=20)
    enabled: bool = True
    ranges: dict[str, tuple[float, float]] = Field(default_factory=dict)
