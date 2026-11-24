# SIP Session Control Engine

A lightweight RFC 3261 Session Initiation Protocol (SIP) dialog state controller and SDP media session negotiator for real-time VoIP and telecom services.

## Overview
- **RFC 3261 Parser & Validator**: Parses SIP requests and responses (INVITE, 100 Trying, 180 Ringing, 200 OK, ACK, BYE) and validates dialog headers (Call-ID, CSeq, From, To, Via).
- **SDP Codec Negotiation**: Matches audio payload formats (Opus, G.711 PCMU/PCMA) and establishes RTP media endpoints.
- **Dialog Lifecycle Controller**: Enforces strict RFC 3261 dialog state transitions (Early, Confirmed, Terminated) and transaction timeouts.
- **AI Voice Agent & Contact Centre Handover**: Real-time intent classification, caller sentiment tracking, speech recognition confidence evaluation, and deterministic human agent handover via SIP `REFER` transfer payloads when frustration or low confidence is detected.

## Quick Start

```bash
pip install -r requirements.txt
pytest -v
```
