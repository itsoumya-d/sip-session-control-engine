import pytest
from src.sip_engine.models import DialogState, SipMethod
from src.sip_engine.parser import SipParser
from src.sip_engine.dialog_controller import SipDialogController

INVITE_RAW = ("INVITE sip:agent@telecom.cloud.internal SIP/2.0\n"
              "Via: SIP/2.0/UDP 10.0.1.20:5060;branch=z9hG4bK-771\n"
              "From: \"Alice\" <sip:alice@carrier.net>;tag=tag-alice-101\n"
              "To: <sip:agent@telecom.cloud.internal>\n"
              "Call-ID: call-8829-xyz@carrier.net\n"
              "CSeq: 1 INVITE\nContent-Type: application/sdp\n\n"
              "v=0\nm=audio 49170 RTP/AVP 111 0\na=rtpmap:111 opus/48000/2\na=rtpmap:0 PCMU/8000\n")

RINGING_180 = ("SIP/2.0 180 Ringing\n"
               "Via: SIP/2.0/UDP 10.0.1.20:5060;branch=z9hG4bK-771\n"
               "From: \"Alice\" <sip:alice@carrier.net>;tag=tag-alice-101\n"
               "To: <sip:agent@telecom.cloud.internal>;tag=tag-agent-202\n"
               "Call-ID: call-8829-xyz@carrier.net\nCSeq: 1 INVITE\n\n")

OK_200 = ("SIP/2.0 200 OK\n"
          "Via: SIP/2.0/UDP 10.0.1.20:5060;branch=z9hG4bK-771\n"
          "From: \"Alice\" <sip:alice@carrier.net>;tag=tag-alice-101\n"
          "To: <sip:agent@telecom.cloud.internal>;tag=tag-agent-202\n"
          "Call-ID: call-8829-xyz@carrier.net\nCSeq: 1 INVITE\nContent-Type: application/sdp\n\n"
          "v=0\nm=audio 49172 RTP/AVP 111\na=rtpmap:111 opus/48000/2\n")

ACK_RAW = ("ACK sip:agent@telecom.cloud.internal SIP/2.0\n"
           "Via: SIP/2.0/UDP 10.0.1.20:5060;branch=z9hG4bK-772\n"
           "From: \"Alice\" <sip:alice@carrier.net>;tag=tag-alice-101\n"
           "To: <sip:agent@telecom.cloud.internal>;tag=tag-agent-202\n"
           "Call-ID: call-8829-xyz@carrier.net\nCSeq: 1 ACK\n\n")

BYE_RAW = ("BYE sip:alice@carrier.net SIP/2.0\n"
           "Via: SIP/2.0/UDP 10.0.2.50:5060;branch=z9hG4bK-990\n"
           "From: <sip:agent@telecom.cloud.internal>;tag=tag-agent-202\n"
           "To: \"Alice\" <sip:alice@carrier.net>;tag=tag-alice-101\n"
           "Call-ID: call-8829-xyz@carrier.net\nCSeq: 2 BYE\n\n")

def test_full_sip_call_lifecycle_and_codec_negotiation():
    controller = SipDialogController(supported_codecs=["OPUS", "PCMU"])
    assert controller.state == DialogState.IDLE

    ok, _ = controller.process_message(SipParser.parse(INVITE_RAW))
    assert ok and controller.state == DialogState.CALLING
    assert controller.call_id == "call-8829-xyz@carrier.net"

    ok, _ = controller.process_message(SipParser.parse(RINGING_180))
    assert ok and controller.state == DialogState.EARLY

    ok, _ = controller.process_message(SipParser.parse(OK_200))
    assert ok and controller.negotiated_codec == "OPUS"

    ok, _ = controller.process_message(SipParser.parse(ACK_RAW))
    assert ok and controller.state == DialogState.CONFIRMED

    ok, _ = controller.process_message(SipParser.parse(BYE_RAW))
    assert ok and controller.state == DialogState.TERMINATED

def test_call_id_mismatch_rejected():
    controller = SipDialogController()
    controller.process_message(SipParser.parse(INVITE_RAW))
    bad = SipParser.parse(RINGING_180.replace("call-8829-xyz@carrier.net", "wrong-call-id"))
    ok, err = controller.process_message(bad)
    assert not ok and "Call-ID mismatch" in err

def test_call_cancellation():
    controller = SipDialogController()
    controller.process_message(SipParser.parse(INVITE_RAW))
    cancel = ("CANCEL sip:agent@telecom.cloud.internal SIP/2.0\n"
              "Via: SIP/2.0/UDP 10.0.1.20:5060;branch=z9hG4bK-771\n"
              "From: \"Alice\" <sip:alice@carrier.net>;tag=tag-alice-101\n"
              "To: <sip:agent@telecom.cloud.internal>\n"
              "Call-ID: call-8829-xyz@carrier.net\nCSeq: 1 CANCEL\n\n")
    ok, _ = controller.process_message(SipParser.parse(cancel))
    assert ok and controller.state == DialogState.TERMINATED
