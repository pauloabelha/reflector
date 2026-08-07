# Candidate executor overhead benchmark

Date: 2026-08-03. Host: current local CPU environment. Workload: 32 repeated
small schema-validation candidate tasks, two process workers.

```text
serial_seconds:  0.001542211975902319
process_seconds: 0.011145277007017285
parallel_faster: false
```

For this tiny workload multiprocessing was about 7.2 times slower. The default
candidate execution remains serial, and the generic process threshold is 64
tasks. Experiments may override the threshold, but their run manifest records
the requested/effective mode, workers, and threshold. This measurement is a
local overhead calibration, not a cross-machine performance claim.

