from app.reporting.employee_letters import _a_or_an, rupees_in_words, _salary_breakup


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
