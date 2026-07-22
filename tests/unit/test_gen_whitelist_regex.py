from tzMCP.save_media_utils.gen_whitelist_regex import smart_regex


def test_two_part_domain_is_escaped():
    assert smart_regex("example.com") == r"example\.com"


def test_three_part_non_numeric_subdomain():
    assert smart_regex("cdn.example.com") == r".*\.example\.com"


def test_three_part_numeric_subdomain_double_escaped():
    # Documents the actual (quirky) output: the generated [0-9]+ is itself
    # re.escape'd. See the domain-matcher defect note in the spec.
    assert smart_regex("cdn12.example.com") == r"cdn\[0\-9\]\+\.example\.com"
