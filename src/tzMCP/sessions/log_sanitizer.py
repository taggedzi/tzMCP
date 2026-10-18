"""Streaming redaction that matches sanitize_log() without holding the whole log.

The log pattern treats whitespace, including newlines, as optional padding around
the separator, and its value runs until CR or LF. A read chunk can therefore
split a secret, or stop before the exporter knows whether a newline is inside
the match. Confirmed secret values are discarded instead of buffered. Text that
might still grow into a match is kept only up to SANITIZER_RAM_LIMIT; anything
beyond that spills to a spooled temporary file.
"""
from __future__ import annotations

import codecs
import re
import tempfile
from typing import Iterator


_LOG_KEYWORDS = ("authorization", "proxy-authorization", "cookie", "set-cookie")
_QUERY_KEYS = ("token", "access_token", "api_key", "apikey", "password", "secret")
_LOG_ALTERNATION = "|".join(_LOG_KEYWORDS)
_QUERY_ALTERNATION = "|".join(_QUERY_KEYS)

SENSITIVE_LOG = re.compile(rf"(?i)({_LOG_ALTERNATION})\s*[:=]\s*[^\r\n]+")
SENSITIVE_QUERY = re.compile(rf"(?i)([?&](?:{_QUERY_ALTERNATION})=)[^&#\s]+")
_KEYWORD_RE = re.compile(rf"(?i){_LOG_ALTERNATION}")
_NON_WS_VALUE = re.compile(rf"(?i)(?:{_LOG_ALTERNATION})\s*[:=]\s*\S")
_WS = re.compile(r"\s")
_QUERY_INTRODUCERS = tuple(f"{mark}{key}=" for mark in ("?", "&") for key in _QUERY_KEYS)

SANITIZER_RAM_LIMIT = 64 * 1024
_KEYWORD_HOLD = 32


def sanitize_log(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="replace")
    text = SENSITIVE_LOG.sub(lambda match: f"{match.group(1)}: [REDACTED]", text)
    text = SENSITIVE_QUERY.sub(r"\1[REDACTED]", text)
    return text.encode("utf-8")


def _is_ws(char: str) -> bool:
    return _WS.fullmatch(char) is not None


def _has_non_ws_value(match_text: str) -> bool:
    return _NON_WS_VALUE.match(match_text) is not None


def _keyword_hold_len(text: str) -> int:
    """Trailing slice that is a case-insensitive prefix of a log keyword."""
    if not text:
        return 0
    window = text[-_KEYWORD_HOLD:]
    best = 0
    for size in range(1, len(window) + 1):
        suffix = window[-size:]
        if any(re.match(re.escape(suffix), keyword, flags=re.IGNORECASE) for keyword in _LOG_KEYWORDS):
            best = size
    return best


def _query_hold_len(text: str) -> int:
    if not text:
        return 0
    lower = text.lower()
    max_size = min(len(lower), max(len(item) for item in _QUERY_INTRODUCERS))
    best = 0
    for size in range(1, max_size + 1):
        suffix = lower[-size:]
        if any(intro.startswith(suffix) for intro in _QUERY_INTRODUCERS):
            best = size
    return best


class _QueryReplacer:
    """Second pass of sanitize_log(): query secrets after log substitution."""

    def __init__(self) -> None:
        self._pending = ""
        self._drop = False
        self.peak_buffered_chars = 0

    def _touch(self) -> None:
        self.peak_buffered_chars = max(self.peak_buffered_chars, len(self._pending))

    def feed(self, text: str, final: bool = False) -> str:
        parts: list[str] = []
        index = 0
        while index < len(text) or (final and index >= len(text)):
            if self._drop:
                if index >= len(text):
                    self._drop = False
                    break
                suffix = self._drop_value(text[index:])
                if self._drop:
                    break
                index = len(text) - len(suffix)
                continue
            room = SANITIZER_RAM_LIMIT - len(self._pending)
            if room <= 0:
                produced, progressed = self._drain(final=False)
                parts.append(produced)
                if not progressed and self._pending:
                    parts.append(self._pending[0])
                    self._pending = self._pending[1:]
                    self._touch()
                continue
            if index >= len(text):
                parts.append(self._drain(final=True)[0])
                break
            take = text[index : index + room]
            index += len(take)
            self._pending += take
            self._touch()
            at_end = final and index >= len(text)
            parts.append(self._drain(final=at_end)[0])
            if at_end:
                break
        return "".join(parts)

    def _drain(self, final: bool) -> tuple[str, bool]:
        out: list[str] = []
        progressed = False
        while self._pending and not self._drop:
            match = SENSITIVE_QUERY.search(self._pending)
            if match is None:
                if final:
                    out.append(self._pending)
                    self._pending = ""
                    self._touch()
                    progressed = True
                    break
                hold = _query_hold_len(self._pending)
                if hold >= len(self._pending):
                    break
                emit = self._pending[: len(self._pending) - hold]
                self._pending = self._pending[len(emit) :]
                self._touch()
                out.append(emit)
                progressed = True
                break
            value_continues = match.end() == len(self._pending) and not final
            out.append(self._pending[: match.start()])
            out.append(f"{match.group(1)}[REDACTED]")
            progressed = True
            if value_continues:
                self._pending = ""
                self._drop = True
                self._touch()
                break
            self._pending = self._pending[match.end() :]
            self._touch()
        return "".join(out), progressed

    def _drop_value(self, text: str) -> str:
        for index, char in enumerate(text):
            if char in "&#" or _is_ws(char):
                self._drop = False
                return text[index:]
        return ""


class _LogReplacer:
    """First pass of sanitize_log(): header-like secrets, including across newlines."""

    def __init__(self) -> None:
        self._pending = ""
        self._mode = "scan"
        self._keyword = ""
        self._spool: tempfile.SpooledTemporaryFile[bytes] | None = None
        self._replay: tempfile.SpooledTemporaryFile[bytes] | None = None
        self._replay_decoder: codecs.IncrementalDecoder | None = None
        self._replay_suffix = ""
        self._after_sep = False
        self._non_crlf_after_sep = False
        self._trailing_start: int | None = None
        self.peak_buffered_chars = 0

    def close(self) -> None:
        replay = self._replay
        spool = self._spool
        self._replay = None
        self._spool = None
        self._replay_decoder = None
        for handle in (replay, spool):
            if handle is not None:
                handle.close()

    def _spool_ram(self) -> int:
        if self._spool is None:
            return 0
        try:
            return min(self._spool.tell(), SANITIZER_RAM_LIMIT)
        except OSError:
            return 0

    def _touch(self) -> None:
        usage = len(self._pending) + len(self._keyword) + len(self._replay_suffix) + self._spool_ram()
        self.peak_buffered_chars = max(self.peak_buffered_chars, usage)

    def iter_feed(self, text: str, final: bool = False) -> Iterator[str]:
        incoming = text
        idle = 0
        for _ in range(10_000_000):
            before = self._signature(incoming)
            produced, incoming, blocked = self._step(incoming, final)
            if produced:
                idle = 0
                for start in range(0, len(produced), SANITIZER_RAM_LIMIT):
                    yield produced[start : start + SANITIZER_RAM_LIMIT]
                continue
            if not incoming and self._replay is None and self._mode == "scan" and not self._pending:
                break
            # A keyword or secret value can stay open until the next chunk.
            if blocked and not incoming and self._replay is None and not final:
                break
            after = self._signature(incoming)
            if after == before:
                idle += 1
                if idle > 3:
                    raise RuntimeError(f"log sanitizer stalled in mode {self._mode}")
            else:
                idle = 0
        else:
            raise RuntimeError("log sanitizer exceeded its step budget")

    def _signature(self, incoming: str) -> tuple[object, ...]:
        replay_pos = None
        if self._replay is not None:
            try:
                replay_pos = self._replay.tell()
            except OSError:
                replay_pos = -1
        return (len(incoming), self._pending, self._mode, replay_pos, self._after_sep, self._keyword)

    def _step(self, incoming: str, final: bool) -> tuple[str, str, bool]:
        if self._mode == "drop":
            if self._pending:
                self._pending = self._drop_text(self._pending)
                self._touch()
                return "", incoming, False
            if incoming:
                return "", self._drop_text(incoming), self._mode == "drop"
            if final:
                self._mode = "scan"
                return "", incoming, False
            return "", incoming, True

        if self._mode == "hold":
            if incoming:
                piece = incoming[:SANITIZER_RAM_LIMIT]
                return self._hold_text(piece), incoming[len(piece) :], False
            if self._replay is not None:
                self._pull_replay()
                return "", incoming, False
            if final:
                return self._hold_eof(), incoming, False
            return "", incoming, True

        if self._replay is not None and len(self._pending) < SANITIZER_RAM_LIMIT:
            self._pull_replay()
            if self._pending or self._replay is not None:
                produced, _blocked = self._drain_scan(final=False)
                return produced, incoming, False

        room = SANITIZER_RAM_LIMIT - len(self._pending)
        if incoming and room > 0 and self._mode == "scan":
            take = incoming[:room]
            incoming = incoming[len(take) :]
            self._pending += take
            self._touch()
        produced, blocked = self._drain_scan(final=final and not incoming and self._replay is None)
        if self._mode == "scan" and len(self._pending) >= SANITIZER_RAM_LIMIT:
            produced += self._force_full_pending()
            blocked = False
        done = blocked and not incoming and self._replay is None and self._mode == "scan"
        return produced, incoming, done

    def _drain_scan(self, final: bool) -> tuple[str, bool]:
        out: list[str] = []
        blocked = False
        while self._mode == "scan" and self._pending:
            produced, blocked = self._scan_once(final)
            if produced:
                out.append(produced)
            if blocked or self._mode != "scan" or not produced:
                break
        return "".join(out), blocked

    def _scan_once(self, final: bool) -> tuple[str, bool]:
        keyword_match = _KEYWORD_RE.search(self._pending)
        if keyword_match is None:
            return self._emit_literal(final)

        if keyword_match.start() > 0:
            prefix = self._pending[: keyword_match.start()]
            self._pending = self._pending[keyword_match.start() :]
            self._touch()
            return prefix, False

        log_match = SENSITIVE_LOG.match(self._pending)
        if log_match and (final or _has_non_ws_value(log_match.group(0))):
            redaction = f"{log_match.group(1)}: [REDACTED]"
            remainder = self._pending[log_match.end() :]
            self._pending = remainder
            self._touch()
            if not final and _has_non_ws_value(log_match.group(0)) and remainder == "":
                self._mode = "drop"
                return redaction, True
            return redaction, False

        if not final and self._might_still_match(keyword_match.end()):
            if len(self._pending) >= SANITIZER_RAM_LIMIT:
                return self._enter_hold(), False
            return "", True

        next_keyword = _KEYWORD_RE.search(self._pending, 1)
        if next_keyword is not None:
            emit = self._pending[: next_keyword.start()]
            self._pending = self._pending[next_keyword.start() :]
            self._touch()
            return emit, False
        return self._emit_literal(final, force_progress=True)

    def _emit_literal(self, final: bool, force_progress: bool = False) -> tuple[str, bool]:
        if final:
            text = self._pending
            self._pending = ""
            self._touch()
            return text, False
        hold = _keyword_hold_len(self._pending)
        if hold >= len(self._pending):
            if force_progress and self._pending:
                emit = self._pending[0]
                self._pending = self._pending[1:]
                self._touch()
                return emit, False
            return "", True
        emit = self._pending[: len(self._pending) - hold]
        self._pending = self._pending[len(emit) :]
        self._touch()
        return emit, False

    def _might_still_match(self, keyword_len: int) -> bool:
        rest = self._pending[keyword_len:]
        index = 0
        while index < len(rest) and _is_ws(rest[index]):
            index += 1
        if index == len(rest):
            return True
        return rest[index] in ":="

    def _force_full_pending(self) -> str:
        if _KEYWORD_RE.match(self._pending):
            return self._enter_hold()
        if not self._pending:
            return ""
        emit = self._pending[0]
        self._pending = self._pending[1:]
        self._touch()
        return emit

    def _enter_hold(self) -> str:
        match = _KEYWORD_RE.match(self._pending)
        if match is None:
            raise RuntimeError("log sanitizer hold started without a keyword")
        rest = self._pending[match.end() :]
        self._keyword = match.group(0)
        self._pending = ""
        self._spool = tempfile.SpooledTemporaryFile(max_size=SANITIZER_RAM_LIMIT, mode="w+b")
        self._mode = "hold"
        self._after_sep = False
        self._non_crlf_after_sep = False
        self._trailing_start = None
        self._touch()
        return self._hold_text(rest)

    def _hold_text(self, text: str) -> str:
        index = 0
        while index < len(text) and self._mode == "hold":
            char = text[index]
            index += 1
            action = self._hold_char(char)
            if action == "confirmed":
                return self._confirm(text[index:])
            if action == "failed":
                return self._begin_replay(text[index:])
        return ""

    def _hold_char(self, char: str) -> str:
        if self._spool is None:
            raise RuntimeError("log sanitizer hold has no spool")
        position = self._spool.tell()
        self._spool.write(char.encode("utf-8"))
        self._touch()
        if not self._after_sep:
            if _is_ws(char):
                return ""
            if char in ":=":
                self._after_sep = True
                return ""
            return "failed"
        if char in "\r\n":
            if self._trailing_start is None:
                self._trailing_start = position
            return ""
        self._non_crlf_after_sep = True
        self._trailing_start = None
        if not _is_ws(char):
            return "confirmed"
        return ""

    def _confirm(self, extra: str) -> str:
        keyword = self._keyword
        self._discard_spool()
        self._keyword = ""
        self._after_sep = False
        self._non_crlf_after_sep = False
        self._trailing_start = None
        self._mode = "drop"
        self._pending = self._drop_text(extra)
        self._touch()
        return f"{keyword}: [REDACTED]"

    def _begin_replay(self, extra: str) -> str:
        if self._spool is None or not self._keyword:
            raise RuntimeError("log sanitizer replay is missing its hold state")
        first = self._keyword[0]
        rest = self._keyword[1:]
        self._spool.seek(0)
        self._replay = self._spool
        self._spool = None
        self._replay_decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        self._replay_suffix = extra
        self._keyword = ""
        self._after_sep = False
        self._non_crlf_after_sep = False
        self._trailing_start = None
        self._mode = "scan"
        self._pending = rest
        self._touch()
        return first

    def _hold_eof(self) -> str:
        if not self._after_sep or not self._non_crlf_after_sep:
            return self._begin_replay("")
        keyword = self._keyword
        spool = self._spool
        start = self._trailing_start
        self._spool = None
        self._keyword = ""
        self._after_sep = False
        self._non_crlf_after_sep = False
        self._trailing_start = None
        self._mode = "scan"
        if spool is None:
            return f"{keyword}: [REDACTED]"
        if start is None:
            spool.close()
            return f"{keyword}: [REDACTED]"
        spool.seek(start)
        self._replay = spool
        self._replay_decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        self._replay_suffix = ""
        return f"{keyword}: [REDACTED]"

    def _pull_replay(self) -> None:
        if self._replay is None or self._replay_decoder is None:
            return
        raw = self._replay.read(SANITIZER_RAM_LIMIT)
        if raw:
            self._pending += self._replay_decoder.decode(raw)
            self._touch()
            return
        tail = self._replay_decoder.decode(b"", final=True)
        extra = self._replay_suffix
        self._replay.close()
        self._replay = None
        self._replay_decoder = None
        self._replay_suffix = ""
        self._pending += tail + extra
        self._touch()

    def _drop_text(self, text: str) -> str:
        carriage = text.find("\r")
        newline = text.find("\n")
        indexes = [index for index in (carriage, newline) if index >= 0]
        if not indexes:
            return ""
        self._mode = "scan"
        return text[min(indexes) :]

    def _discard_spool(self) -> None:
        if self._spool is not None:
            self._spool.close()
            self._spool = None


class StreamingLogSanitizer:
    """Sanitize one log in bounded pieces. Output matches sanitize_log(data)."""

    def __init__(self) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._log = _LogReplacer()
        self._query = _QueryReplacer()

    def close(self) -> None:
        self._log.close()

    @property
    def peak_buffered_chars(self) -> int:
        return self._log.peak_buffered_chars + self._query.peak_buffered_chars

    def iter_feed(self, data: bytes) -> Iterator[bytes]:
        text = self._decoder.decode(data) if data else ""
        yield from self._encode(self._log.iter_feed(text, final=False))

    def iter_finish(self) -> Iterator[bytes]:
        text = self._decoder.decode(b"", final=True)
        yield from self._encode(self._log.iter_feed(text, final=True))
        produced = self._query.feed("", final=True)
        if produced:
            yield produced.encode("utf-8")

    def _encode(self, pieces: Iterator[str]) -> Iterator[bytes]:
        for piece in pieces:
            produced = self._query.feed(piece, final=False)
            if produced:
                yield produced.encode("utf-8")
