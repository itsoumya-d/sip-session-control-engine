from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

class SipMethod(str, Enum):
    INVITE = "INVITE"
    ACK = "ACK"
    BYE = "BYE"
    CANCEL = "CANCEL"
    OPTIONS = "OPTIONS"
    REGISTER = "REGISTER"

class DialogState(str, Enum):
    IDLE = "IDLE"
    CALLING = "CALLING"
    PROCEEDING = "PROCEEDING"
    EARLY = "EARLY"
    CONFIRMED = "CONFIRMED"
    TERMINATED = "TERMINATED"

@dataclass
class SipMessage:
    is_response: bool
    method: Optional[SipMethod] = None
    status_code: Optional[int] = None
    status_phrase: Optional[str] = None
    call_id: str = ""
    from_uri: str = ""
    from_tag: Optional[str] = None
    to_uri: str = ""
    to_tag: Optional[str] = None
    cseq_num: int = 1
    cseq_method: str = ""
    via_branch: Optional[str] = None
    sdp_codecs: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
