from processing.classifier import classify


def test_classifies_travail_domain():
    r = classify("Le salarié a droit à une indemnité de licenciement selon le code du travail.")
    assert r.domain == "travail"
    assert r.confidence > 0


def test_classifies_fiscal_domain():
    r = classify("La TVA est fixée à 20% pour les prestations de services selon le CGI.")
    assert r.domain == "fiscal"


def test_classifies_societes_domain():
    r = classify("La société anonyme doit disposer d'un capital minimum de 300 000 dirhams.")
    assert r.domain == "societes"


def test_classifies_donnees_personnelles_domain():
    r = classify("Le responsable du traitement doit déclarer les traitements de données personnelles à la CNDP.")
    assert r.domain == "donnees_personnelles"


def test_no_keyword_match_falls_back_to_divers():
    r = classify("Bonjour, comment allez-vous aujourd'hui ?")
    assert r.domain == "divers"
    assert r.confidence == 0.0


def test_short_acronym_does_not_match_inside_unrelated_word():
    """Régression : 'IS'/'IR' (mots-clés fiscal) ne doivent pas matcher par
    sous-chaîne dans 'préavis' / 'secrétaire' — bug corrigé par la limite de
    mot (\\b) dans la classification (cf. processing/classifier.py)."""
    r = classify("Quel est le délai de préavis légal en cas de démission d'une secrétaire ?")
    assert r.domain != "fiscal"
    assert r.domain == "travail"


def test_word_boundary_still_matches_acronym_as_standalone_word():
    r = classify("Le taux de TVA applicable est de 20%.")
    assert r.domain == "fiscal"
