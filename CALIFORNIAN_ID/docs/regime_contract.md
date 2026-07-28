# Regime Contract

`critique_regime` and `variation_regime` are runtime contracts, not mood labels.

`critique_regime` controls:
- preference for `pressure` operations over `stabilize`
- whether cost exposure should happen before defense
- how strongly the system biases toward steelman vs direct attack
- what directness hint is passed into persona prompts

`variation_regime` controls:
- how much non-canonical routing is rewarded
- penalties for repeating the same operation, class, or 3-step trajectory
- whether class-switching is preferred
- whether the router may break canonical SOP when relevance is preserved

Observable evidence:
- every route event records `canonical_operation`, `selected_operation`, `selected_class`, `recent_operations`, `recent_classes`, and per-candidate scores
- every run completion records `regime_metrics`
- persona prompts receive `routing_contract` plus regime hints

Current metrics:
- `operation_repeat_rate`
- `class_repeat_rate`
- `trajectory_repeat_rate`
- `noncanonical_selection_rate`
- `pressure_selection_rate`
