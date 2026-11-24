"""AI Voice Agent dialogue management, sentiment tracking, and contact centre human handover engine."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class CallIntent(str, Enum):
    BILLING = "BILLING"
    TECHNICAL_SUPPORT = "TECHNICAL_SUPPORT"
    NEW_SERVICE = "NEW_SERVICE"
    GENERAL_FAQ = "GENERAL_FAQ"
    UNKNOWN = "UNKNOWN"


class HandoverTrigger(str, Enum):
    CUSTOMER_REQUESTED = "CUSTOMER_REQUESTED"
    CUSTOMER_FRUSTRATION = "CUSTOMER_FRUSTRATION"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ESCALATION = "ESCALATION"
    QOS_DEGRADED = "QOS_DEGRADED"


@dataclass
class VoiceTurn:
    turn_id: int
    speaker: str  # "caller" or "ai_agent"
    utterance: str
    confidence: float
    sentiment_score: float  # -1.0 to +1.0
    timestamp_ms: int


@dataclass
class VoiceSession:
    call_id: str
    caller_number: str
    current_intent: CallIntent = CallIntent.UNKNOWN
    turns: List[VoiceTurn] = field(default_factory=list)
    average_confidence: float = 1.0
    average_sentiment: float = 0.0
    requires_handover: bool = False
    handover_reason: Optional[HandoverTrigger] = None
    target_skill_queue: str = "ai_voice_bot"
    sip_refer_payload: Optional[Dict[str, str]] = None


class AIVoiceDispatchEngine:
    """Manages AI conversational voice turns and deterministic handover to contact centre agent queues."""

    def __init__(self):
        self.sessions: Dict[str, VoiceSession] = {}

    def get_or_create_session(self, call_id: str, caller_number: str) -> VoiceSession:
        if call_id not in self.sessions:
            self.sessions[call_id] = VoiceSession(call_id=call_id, caller_number=caller_number)
        return self.sessions[call_id]

    def classify_intent(self, text: str) -> CallIntent:
        lower = text.lower()
        if any(w in lower for w in ("bill", "invoice", "payment", "charge", "refund", "receipt")):
            return CallIntent.BILLING
        if any(w in lower for w in ("outage", "slow", "down", "fibre", "wifi", "router", "broken", "offline", "disconnect")):
            return CallIntent.TECHNICAL_SUPPORT
        if any(w in lower for w in ("new line", "sign up", "plan", "upgrade", "pricing", "order")):
            return CallIntent.NEW_SERVICE
        if any(w in lower for w in ("hours", "address", "location", "open", "holiday")):
            return CallIntent.GENERAL_FAQ
        return CallIntent.UNKNOWN

    def check_human_request(self, text: str) -> bool:
        lower = text.lower()
        phrases = (
            "human",
            "agent",
            "representative",
            "real person",
            "operator",
            "speak to someone",
            "talk to a person",
            "manager",
            "supervisor",
        )
        return any(p in lower for p in phrases)

    def process_turn(
        self,
        call_id: str,
        caller_number: str,
        utterance: str,
        confidence: float,
        sentiment_score: float,
        mos_score: float = 4.2,
        timestamp_ms: int = 0,
    ) -> VoiceSession:
        session = self.get_or_create_session(call_id, caller_number)
        turn_num = len(session.turns) + 1
        turn = VoiceTurn(
            turn_id=turn_num,
            speaker="caller",
            utterance=utterance,
            confidence=max(0.0, min(1.0, confidence)),
            sentiment_score=max(-1.0, min(1.0, sentiment_score)),
            timestamp_ms=timestamp_ms,
        )
        session.turns.append(turn)

        # Update intent if currently unknown or stronger match
        detected_intent = self.classify_intent(utterance)
        if detected_intent != CallIntent.UNKNOWN:
            session.current_intent = detected_intent

        # Recalculate metrics
        session.average_confidence = sum(t.confidence for t in session.turns) / len(session.turns)
        session.average_sentiment = sum(t.sentiment_score for t in session.turns) / len(session.turns)

        # 1. Telephony QoS degradation check (MOS < 2.5)
        if mos_score < 2.5:
            session.requires_handover = True
            session.handover_reason = HandoverTrigger.QOS_DEGRADED
            session.target_skill_queue = "tier2_technical"
            session.sip_refer_payload = self._build_refer(session, "sip:queue-tier2-voice@telecom.local")
            return session

        # 2. Explicit caller request for human operator
        if self.check_human_request(utterance):
            session.requires_handover = True
            session.handover_reason = HandoverTrigger.CUSTOMER_REQUESTED
            session.target_skill_queue = (
                "billing_specialists" if session.current_intent == CallIntent.BILLING else "general_tier1_queue"
            )
            session.sip_refer_payload = self._build_refer(session, f"sip:{session.target_skill_queue}@telecom.local")
            return session

        # 3. Customer frustration: consecutive negative sentiment
        if len(session.turns) >= 2:
            last_two = session.turns[-2:]
            if all(t.sentiment_score <= -0.45 for t in last_two):
                session.requires_handover = True
                session.handover_reason = HandoverTrigger.CUSTOMER_FRUSTRATION
                session.target_skill_queue = "supervisor_queue"
                session.sip_refer_payload = self._build_refer(session, "sip:queue-supervisor@telecom.local")
                return session

        # 4. Low speech recognition confidence: repeated clarification failure
        if len(session.turns) >= 2:
            last_two = session.turns[-2:]
            if all(t.confidence < 0.60 for t in last_two):
                session.requires_handover = True
                session.handover_reason = HandoverTrigger.LOW_CONFIDENCE
                session.target_skill_queue = (
                    "tier2_technical"
                    if session.current_intent == CallIntent.TECHNICAL_SUPPORT
                    else "general_tier1_queue"
                )
                session.sip_refer_payload = self._build_refer(session, f"sip:{session.target_skill_queue}@telecom.local")
                return session

        # Default: handled by AI voice agent
        session.target_skill_queue = "ai_voice_bot"
        return session

    def _build_refer(self, session: VoiceSession, target_uri: str) -> Dict[str, str]:
        return {
            "Method": "REFER",
            "Call-ID": session.call_id,
            "Refer-To": f"<{target_uri}>",
            "Referred-By": "<sip:ai-voice-agent@telecom.local>",
            "X-Handover-Reason": session.handover_reason.value if session.handover_reason else "NONE",
            "X-Intent": session.current_intent.value,
            "X-Turns-Count": str(len(session.turns)),
        }
