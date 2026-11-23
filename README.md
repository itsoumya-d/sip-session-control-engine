# SIP Session Control Engine

A lightweight RFC 3261 Session Initiation Protocol (SIP) dialog state controller and SDP media session negotiator for real-time VoIP and telecom services.

## Overview
- **RFC 3261 Parser & Validator**: Parses SIP requests and responses (INVITE, 100 Trying, 180 Ringing, 200 OK, ACK, BYE) and validates dialog headers (Call-ID, CSeq, From, To, Via).
- **SDP Codec Negotiation**: Matches audio payload formats (Opus, G.711 PCMU/PCMA) and establishes RTP media endpoints.
- **Dialog Lifecycle Controller**: Enforces strict RFC 3261 dialog state transitions (Early, Confirmed, Terminated) and transaction timeouts.

## Quick Start

```bash
pip install -r requirements.txt
pytest -v
```
