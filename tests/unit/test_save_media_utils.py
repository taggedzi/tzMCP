from pathlib import Path

import pytest

from tzMCP.save_media_utils import save_media_utils as smu


# ---- sanitize_filename ----------------------------------------------------
def test_sanitize_filename_replaces_illegal_chars():
    assert smu.sanitize_filename("a b/c*d.png") == "a_b_c_d.png"


def test_sanitize_filename_truncates_to_255():
    long_name = "x" * 400
    assert len(smu.sanitize_filename(long_name)) == 255


def test_sanitize_filename_reserved_name_gets_hashed():
    result = smu.sanitize_filename("CON", fallback_url="http://x/y")
    assert result.startswith("file_")
    assert result != "CON"


def test_sanitize_filename_empty_gets_hashed():
    result = smu.sanitize_filename("", fallback_url="http://x/y")
    assert result.startswith("file_")


# ---- safe_filename --------------------------------------------------------
def test_safe_filename_no_dot_generates_name():
    result = smu.safe_filename("noext", ".png", fallback_url="http://x/y")
    assert result.startswith("file_")
    assert result.endswith(".png")


def test_safe_filename_missing_extension_appended():
    # ".gitignore" has a dot but no real extension -> ext is appended.
    assert smu.safe_filename(".gitignore", ".png") == ".gitignore.png"


def test_safe_filename_passthrough_sanitized():
    assert smu.safe_filename("good name.png", ".png") == "good_name.png"


# ---- detect_mime_and_extension -------------------------------------------
def test_detect_mime_from_url_extension():
    assert smu.detect_mime_and_extension(b"", "http://x/pic.png") == \
        ("image/png", ".png")


def test_detect_mime_from_content(make_png):
    mime, ext = smu.detect_mime_and_extension(make_png(10, 10), "")
    assert mime == "image/png"


def test_detect_mime_fallback_octet_stream():
    assert smu.detect_mime_and_extension(b"\x00\x01garbage", "") == \
        ("application/octet-stream", ".bin")


# ---- sanitize_url ---------------------------------------------------------
def test_sanitize_url_redacts_sensitive_keys():
    out = smu.sanitize_url("http://x/y?token=abc&auth=z&page=1")
    assert "%5BREDACTED%5D" in out  # url-encoded [REDACTED]
    assert "page=1" in out
    assert "abc" not in out


def test_sanitize_url_keeps_blank_values():
    out = smu.sanitize_url("http://x/y?empty=&page=1")
    assert "empty=" in out


# ---- is_mime_type_allowed -------------------------------------------------
def test_mime_allowed_in_group(isolated_config):
    isolated_config(allowed_mime_groups=["image"])
    assert smu.is_mime_type_allowed("image/png") is True


def test_mime_not_in_group(isolated_config):
    isolated_config(allowed_mime_groups=["image"])
    assert smu.is_mime_type_allowed("text/plain") is False


def test_mime_empty_groups_disallows(isolated_config):
    isolated_config(allowed_mime_groups=[])
    assert smu.is_mime_type_allowed("image/png") is False


# ---- is_file_size_out_of_bounds ------------------------------------------
def test_size_within_bounds(isolated_config):
    isolated_config(filter_file_size={"enabled": True, "min_bytes": 10,
                                      "max_bytes": 1000})
    assert smu.is_file_size_out_of_bounds(500) is False


def test_size_below_min(isolated_config):
    isolated_config(filter_file_size={"enabled": True, "min_bytes": 100,
                                      "max_bytes": 1000})
    assert smu.is_file_size_out_of_bounds(50) is True


def test_size_above_max(isolated_config):
    isolated_config(filter_file_size={"enabled": True, "min_bytes": 10,
                                      "max_bytes": 100})
    assert smu.is_file_size_out_of_bounds(500) is True


def test_size_filter_disabled(isolated_config):
    isolated_config(filter_file_size={"enabled": False, "min_bytes": 10,
                                      "max_bytes": 100})
    assert smu.is_file_size_out_of_bounds(999999) is False


# ---- is_domain_blocked_by_whitelist (current SUBSTRING behavior) ---------
def test_whitelist_empty_allows_all(isolated_config):
    isolated_config(whitelist=[])
    assert smu.is_domain_blocked_by_whitelist("http://any.com/x") is False


def test_whitelist_substring_match_allows(isolated_config):
    isolated_config(whitelist=["example.com"])
    assert smu.is_domain_blocked_by_whitelist("http://www.example.com/x") is False


def test_whitelist_non_match_blocks(isolated_config):
    isolated_config(whitelist=["example.com"])
    assert smu.is_domain_blocked_by_whitelist("http://other.org/x") is True


# ---- is_domain_blacklisted (current SUBSTRING behavior) ------------------
def test_blacklist_empty_allows_all(isolated_config):
    isolated_config(blacklist=[])
    assert smu.is_domain_blacklisted("http://any.com/x") is False


def test_blacklist_substring_match_blocks(isolated_config):
    isolated_config(blacklist=["doubleclick.net"])
    assert smu.is_domain_blacklisted("http://ads.doubleclick.net/x") is True


def test_blacklist_non_match_allows(isolated_config):
    isolated_config(blacklist=["doubleclick.net"])
    assert smu.is_domain_blacklisted("http://good.com/x") is False


# ---- KNOWN DEFECT: matcher uses substring, not regex ---------------------
# See docs/superpowers/specs/2026-07-22-test-suite-design.md.
# These document the *intended* regex behavior; they xpass the day the
# matcher is fixed (strict=True turns an unexpected pass into a failure).
@pytest.mark.xfail(strict=True,
                   reason="matcher uses substring, not regex; default "
                          "blacklist should block ads.doubleclick.net")
def test_blacklist_default_regex_should_block(isolated_config):
    isolated_config()  # default blacklist ships regex entries
    assert smu.is_domain_blacklisted("http://ads.doubleclick.net/img.png") is True


@pytest.mark.xfail(strict=True,
                   reason="matcher uses substring, not regex; a regex "
                          "whitelist entry should allow a matching host")
def test_whitelist_regex_should_allow(isolated_config):
    isolated_config(whitelist=[r".*\.example\.com"])
    assert smu.is_domain_blocked_by_whitelist("http://cdn.example.com/x") is False


# ---- is_valid_image -------------------------------------------------------
def test_is_valid_image_true(make_png):
    assert smu.is_valid_image(make_png(10, 10)) is True


def test_is_valid_image_false(not_an_image):
    assert smu.is_valid_image(not_an_image) is False


# ---- is_image_size_out_of_bounds -----------------------------------------
def test_image_within_pixel_bounds(isolated_config, make_png):
    isolated_config(filter_pixel_dimensions={"min_width": 100, "min_height": 100,
                                             "max_width": 1000, "max_height": 1000})
    assert smu.is_image_size_out_of_bounds(make_png(500, 500)) is False


def test_image_too_small(isolated_config, make_png):
    isolated_config(filter_pixel_dimensions={"min_width": 100, "min_height": 100,
                                             "max_width": 1000, "max_height": 1000})
    assert smu.is_image_size_out_of_bounds(make_png(10, 10)) is True


def test_image_pixel_filter_disabled_via_empty_dict(isolated_config, make_png):
    isolated_config(filter_pixel_dimensions={})
    assert smu.is_image_size_out_of_bounds(make_png(10, 10)) is False


# ---- does_header_match_size ----------------------------------------------
def test_header_none_matches():
    assert smu.does_header_match_size(None, 100, "http://x") is True


def test_header_equal_matches():
    assert smu.does_header_match_size("100", 100, "http://x") is True


def test_header_mismatch():
    assert smu.does_header_match_size("100", 50, "http://x") is False


def test_header_non_integer_is_tolerated():
    assert smu.does_header_match_size("abc", 50, "http://x") is True


# ---- is_directory_traversal_attempted ------------------------------------
def test_traversal_inside_save_dir(isolated_config):
    cfg = isolated_config()
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    inside = (cfg.save_dir / "file.png").resolve()
    assert smu.is_directory_traversal_attempted(inside) is False


def test_traversal_outside_save_dir(isolated_config):
    cfg = isolated_config()
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    outside = Path("C:/Windows/system32/evil.png").resolve()
    assert smu.is_directory_traversal_attempted(outside) is True


# ---- atomic_save ----------------------------------------------------------
def test_atomic_save_writes_file(isolated_config):
    cfg = isolated_config()
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    target = cfg.save_dir / "out.txt"
    smu.atomic_save(b"hello", target, 5)
    assert target.read_bytes() == b"hello"


def test_atomic_save_collision_suffix(isolated_config):
    cfg = isolated_config()
    cfg.save_dir.mkdir(parents=True, exist_ok=True)
    target = cfg.save_dir / "out.txt"
    smu.atomic_save(b"first", target, 5)
    smu.atomic_save(b"second", target, 6)
    assert (cfg.save_dir / "out.txt").read_bytes() == b"first"
    assert (cfg.save_dir / "out_1.txt").read_bytes() == b"second"


# ---- cleanup_temp_file ----------------------------------------------------
def test_cleanup_temp_file_removes(tmp_path):
    p = tmp_path / "temp.bin"
    p.write_bytes(b"x")
    smu.cleanup_temp_file(p)
    assert not p.exists()


def test_cleanup_temp_file_missing_is_noop(tmp_path):
    smu.cleanup_temp_file(tmp_path / "does_not_exist.bin")  # must not raise
