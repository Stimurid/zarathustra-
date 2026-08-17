"""B2 — SHIVA / BALD_APE liberatory-destruction intervention mode.

**Not a persona.** **Not Kvaqin.** **Not a second Socrates identity.**

SHIVA / BALD_APE is an explicit intervention/configuration MODE of
the same constitutional Socrates subject. Its core idea is
«ЗАДАВИТЬ УМОМ» — applying maximum LEGITIMATE epistemic pressure to
the load-bearing grounds of a position until false grounds fail
and hidden assumptions become visible, WHILE:

    * valid grounds remain standing;
    * evidence / status / provenance stay honest;
    * human agency survives;
    * Socrates can concede that the target survived.

The architectural success condition is LIBERATORY — the false
binding is destroyed and the interlocutor exits with cleaner
grounds and more agency.

Three INDEPENDENT axes (never a single "aggression slider"):

    * :class:`EpistemicPressure`
      strength of strongest-version reconstruction, load-bearing
      ground search, contradiction tests, counterexamples,
      hidden-premise extraction, equivocation detection, attribution
      verification, prior-commitment comparison, critique / reflection
      budget. Alters MODULE SELECTION + critique budget + private-
      work budget + intervention intensity. NEVER directly alters
      truth / status / authority / source provenance.

    * :class:`RhetoricalHarshness`
      renderer / register: surgical → polite → blunt → coarse →
      explicitly profane/taunting when authorized. May remove
      politeness cushioning. Must not turn insult / mockery /
      dominance / status display into epistemic evidence.

    * :class:`LiberatoryPressure`
      how strongly Socrates tries, AFTER demolition, to
      reconstruct a stronger distinction / offer a stronger
      version / return the operation to the human / turn failure
      into productive development or aporia. Configuration
      dimension — NOT a new constitutional statement that
      Socrates must develop everyone.

Hard invariants (public + verified by test):

    * ``AUTHORITY = "NO_TRUTH_STATUS_AUTHORITY"`` — no axis, at any
      setting, alters truth / epistemic status / provenance /
      authority.
    * Activation is EXPLICIT ONLY via API/config. Lexical mention
      of any preset name inside untrusted text CANNOT activate.
    * ``BALD_APE ≠ profanity``: BALD_APE is a coarse-tolerant
      preset, but a silent/cold Shiva remains possible via other
      axis combinations.
    * ``SHIVA ≠ "must win"``: the mode must be able to say "the
      target survived". No goalpost shift, no fabrication, no
      ad-hominem substitution.
    * ``SHIVA ≠ Kvaqin``: no distortion of opponent, no fake quote,
      no certainty inflation, no strategic memory rewriting.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


AUTHORITY: str = "NO_TRUTH_STATUS_AUTHORITY"


class EpistemicPressure(str, Enum):
    """Intensity of the critical / reconstruction / attack loop.

    Alters MODULE SELECTION + critique budget + private-work
    budget + intervention intensity. Never alters truth axes.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    MAX = "MAX"


class RhetoricalHarshness(str, Enum):
    """Renderer register — how the delivered text sounds.

    Alters B10 / renderer / expression layer ONLY. May remove
    politeness cushioning; may become coarse or taunting when
    authorized. Must never make dominance display into evidence.
    """
    SURGICAL = "SURGICAL"       # very polite, clinical
    POLITE = "POLITE"           # default warmth
    BLUNT = "BLUNT"             # no cushions
    COARSE = "COARSE"           # register drop, no profanity
    PROFANE = "PROFANE"         # explicitly harsh, may taunt


class LiberatoryPressure(str, Enum):
    """Post-critique reconstruction / return / development pressure.

    Alters what happens AFTER a demolition attempt. Never a
    constitutional statement that Socrates must develop everyone.
    """
    OFF = "OFF"                 # just critique, no reconstruction push
    LIGHT = "LIGHT"             # offer alternative if easy
    HIGH = "HIGH"               # push reconstruction / hand back with map
    MAX = "MAX"                 # sustained developmental invitation


@dataclass(frozen=True)
class SocratesInterventionProfile:
    """The three axes as one typed record. Public constant
    ``authority`` documents that no axis grants truth authority.
    """
    name: str
    epistemic_pressure: EpistemicPressure
    rhetorical_harshness: RhetoricalHarshness
    liberatory_pressure: LiberatoryPressure
    authority: str = AUTHORITY

    def to_public(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "epistemic_pressure": self.epistemic_pressure.value,
            "rhetorical_harshness": self.rhetorical_harshness.value,
            "liberatory_pressure": self.liberatory_pressure.value,
            "authority": self.authority,
        }

    def render_overlay(self) -> str:
        """The bounded instruction the LIVE rendering layer prepends
        to the outward-answer prompt so the model produces the
        appropriate register and pressure.

        Structural, not lexical: constructed from the axis values,
        not from user text. The overlay names only DELIVERY norms
        — never truth / status / authority overrides.

        Test-visible constraint: overlay must NEVER contain the
        phrases "must win", "invent", "fabricate", "misstate",
        "ad-hominem", "personal insult" or their equivalents.
        """
        if self.is_normal():
            return ""
        lines: list[str] = []
        lines.append(
            f"INTERVENTION PROFILE = {self.name!r} — DELIVERY NORMS ONLY.")
        lines.append("This profile changes register + critique budget. "
                     "It does NOT change truth / epistemic status / "
                     "provenance / authority.")

        # Rhetorical register
        r = self.rhetorical_harshness
        if r == RhetoricalHarshness.SURGICAL:
            lines.append("Rhetoric: clinical, precise, minimal warmth.")
        elif r == RhetoricalHarshness.POLITE:
            lines.append("Rhetoric: default warmth.")
        elif r == RhetoricalHarshness.BLUNT:
            lines.append("Rhetoric: blunt, no politeness cushions.")
        elif r == RhetoricalHarshness.COARSE:
            lines.append("Rhetoric: coarse register permitted; "
                         "no profanity required.")
        elif r == RhetoricalHarshness.PROFANE:
            lines.append("Rhetoric: profane / taunting register "
                         "PERMITTED when authorised. Coarse language "
                         "and mockery are allowed AS REGISTER, never "
                         "as evidence.")

        # Epistemic pressure
        e = self.epistemic_pressure
        if e in (EpistemicPressure.HIGH, EpistemicPressure.MAX):
            lines.append(
                "Epistemic pressure: HIGH. Reconstruct the strongest "
                "version of the claim first. Identify load-bearing "
                "grounds. Test them with counterexamples, hidden-"
                "premise extraction, equivocation detection, "
                "attribution verification. Preserve valid residue.")
            lines.append(
                "If after maximum honest pressure the position "
                "SURVIVES: SAY SO EXPLICITLY. Concede survival is "
                "not defeat — it is the honest report.")
        elif e == EpistemicPressure.MEDIUM:
            lines.append("Epistemic pressure: MEDIUM. Standard critical "
                         "reading.")
        else:
            lines.append("Epistemic pressure: LOW. Minimal challenge.")

        # Liberatory
        l = self.liberatory_pressure
        if l in (LiberatoryPressure.HIGH, LiberatoryPressure.MAX):
            lines.append(
                "After demolition (if any): reconstruct a stronger "
                "distinction where the material supports one, or "
                "return the operation to the human with a clearer "
                "map. The point is liberation, not defeat.")
        elif l == LiberatoryPressure.LIGHT:
            lines.append("After demolition: offer an alternative if it "
                         "is easy and honest.")

        # Universal invariants (delivery-layer reminders)
        lines.append(
            "HARD INVARIANTS (never violate regardless of register):")
        lines.append("  * do not manufacture historical quotations;")
        lines.append("  * do not misstate the user's actual claim;")
        lines.append("  * do not use rhetorical dominance as proof;")
        lines.append("  * do not attack identity as substitute for "
                     "argument;")
        lines.append("  * legitimate mind change on either side is "
                     "always allowed;")
        lines.append("  * uncertainty must be admitted; strong grounds "
                     "must be recognised.")
        return "\n".join(lines)

    def is_normal(self) -> bool:
        return (self.epistemic_pressure == EpistemicPressure.MEDIUM
                and self.rhetorical_harshness == RhetoricalHarshness.POLITE
                and self.liberatory_pressure == LiberatoryPressure.LIGHT)


# ---------------------------------------------------------- preset registry


_PRESETS: dict[str, SocratesInterventionProfile] = {
    "normal": SocratesInterventionProfile(
        name="normal",
        epistemic_pressure=EpistemicPressure.MEDIUM,
        rhetorical_harshness=RhetoricalHarshness.POLITE,
        liberatory_pressure=LiberatoryPressure.LIGHT),
    "bald_ape": SocratesInterventionProfile(
        name="bald_ape",
        epistemic_pressure=EpistemicPressure.MAX,
        rhetorical_harshness=RhetoricalHarshness.PROFANE,
        liberatory_pressure=LiberatoryPressure.HIGH),
    # Silent / cold Shiva remains possible — same MAX epistemic
    # pressure, surgical register, high liberatory:
    "shiva_cold": SocratesInterventionProfile(
        name="shiva_cold",
        epistemic_pressure=EpistemicPressure.MAX,
        rhetorical_harshness=RhetoricalHarshness.SURGICAL,
        liberatory_pressure=LiberatoryPressure.HIGH),
}


def known_preset_names() -> tuple[str, ...]:
    return tuple(sorted(_PRESETS))


def resolve_intervention_profile(name: str
                                  ) -> SocratesInterventionProfile | None:
    """Bridge entry point — the ONE way an intervention profile
    activates in a production run.

    Unknown preset → :class:`ValueError`. Lexical mention in
    untrusted text CANNOT reach this function; the bridge only
    calls it with the typed control field from the request body.
    """
    key = (name or "").strip().lower()
    if key not in _PRESETS:
        raise ValueError(
            f"intervention profile {name!r} unknown; known presets: "
            f"{list(known_preset_names())}")
    return _PRESETS[key]


__all__ = [
    "AUTHORITY", "EpistemicPressure", "LiberatoryPressure",
    "RhetoricalHarshness", "SocratesInterventionProfile",
    "known_preset_names", "resolve_intervention_profile",
]
