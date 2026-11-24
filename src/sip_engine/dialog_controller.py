from typing import List, Optional, Tuple
from .models import DialogState, SipMessage, SipMethod

class SipDialogController:
    def __init__(self, supported_codecs: Optional[List[str]] = None):
        self.supported_codecs = [c.upper() for c in (supported_codecs or ["OPUS", "PCMU", "PCMA"])]
        self.state = DialogState.IDLE
        self.call_id: Optional[str] = None
        self.local_tag: Optional[str] = None
        self.remote_tag: Optional[str] = None
        self.last_cseq: int = 0
        self.negotiated_codec: Optional[str] = None

    def process_message(self, msg: SipMessage) -> Tuple[bool, Optional[str]]:
        if self.state == DialogState.IDLE:
            if msg.is_response or msg.method != SipMethod.INVITE:
                return False, f"Expected INVITE in IDLE state, got {msg.method or msg.status_code}"
            if not msg.call_id:
                return False, "Missing Call-ID header"
            self.call_id = msg.call_id
            self.remote_tag = msg.from_tag
            self.last_cseq = msg.cseq_num
            self.state = DialogState.CALLING
            return True, None

        if msg.call_id != self.call_id:
            return False, f"Call-ID mismatch: expected {self.call_id}, got {msg.call_id}"

        if msg.is_response:
            code = msg.status_code or 0
            if 100 <= code < 200:
                if code == 100:
                    self.state = DialogState.PROCEEDING
                elif code == 180 or code == 183:
                    self.state = DialogState.EARLY
                if msg.to_tag:
                    self.local_tag = msg.to_tag
                return True, None
            elif 200 <= code < 300:
                self.local_tag = msg.to_tag or self.local_tag
                if msg.sdp_codecs:
                    self.negotiated_codec = self._negotiate_codec(msg.sdp_codecs)
                return True, None
            elif code >= 400:
                self.state = DialogState.TERMINATED
                return True, f"Call failed with status {code}: {msg.status_phrase}"
        else:
            if msg.method == SipMethod.ACK:
                if self.state in (DialogState.CALLING, DialogState.PROCEEDING, DialogState.EARLY):
                    self.state = DialogState.CONFIRMED
                    return True, None
                return False, f"Invalid ACK in state {self.state}"
            elif msg.method == SipMethod.BYE:
                if self.state == DialogState.CONFIRMED:
                    self.state = DialogState.TERMINATED
                    return True, None
                return False, f"Cannot process BYE in state {self.state}"
            elif msg.method == SipMethod.CANCEL:
                if self.state in (DialogState.CALLING, DialogState.PROCEEDING, DialogState.EARLY):
                    self.state = DialogState.TERMINATED
                    return True, None
                return False, f"Cannot CANCEL dialog in state {self.state}"

        return False, "Unhandled SIP message transition"

    def _negotiate_codec(self, remote_codecs: List[str]) -> Optional[str]:
        for supp in self.supported_codecs:
            if supp in [r.upper() for r in remote_codecs]:
                return supp
        return None
