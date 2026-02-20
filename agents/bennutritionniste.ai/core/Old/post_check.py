from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any


class GuardDecision(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    SANITIZE = "sanitize"   # optional: redact parts (here we'll mostly BLOCK)


@dataclass
class GuardResult:
    decision: GuardDecision
    reasons: List[str]
    matched_patterns: List[str]
    safe_answer: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


SAFE_FALLBACK_FR = """Je peux fournir de l’information générale à visée éducative,
mais je ne peux pas donner de recommandations, de chiffres cibles, d’exemples de menus,
ni répondre à des situations personnelles ou cliniques.

Pour ce type de question, consulte un professionnel de la santé qualifié (ou un diététiste-nutritionniste).
Ne modifie pas un traitement sans avis médical. En cas d’urgence, contacte les services d’urgence.
"""

# Patterns are intentionally explainable (auditable). Tune as needed.
OUTPUT_PATTERNS_FR = {
    # Numerical targets / dosages / quantities
    "numeric_targets_or_dosage": [
        r"\b\d+(\,\d+)?\s*(kcal|calories)\b",
        r"\b\d+(\,\d+)?\s*(mg|g|mcg|µg)\b",
        r"\b\d+(\,\d+)?\s*(g\/kg|mg\/kg)\b",
        r"\b\d+\s*(tasses|cups?)\b",
        r"\b\d+\s*(fois par jour|x\/jour|x par jour|\/jour)\b",
        r"\b(0,\d+|0\.\d+)\s*(g\/kg|mg\/kg)\b",
    ],

    # Meal plans / menus / day structure
    "meal_plan": [
        r"\bvoici un exemple de menu\b",
        r"\bmenu\b.*\b(journ[ée]e|jour)\b",
        r"\bpetit[- ]d[eé]jeuner\b",
        r"\bd[eé]jeuner\b",
        r"\bd[iî]ner\b",
        r"\bcollation(s)?\b",
        r"\bplan alimentaire\b",
        r"\bplan de repas\b",
        r"\bexemple de repas\b",
    ],

    # Prescriptive / directive language (strong imperatives)
    "prescriptive_language": [
        r"\btu devrais\b",
        r"\btu dois\b",
        r"\bil faut\b",
        r"\bje te conseille\b",
        r"\bje recommande\b",
        r"\bprends?\b\s+\w+",
        r"\barr[êe]te\b",
        r"\b(augmente|r[eé]duis|supprime)\b",
        r"\bconsomme\b",
        r"\b[ée]vite\b",
        r"\bobjectif\b.*\b(kcal|calories|g\/kg|mg)\b",
    ],

    # Personalized claims (talking about "your case" with advice)
    "personalized_framing": [
        r"\bdans ton cas\b",
        r"\bpour toi\b",
        r"\bselon ton profil\b",
        r"\bvu que tu\b",
        r"\bavec ton poids\b",
        r"\bavec ton âge\b",
    ],

    # Clinical advice (high-level filter: not perfect, but useful)
    "clinical_advice": [
        r"\b(diabetes|diab[eè]te|hypertension|insuline|metformine|statine)\b",
        r"\btraitement\b",
        r"\bposologie\b",
        r"\bdiagnostic\b",
        r"\bprescri(s|re)\b",
    ],
}


def _find_matches(text: str, pattern_list: List[str]) -> List[str]:
    hits = []
    for pat in pattern_list:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return hits


def output_guard_fr(answer: str) -> GuardResult:
    """
    Post-check the LLM answer.
    If unsafe patterns are detected, block and replace with SAFE_FALLBACK_FR.
    """
    matched_patterns: List[str] = []
    reasons: List[str] = []

    for category, pats in OUTPUT_PATTERNS_FR.items():
        hits = _find_matches(answer, pats)
        if hits:
            matched_patterns.extend(hits)

            if category == "numeric_targets_or_dosage":
                reasons.append("Contains numeric targets / dosages / quantities.")
            elif category == "meal_plan":
                reasons.append("Contains meal plan / menu-like structure.")
            elif category == "prescriptive_language":
                reasons.append("Contains prescriptive or directive language.")
            elif category == "personalized_framing":
                reasons.append("Contains personalized framing.")
            elif category == "clinical_advice":
                reasons.append("Contains clinical advice language.")

    # Decision policy:
    # BLOCK if any high-risk category appears.
    if reasons:
        return GuardResult(
            decision=GuardDecision.BLOCK,
            reasons=reasons,
            matched_patterns=matched_patterns,
            safe_answer=SAFE_FALLBACK_FR,
            metadata={"policy": "block_on_any_match"}
        )

    return GuardResult(
        decision=GuardDecision.PASS,
        reasons=[],
        matched_patterns=[],
        safe_answer=None,
        metadata={"policy": "pass"}
    )


# Example integration:
def answer_user_with_postcheck(raw_answer: str):
    """
    1) Call LLM (assuming refusal_engine already passed).
    2) Post-check answer. If blocked, return fallback.
    """

    guard = output_guard_fr(raw_answer)
    if guard.decision == GuardDecision.BLOCK:
        return {
            "answer": guard.safe_answer,
            "blocked": True,
            "guard_reasons": guard.reasons,
            "guard_matches": guard.matched_patterns,
        }

    return {
        "answer": raw_answer,
        "blocked": False,
        "guard_reasons": [],
        "guard_matches": [],
    }
