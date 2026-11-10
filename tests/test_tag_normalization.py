from services.import_utils import normalize_tags, invalid_tag_reason


def test_spaces_and_punctuation_are_normalized_without_splitting_model():
    tags = normalize_tags(["#статор_DT W1001", "статор/DT-W1001"])
    assert tags == ["#статор_DT_W1001", "#статор_DT_W1001"]


def test_normalized_tag_passes_character_validation():
    tag = normalize_tags(["#двигатель DT W1001"])[0]
    assert tag == "#двигатель_DT_W1001"
    assert invalid_tag_reason(tag) is None


def test_overlength_tag_is_not_silently_truncated():
    tag = normalize_tags(["#" + "а" * 31])[0]
    assert len(tag) == 32
    assert "长度" in (invalid_tag_reason(tag) or "")


def test_risk_check_false_is_blocked_from_save():
    from services.listing_rules import validate_risk_check
    import pytest
    with pytest.raises(ValueError, match="风险检查未通过"):
        validate_risk_check({"risk_check": {"passed": False}})

def test_risk_check_true_is_allowed():
    from services.listing_rules import validate_risk_check
    result = {"risk_check": {"passed": True, "issues": []}}
    assert validate_risk_check(result) is result
