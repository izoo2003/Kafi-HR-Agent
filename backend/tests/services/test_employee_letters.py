from app.reporting.employee_letters import _a_or_an, rupees_in_words, _salary_breakup
from app.services.employee_letter_service import (
    _parse_vision_json,
    decide_letter_verification,
)


def test_rupees_in_words_sample_package():
    assert rupees_in_words(195_000) == "One Lakh Ninety Five Thousand"
    assert rupees_in_words(150_000) == "One Lakh Fifty Thousand"


def test_salary_breakup_keeps_official_ratio():
    basic, hra, allowance = _salary_breakup(195_000)
    assert (basic, hra, allowance) == (120_000, 45_000, 30_000)
    total = 150_000
    basic, hra, allowance = _salary_breakup(total)
    assert basic + hra + allowance == total


def test_a_or_an_handles_acronyms():
    assert _a_or_an("HR Officer") == "an"
    assert _a_or_an("Sales & Marketing") == "a"
    assert _a_or_an("International Sales") == "an"


def test_parse_vision_json_strips_markdown_fence():
    data = _parse_vision_json(
        '```json\n{"image_readable": true, "has_handwritten_signature": false}\n```'
    )
    assert data["image_readable"] is True
    assert data["has_handwritten_signature"] is False


def test_verify_signed_appointment_letter():
    verified, status, _message = decide_letter_verification(
        "appointment",
        {
            "image_readable": True,
            "detected_document_kind": "appointment letter",
            "looks_like_expected_letter": True,
            "has_handwritten_signature": True,
        },
    )
    assert verified is True
    assert status == "verified"


def test_reject_unsigned_contract():
    verified, status, message = decide_letter_verification(
        "contract",
        {
            "image_readable": True,
            "detected_document_kind": "employment_contract",
            "looks_like_expected_letter": True,
            "has_handwritten_signature": False,
        },
    )
    assert verified is False
    assert status == "no_signature"
    assert "signature" in message.lower()


def test_reject_wrong_letter_type():
    verified, status, message = decide_letter_verification(
        "appointment",
        {
            "image_readable": True,
            "detected_document_kind": "contract",
            "looks_like_expected_letter": True,
            "has_handwritten_signature": True,
        },
    )
    assert verified is False
    assert status == "wrong_type"
    assert "employment contract" in message.lower()


def test_reject_unrelated_document():
    verified, status, _message = decide_letter_verification(
        "contract",
        {
            "image_readable": True,
            "detected_document_kind": "other",
            "looks_like_expected_letter": False,
            "has_handwritten_signature": True,
        },
    )
    assert verified is False
    assert status == "not_letter"


def test_reject_unreadable_image():
    verified, status, _message = decide_letter_verification(
        "appointment",
        {
            "image_readable": False,
            "detected_document_kind": "appointment",
            "looks_like_expected_letter": True,
            "has_handwritten_signature": True,
        },
    )
    assert verified is False
    assert status == "unreadable"


def test_accept_legacy_field_names():
    verified, status, _message = decide_letter_verification(
        "contract",
        {
            "image_readable": "true",
            "looks_like_letter_document": True,
            "has_client_signature": "yes",
        },
    )
    assert verified is True
    assert status == "verified"
