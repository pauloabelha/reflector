# Evidence-consistent live goal revision v4 status

- Frozen after v3's semantic-success/control-grounding failure.
- The only new semantic input is exact R2 criticism derived from the already
  visible calibration rows. No port is silently repaired.

## Fresh run 1 — valid revision FAIL

- R2 returned both exact witnesses, but Qwen repeated the contradicted ports
  (`controlled=f05`, translating `im00`) instead of copying the unique grounded
  alternatives (`f02`, zero-effect `im04`). No proposal reached control.
- This exposed a division-of-labor error: exact controlled and intervention
  ports are R2 grounding responsibilities. v5 preserves Qwen semantics and
  rejected-port provenance while resolving only uniquely grounded OPEN ports.
