import pytest
from processing.calculators import calculate_severance_pay, calculate_notice_period, calculate_net_salary


def test_severance_pay_within_first_tranche():
    r = calculate_severance_pay(monthly_salary=6000, years_of_service=3)
    # 3 ans × 96h = 288h, taux horaire = 6000/191
    assert r["total_hours"] == 288.0
    assert r["hourly_rate"] == round(6000 / 191, 2)
    assert r["total_amount"] == pytest.approx(288 * (6000 / 191), abs=0.5)
    assert len(r["breakdown"]) == 1


def test_severance_pay_spans_multiple_tranches():
    r = calculate_severance_pay(monthly_salary=6000, years_of_service=8)
    # 5 ans × 96h (tranche 1) + 3 ans × 144h (tranche 2) = 480 + 432 = 912h
    assert r["total_hours"] == 912.0
    assert len(r["breakdown"]) == 2


def test_severance_pay_beyond_fifteen_years_uses_top_rate():
    r = calculate_severance_pay(monthly_salary=5000, years_of_service=20)
    # 5×96 + 5×144 + 5×192 + 5×240 = 480+720+960+1200 = 3360h
    assert r["total_hours"] == 3360.0
    assert len(r["breakdown"]) == 4


def test_severance_pay_rejects_invalid_input():
    with pytest.raises(ValueError):
        calculate_severance_pay(monthly_salary=0, years_of_service=5)
    with pytest.raises(ValueError):
        calculate_severance_pay(monthly_salary=6000, years_of_service=-1)


@pytest.mark.parametrize("category,years,expected", [
    ("employe", 0.5, "8 jours"),
    ("employe", 3, "1 mois"),
    ("employe", 10, "2 mois"),
    ("cadre", 0.5, "1 mois"),
    ("cadre", 3, "2 mois"),
    ("cadre", 10, "3 mois"),
])
def test_notice_period_table(category, years, expected):
    r = calculate_notice_period(category, years)
    assert r["notice_period"] == expected


def test_notice_period_rejects_invalid_category():
    with pytest.raises(ValueError):
        calculate_notice_period("invalide", 3)


def test_net_salary_is_less_than_gross():
    r = calculate_net_salary(6000)
    assert r["net_salary"] < r["gross_salary"]
    assert r["cnss"] > 0
    assert r["amo"] > 0


def test_net_salary_low_income_pays_no_ir():
    r = calculate_net_salary(2500)
    assert r["ir"] == 0


def test_net_salary_cnss_is_capped_above_ceiling():
    r_below = calculate_net_salary(6000)
    r_above = calculate_net_salary(20000)
    # Au-delà du plafond CNSS, la cotisation ne doit plus augmenter.
    assert r_below["cnss"] == r_above["cnss"]


def test_net_salary_rejects_non_positive_input():
    with pytest.raises(ValueError):
        calculate_net_salary(0)
