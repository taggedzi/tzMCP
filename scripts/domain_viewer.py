from typing import List, Pattern
import re


def generate_regex_for_domains(domains: List[str]) -> Pattern:
    """
    Given a list of domain strings, compile a regex pattern that matches any of them.
    """
    escaped = [re.escape(domain) for domain in domains]
    pattern = r"(?:" + r"|".join(escaped) + r")"
    return re.compile(pattern)
