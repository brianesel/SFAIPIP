# Testing

- **Two tiers.** Unit: fast, logic via DI / Stub API, no DML where avoidable. Integration: few, real DML for triggers, sharing (`System.runAs`), bulk 251+, Flow + Apex interaction.
- **Short tests.** One behavior per test, Arrange-Act-Assert with one Act, data from a factory + `@TestSetup`, no logic in tests, `Assert.*` with messages, ≤ ~25 statements.
- **Coverage is a gate, not proof.** Org minimum 75%; per changed class ≥ project minimum (default 85). Never pad.
- **Required categories** follow the ticket: happy + negative always; bulk for triggers/Flows; permission when access changes; regression for migration items.
- **Two independent test sets.** The tester and AI each write cases blind, then align. Each finds what the other misses (domain edge cases vs systematic risks).
- **Suite speed matters.** A fast suite makes real CI possible; slow suites get skipped.
- **Evidence for every result.** A manual case without evidence is not a pass.
