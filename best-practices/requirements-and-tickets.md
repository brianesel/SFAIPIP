# Requirements and tickets

- **Requirements:** one need per `REQ-nnn`, with role, business reason, Given/When/Then, MoSCoW and a source. Version the register; changes only via CR.
- **Breakdown:** REQ → Epic (process/module) → Story (one visible behavior) → Task (one technical unit).
- **Before creating a ticket:** search for repeats and in-flight work (≥ 3 angles, include closed). A repeat is updated, never duplicated.
- **Challenge before writing:** why this ticket, why not merge, who decided.
- **Structure:** fixed 5-section body + structured fields (`../guardrails/schemas/ticket-schema.yaml`). Every claim sourced.
- **Exact names:** metadata API names as they exist, marked existing/new. Invented names are the most common AI defect.
- **Change control:** size by rule, decider by size, re-baseline after approval, keep rejected CRs.
