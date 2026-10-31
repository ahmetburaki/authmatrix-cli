# Synthetic compatibility corpus

These documents describe the public matrix/evidence contracts. They contain no
live credentials, response contents or observations of external systems. The
loopback origin is illustrative; loading these fixtures sends no requests.
Matrix fingerprints are fixed, so accidental contract/fixture drift breaks
comparison tests instead of silently regenerating expectations.

- `matrix-status.json` and `matrix-asserted.json` are version-1 inputs.
- `report-v1.json` and `report-v2.json` are failing legacy baselines.
- `report-v3-status.json` and `report-v3-asserted.json` are passing current reports
  for the corresponding unchanged matrices.
- `report-v2-response-error.json` and `report-v3-timeout.json` exercise error
  representations that cannot prove a fix.

The schema suite checks these files against JSON Schema and runtime validation,
then verifies fail-to-pass comparisons and reversed regressions. Generated reports
from a disposable loopback peer are checked separately.
