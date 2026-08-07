# Reflector-II CPU/GPU evolution plan

The target is GPU-ready semantics, not mandatory GPU residence. Small or
irregular batches stay on CPU. Phase 1 records batch sizes and timings needed
to make that decision empirically.

| Operation | Phase-1 CPU representation | GPU mapping / likely primitive | Batching and synchronization | Expected bottleneck / custom CUDA |
|---|---|---|---|---|
| sensory cell/value facts | contiguous grid and integer fact buffers | elementwise kernels, prefix scan, compaction | batch frames or regions; one barrier before graph ingestion | transfer/launch dominates small ARC frames; no custom CUDA initially |
| connected components / enclosure | deque flood fill, bit masks | parallel labeling, union-find, frontier compaction | batch many frames; iterative frontier barriers | tiny irregular grids favor CPU; custom kernel only if perception dominates large batches |
| signature extraction | sorted coordinate arrays and hashes | segmented sort/reduction, prefix scan, hash | batch components; synchronize before index probe | variable segment sizes; library sort first |
| postings retrieval | CPU hash maps to packed postings | GPU hash lookup or sorted-key binary search, gather | group queries by index generation; stable graph read-only | random memory and small postings; likely CPU until many simultaneous workspaces |
| pattern filtering | integer `(head,arity,slot)` arrays | gather, comparison masks, prefix scan/compaction | batch same atom/arity; barrier per staged filter | divergent patterns; no custom kernel before bucket-size evidence |
| binding verification | bounded substitution tables | bucket by pattern shape, gather/scatter, segmented reduction | one kernel per common pattern signature; rare patterns CPU | register pressure/divergence; specialized kernels may eventually help proven common shapes |
| activation propagation | frontier IDs + stable CSR + delta adjacency | CSR gather/scatter; sparse SpMV for large homogeneous batches; frontier compaction | process stable generation and small delta separately, reduce together; barrier per round | atomic contention and sparse irregularity; CUB-style sort/reduce before custom CUDA |
| evidence delta reduction | `(target,delta-kind,value)` records | radix sort, segmented reduction, scatter | batch full cycle; integer counters allow deterministic reduction | PCIe cost for small batches; no custom CUDA |
| candidate scoring | SoA feature columns | vectorized gather and fused arithmetic | batch by work-item kind; top-k at end | memory bandwidth; framework kernel sufficient |
| top-k/pruning | CPU heap/stable sort | radix/select top-k, segmented top-k, frontier compaction | one segment per workspace/queue; synchronization publishes frontier | deterministic tie-breaking; use library primitives first |
| composition pair generation | active binding indices | join-like sort by bound entity, segmented Cartesian products under caps | batch workspaces and shared-binding keys; compact before CPU commit | output explosion, controlled by budgets; CPU owns structural mutation |
| decomposition-DAG evaluation | occurrence CSR plus compact child/owner variable maps | topological frontier compaction, gather, segmented reduction | batch equal-depth occurrences; barrier only between dependency frontiers | small/irregular DAGs stay CPU; no custom kernel until many schemas share shapes |
| canonicalization / alpha-renaming | CPU flat term arrays and hash maps | segmented sort and structural hashing are possible | GPU may pre-sort large candidate batches; CPU verifies and commits | dependency chains and small bodies favor CPU; custom CUDA unlikely |
| hash-cons lookup | CPU canonical hash table across stable+delta | GPU read-only cuckoo/sorted lookup for stable table | query batch, return hits/misses; CPU serializes misses | dynamic insertion belongs on CPU; no custom kernel initially |
| transition correspondence | signature buckets, bounded candidate arrays | batched pair scoring via gather and reductions | batch entity pairs across transitions; top-k then CPU anti-unify | candidate sparsity; GPU only at many simultaneous environments |
| morphism scoring | SoA preservation/change/evidence columns | gather, segmented reductions, top-k | bucket by morphism body shape/action; one reconcile barrier | same as candidate scoring; fuse only after profile |
| sparse composition of mappings | bounded CPU joins | sparse SpGEMM/GraphBLAS only if mapping batches become matrix-shaped | operate within active candidate subgraphs, never whole graph | symbolic unification is irregular; SpGEMM is not assumed superior |
| persistence compaction | CPU external sort/dedupe to CSR | radix sort, prefix scan, COO-to-CSR | offline/cold transaction; publish new generation at barrier | memory volume; library primitives sufficient |

## Memory and numeric policy

Term/schema/link IDs are `int32` until a store generation exceeds the safe ID
range; offsets are `int64`. Relation/predicate IDs may be `uint16` only after a
checked vocabulary bound, otherwise `int32`. Evidence counters are integer.
Activation and weights begin as `fp32`; `fp16` is allowed only after parity and
stability tests because underflow near the active threshold changes search.

The stable CSR generation, term arrays, and index tables are long-lived device
buffers. Delta rows use append buffers and may stay CPU-side while small; GPU
expansion processes stable and delta portions independently. Host/device
transfer volume, kernel launch count, active rows, and occupancy are measured
per operation.

## Concurrency and determinism

CPU threads or processes generate immutable work batches against one graph
generation. GPU streams may overlap retrieval, scoring, and evidence reduction
when dependencies allow. Fine-grained locks are forbidden in hot arrays;
append buffers and bulk publication are used. A cycle barrier stable-sorts
results by deterministic keys before CPU graph mutations.

Floating reduction order can otherwise change thresholds. The initial GPU
prototype must offer a deterministic mode using stable sort and fixed-order
segmented reductions; a faster nondeterministic mode may exist only with
reported decision-parity measurements. Integer evidence updates remain exact.

## Decision gates

An operation moves to GPU only when profiles show enough work to amortize
transfer and launch, the active-frontier implementation is already correct,
CPU/GPU canonical output parity passes, and memory use fits without densifying
the graph. Custom CUDA is considered only after PyTorch/CuPy/CUB/cuSPARSE or a
GraphBLAS-style primitive demonstrably dominates end-to-end time for that
operation. Sparse SpMV, SpMM, or SpGEMM is a candidate implementation detail,
not the architecture.
