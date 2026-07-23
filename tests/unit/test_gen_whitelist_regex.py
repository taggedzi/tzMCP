import re

from tzMCP.save_media_utils.gen_whitelist_regex import smart_regex


def test_two_part_domain_is_escaped():
    assert smart_regex("example.com") == r"example\.com"


def test_three_part_non_numeric_subdomain():
    assert smart_regex("cdn.example.com") == r".*\.example\.com"


def test_three_part_numeric_subdomain_matches_numeric_variants():
    pattern = smart_regex("cdn12.example.com")
    assert pattern == r"cdn[0-9]+\.example\.com"
    assert re.fullmatch(pattern, "cdn12.example.com")
    assert re.fullmatch(pattern, "cdn99.example.com")
    assert not re.fullmatch(pattern, "cdn.example.com")
