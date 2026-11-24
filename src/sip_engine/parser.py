import re
from typing import List, Optional, Tuple
from .models import SipMessage, SipMethod

class SipParser:
    @staticmethod
    def parse(raw: str) -> SipMessage:
        raw = raw.replace("\r\n", "\n")
        parts = raw.split("\n\n", 1)
        header_text = parts[0]
        body_text = parts[1] if len(parts) > 1 else ""

        lines = header_text.split("\n")
        first_line = lines[0].strip()

        is_response = first_line.startswith("SIP/2.0")
        method = None
        status_code = None
        status_phrase = None

        if is_response:
            m = re.match(r"SIP/2\.0\s+(\d{3})\s*(.*)", first_line)
            if m:
                status_code = int(m.group(1))
                status_phrase = m.group(2).strip()
        else:
            tokens = first_line.split()
            if tokens and tokens[0] in SipMethod.__members__:
                method = SipMethod(tokens[0])

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        call_id = headers.get("call-id", "")
        cseq_str = headers.get("cseq", "")
        cseq_num = 1
        cseq_method = ""
        if cseq_str:
            c_tokens = cseq_str.split()
            if c_tokens and c_tokens[0].isdigit():
                cseq_num = int(c_tokens[0])
            if len(c_tokens) > 1:
                cseq_method = c_tokens[1]

        from_raw = headers.get("from", "")
        from_uri, from_tag = SipParser._parse_address_and_tag(from_raw)

        to_raw = headers.get("to", "")
        to_uri, to_tag = SipParser._parse_address_and_tag(to_raw)

        via_raw = headers.get("via", "")
        via_branch = None
        if "branch=" in via_raw:
            b_m = re.search(r"branch=([^;\s]+)", via_raw)
            if b_m:
                via_branch = b_m.group(1)

        sdp_codecs = SipParser._extract_sdp_codecs(body_text)

        return SipMessage(
            is_response=is_response,
            method=method,
            status_code=status_code,
            status_phrase=status_phrase,
            call_id=call_id,
            from_uri=from_uri,
            from_tag=from_tag,
            to_uri=to_uri,
            to_tag=to_tag,
            cseq_num=cseq_num,
            cseq_method=cseq_method,
            via_branch=via_branch,
            sdp_codecs=sdp_codecs,
            headers=headers
        )

    @staticmethod
    def _parse_address_and_tag(hdr: str) -> Tuple[str, Optional[str]]:
        tag = None
        if "tag=" in hdr:
            t_m = re.search(r"tag=([^;\s>]+)", hdr)
            if t_m:
                tag = t_m.group(1)
        uri = hdr.split(";")[0].strip()
        u_m = re.search(r"<([^>]+)>", uri)
        if u_m:
            uri = u_m.group(1)
        return uri, tag

    @staticmethod
    def _extract_sdp_codecs(body: str) -> List[str]:
        codecs = []
        for line in body.split("\n"):
            if line.startswith("a=rtpmap:"):
                m = re.match(r"a=rtpmap:\d+\s+([A-Za-z0-9\-]+)/", line)
                if m:
                    codecs.append(m.group(1).upper())
        return codecs
