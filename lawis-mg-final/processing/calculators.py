"""
Calculateurs juridiques — calculs déterministes (pas de LLM) fondés sur le
Code du travail marocain (loi 65-99). Chaque résultat référence l'article
applicable, conformément à BNF-01 (toute affirmation doit être fondée).

Ces calculs sont indicatifs : ils appliquent le barème légal minimal et ne
remplacent pas une consultation professionnelle (conventions collectives,
régimes particuliers, jurisprudence peuvent modifier le résultat réel).
"""

HOURLY_RATE_DIVISOR = 191  # heures légales mensuelles moyennes (44h/semaine)

# Barème progressif de l'indemnité de licenciement — Article 53, Code du travail.
_SEVERANCE_TRANCHES = [
    (5, 96),              # années 1 à 5 : 96h de salaire par année
    (5, 144),             # années 6 à 10 : 144h par année
    (5, 192),             # années 11 à 15 : 192h par année
    (float("inf"), 240),  # au-delà de 15 ans : 240h par année
]

# Préavis légal — Article 51, Code du travail.
_NOTICE_PERIOD_TABLE = {
    "employe": [(1, "8 jours"), (5, "1 mois"), (float("inf"), "2 mois")],
    "cadre": [(1, "1 mois"), (5, "2 mois"), (float("inf"), "3 mois")],
}

# Barème mensuel de l'impôt sur le revenu (IR) applicable aux salaires.
# (borne_inf, borne_sup, taux, somme_a_deduire) — valeurs en MAD.
_IR_BRACKETS = [
    (0, 2500, 0.0, 0),
    (2500, 4166.67, 0.10, 250),
    (4166.67, 5000, 0.20, 666.67),
    (5000, 6666.67, 0.30, 1166.67),
    (6666.67, 15000, 0.34, 1433.33),
    (15000, float("inf"), 0.37, 1883.33),
]
_CNSS_RATE = 0.0448
_CNSS_CEILING = 6000
_AMO_RATE = 0.0226
_FRAIS_PRO_RATE = 0.20
_FRAIS_PRO_CEILING = 2500


def calculate_severance_pay(monthly_salary: float, years_of_service: float) -> dict:
    """Indemnité légale de licenciement (Article 53, Code du travail)."""
    if monthly_salary <= 0:
        raise ValueError("Le salaire mensuel doit être positif.")
    if years_of_service < 0:
        raise ValueError("L'ancienneté ne peut pas être négative.")

    hourly_rate = monthly_salary / HOURLY_RATE_DIVISOR
    remaining = years_of_service
    total_hours = 0.0
    breakdown = []
    for tranche_years, hours_per_year in _SEVERANCE_TRANCHES:
        years_in_tranche = min(remaining, tranche_years)
        if years_in_tranche <= 0:
            break
        hours = years_in_tranche * hours_per_year
        total_hours += hours
        breakdown.append({"years_in_tranche": round(years_in_tranche, 2), "hours_per_year": hours_per_year, "hours": round(hours, 2)})
        remaining -= years_in_tranche

    return {
        "monthly_salary": monthly_salary,
        "years_of_service": years_of_service,
        "hourly_rate": round(hourly_rate, 2),
        "total_hours": round(total_hours, 2),
        "total_amount": round(total_hours * hourly_rate, 2),
        "breakdown": breakdown,
        "legal_reference": "Article 53, Code du travail (loi 65-99)",
    }


def calculate_notice_period(category: str, years_of_service: float) -> dict:
    """Préavis légal de licenciement/démission (Article 51, Code du travail)."""
    if category not in _NOTICE_PERIOD_TABLE:
        raise ValueError(f"Catégorie invalide : {category} (attendu : employe, cadre)")
    if years_of_service < 0:
        raise ValueError("L'ancienneté ne peut pas être négative.")

    for threshold, period in _NOTICE_PERIOD_TABLE[category]:
        if years_of_service < threshold:
            return {
                "category": category,
                "years_of_service": years_of_service,
                "notice_period": period,
                "legal_reference": "Article 51, Code du travail (loi 65-99)",
            }


def calculate_net_salary(gross_salary: float) -> dict:
    """
    Estimation du salaire net à partir du brut : CNSS + AMO + IR (barème
    progressif), frais professionnels forfaitaires. Approximation indicative
    — un contrat, une convention collective ou un régime particulier peuvent
    modifier le résultat réel.
    """
    if gross_salary <= 0:
        raise ValueError("Le salaire brut doit être positif.")

    cnss = min(gross_salary, _CNSS_CEILING) * _CNSS_RATE
    amo = gross_salary * _AMO_RATE
    base_after_contributions = gross_salary - cnss - amo
    frais_pro = min(base_after_contributions * _FRAIS_PRO_RATE, _FRAIS_PRO_CEILING)
    taxable_base = max(base_after_contributions - frais_pro, 0)

    ir = 0.0
    ir_rate = 0.0
    for low, high, rate, deduction in _IR_BRACKETS:
        if low <= taxable_base < high or (high == float("inf") and taxable_base >= low):
            ir = max(taxable_base * rate - deduction, 0)
            ir_rate = rate
            break

    net_salary = gross_salary - cnss - amo - ir

    return {
        "gross_salary": gross_salary,
        "cnss": round(cnss, 2),
        "amo": round(amo, 2),
        "frais_professionnels": round(frais_pro, 2),
        "taxable_base": round(taxable_base, 2),
        "ir_rate": ir_rate,
        "ir": round(ir, 2),
        "net_salary": round(net_salary, 2),
        "legal_reference": "Barème IR (Code Général des Impôts) + taux CNSS/AMO en vigueur",
    }
