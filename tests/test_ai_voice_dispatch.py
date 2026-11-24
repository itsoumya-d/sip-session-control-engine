import pytest
from src.sip_engine.voice_agent_dispatch import (
    AIVoiceDispatchEngine,
    CallIntent,
    HandoverTrigger,
)


def test_normal_ai_agent_flow():
    engine = AIVoiceDispatchEngine()
    session = engine.process_turn(
        call_id="call-001",
        caller_number="+6494891502",
        utterance="I would like to check the details on my latest invoice.",
        confidence=0.95,
        sentiment_score=0.2,
    )
    assert session.current_intent == CallIntent.BILLING
    assert session.requires_handover is False
    assert session.target_skill_queue == "ai_voice_bot"
    assert session.sip_refer_payload is None


def test_explicit_human_agent_handover():
    engine = AIVoiceDispatchEngine()
    engine.process_turn(
        call_id="call-002",
        caller_number="+6494891502",
        utterance="My fibre internet is completely down and offline.",
        confidence=0.92,
        sentiment_score=-0.2,
    )
    session = engine.process_turn(
        call_id="call-002",
        caller_number="+6494891502",
        utterance="I need to speak to a real person and human technician right now.",
        confidence=0.94,
        sentiment_score=-0.3,
    )
    assert session.current_intent == CallIntent.TECHNICAL_SUPPORT
    assert session.requires_handover is True
    assert session.handover_reason == HandoverTrigger.CUSTOMER_REQUESTED
    assert session.sip_refer_payload is not None
    assert session.sip_refer_payload["Method"] == "REFER"
    assert "general_tier1_queue" in session.sip_refer_payload["Refer-To"]


def test_frustration_handover_to_supervisor():
    engine = AIVoiceDispatchEngine()
    engine.process_turn(
        call_id="call-003",
        caller_number="+6421555123",
        utterance="This service is ridiculous and completely broken.",
        confidence=0.90,
        sentiment_score=-0.7,
    )
    session = engine.process_turn(
        call_id="call-003",
        caller_number="+6421555123",
        utterance="Nothing works and I am furious with this delay.",
        confidence=0.91,
        sentiment_score=-0.8,
    )
    assert session.requires_handover is True
    assert session.handover_reason == HandoverTrigger.CUSTOMER_FRUSTRATION
    assert session.target_skill_queue == "supervisor_queue"
    assert "queue-supervisor" in session.sip_refer_payload["Refer-To"]


def test_low_confidence_clarification_handover():
    engine = AIVoiceDispatchEngine()
    engine.process_turn(
        call_id="call-004",
        caller_number="+6421999888",
        utterance="Muffled background noise static...",
        confidence=0.45,
        sentiment_score=0.0,
    )
    session = engine.process_turn(
        call_id="call-004",
        caller_number="+6421999888",
        utterance="Distorted garbled audio speech...",
        confidence=0.50,
        sentiment_score=0.0,
    )
    assert session.requires_handover is True
    assert session.handover_reason == HandoverTrigger.LOW_CONFIDENCE


def test_qos_degradation_handover():
    engine = AIVoiceDispatchEngine()
    session = engine.process_turn(
        call_id="call-005",
        caller_number="+6491234567",
        utterance="Can you hear me?",
        confidence=0.88,
        sentiment_score=0.0,
        mos_score=1.8,  # Degraded audio quality
    )
    assert session.requires_handover is True
    assert session.handover_reason == HandoverTrigger.QOS_DEGRADED
    assert session.target_skill_queue == "tier2_technical"
