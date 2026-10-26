# Encrypted Image Flooding-Network Simulation — Project Spec

**Course context:** Computer Networks Lab
**Purpose of this document:** Single source of truth for an AI coding agent (Claude Code, Codex, etc.) implementing this project. Read this file in full before writing any code. Follow the phases in order. Do not skip a verification step.

---

## 1. System Overview

Five logical nodes simulate a flooding-based network carrying an encrypted image, split into fragments.

| Node | Role |
|---|---|
| **A (Sender)** | Loads image → bytes → encrypts → splits into 1024-byte fragments → attaches header → floods to neighbors |
| **B, C, D (Intermediate)** | Read header only → enforce TTL / loop (duplicate) tracking → forward immediately, no decryption |
| **E (Receiver)** | Collects fragments → reorders by `chunk_sequence` → decrypts → saves/renders image |

Topology: `A -- B -- E`, `A -- C -- E`, `A -- D -- E` (A and E each connect to all three intermediates; B/C/D are not connected to each other). This gives genuine flooding behavior (multiple paths, duplicate arrivals) without full mesh complexity. Confirm this topology with the instructor's brief if one exists; otherwise treat it as the default.

Transport for the simulation: use **Python + `asyncio` or `multiprocessing` with local sockets (`localhost`, distinct ports per node)**, so the "network" is real IPC, not just function calls — this is what makes it a networks lab project rather than a scripting exercise. Each node is its own process/script.

---

## 2. Packet Header Format

Fixed-size header, prepended to every fragment, defined once in `common/packet.py` and imported everywhere (never redefined per-node — this is a common source of bugs).

```
| Field            | Type   | Size (bytes) | Notes                                |
|------------------|--------|---------------|---------------------------------------|
| magic            | bytes  | 4             | b"IMGF" — sanity check                |
| src_id           | uint8  | 1             | originating node id (A=0)             |
| dest_id          | uint8  | 1             | final receiver id (E=4)               |
| packet_id        | uint32 | 4             | unique id for this fragment (dedup)   |
| chunk_sequence   | uint16 | 2             | order index of this fragment          |
| total_chunks     | uint16 | 2             | total fragment count for this image   |
| ttl               | uint8  | 1             | decremented at each hop               |
| payload_length   | uint16 | 2             | length of the encrypted payload       |
```

Total header = 17 bytes, packed with `struct`. Payload = up to 1024 bytes of ciphertext using the custom Bit-Shuffle algorithm.

Serialization: `struct.pack("!4sBBIHHBH", ...)` — network byte order, explicit format string, unit-tested independently in Phase 1.

---

## 3. Folder Structure

```
cn-flood-image/
├── PROJECT_SPEC.md              # this file
├── README.md                    # short human-facing summary + run instructions
├── requirements.txt
├── common/
│   ├── __init__.py
│   ├── packet.py                # header pack/unpack, dataclass Packet
│   ├── crypto.py                # encrypt_bytes(), decrypt_bytes() — Custom Bit-Shuffle algorithm
│   └── config.py                # ports, node ids, topology map, TTL default, fragment size
├── nodes/
│   ├── sender_a.py
│   ├── intermediate_bcd.py      # single parametrized script, launched 3x (B/C/D) with --id
│   └── receiver_e.py
├── assets/
│   └── input_image.png          # sample test image (small, <200KB)
├── output/
│   └── (received_image.png written here at runtime — gitignored)
├── tests/
│   ├── test_packet.py           # pack/unpack round-trip
│   ├── test_crypto.py           # encrypt/decrypt round-trip
│   ├── test_fragmentation.py    # split + reassemble byte-for-byte
│   └── test_integration.py      # spins up all 5 nodes, runs full flow, diffs output image
├── logs/
│   └── (per-node .log files written at runtime — gitignored)
└── docs/
    ├── design_notes.md          # architecture diagram + design decisions (for report)
    └── screenshots/             # for lab report submission
```

---

## 4. Build Phases

Work through these strictly in order. **Do not start Phase N+1 until Phase N's verification step passes.**

### Phase 0 — Scaffolding
- Create folder structure above, `requirements.txt` (e.g. `pycryptodome`, `pillow`), empty stub files.
- `common/config.py`: define `NODE_PORTS`, `TTL_DEFAULT = 8`, `FRAGMENT_SIZE = 1024`, `AES_KEY` (fixed for the lab — note in README this is a simulation key, not production-secure).
- **Verify:** `python -c "import common.config"` runs with no error.

### Phase 1 — Packet format
- Implement `common/packet.py`: a `Packet` dataclass + `pack()`/`unpack()` using the header table in §2.
- `tests/test_packet.py`: construct a packet, pack it, unpack it, assert every field round-trips exactly, including edge values (ttl=0, chunk_sequence=0, max payload).
- **Verify:** `pytest tests/test_packet.py -v` — all pass.
- **Stop condition for this phase:** if round-trip fails, do not proceed — a header bug will silently corrupt every later phase.

### Phase 2 — Crypto
- Implement `common/crypto.py`: `encrypt_bytes(data: bytes) -> bytes` and `decrypt_bytes(data: bytes) -> bytes` using a custom Bit-Shuffle symmetric cipher.
- `tests/test_crypto.py`: encrypt/decrypt round-trip on random byte strings of varying length (0, 1, 1023, 1024, 100000 bytes).
- **Verify:** `pytest tests/test_crypto.py -v` — all pass, decrypted output byte-identical to input.

### Phase 3 — Fragmentation & reassembly (pure logic, no networking yet)
- Add `fragment(data: bytes, size=1024) -> list[bytes]` and `reassemble(fragments: dict[int, bytes], total: int) -> bytes` to `common/packet.py` or a new `common/fragment.py`.
- `tests/test_fragmentation.py`: fragment a real image's encrypted bytes, shuffle the fragment order, reassemble, assert byte-identical to original.
- **Verify:** round-trip test passes on `assets/input_image.png`.

### Phase 4 — Sender (Node A)
- `nodes/sender_a.py`: load image → bytes → `encrypt_bytes` → `fragment` → wrap each in a `Packet` (correct header fields) → open sockets to B, C, D → send every fragment to **all** neighbors (flood).
- Log every send: `packet_id`, `chunk_sequence`, `dest`.
- **Verify:** run sender against a stub receiver (`nc -l` or a throwaway script) and confirm the exact expected number of packets (`total_chunks × 3 neighbors`) arrive with well-formed headers.

### Phase 5 — Intermediate nodes (B, C, D)
- `nodes/intermediate_bcd.py`, parametrized by `--id`: listen on its port, on each received packet:
  1. Unpack header only (never touch payload/decrypt).
  2. Check `packet_id` against a local seen-set — if already seen, **drop** (loop/duplicate prevention).
  3. Decrement `ttl`; if `ttl == 0`, drop and log.
  4. Otherwise forward unmodified (payload untouched) to E, and re-pack with decremented ttl.
- **Verify:** unit-style test with a mock incoming packet stream containing duplicates and a ttl=0 packet; assert dedup and TTL-drop both work before touching real sockets.

### Phase 6 — Receiver (Node E)
- `nodes/receiver_e.py`: listen on its port(s) from B, C, D → on each packet, dedup by `packet_id` → store payload indexed by `chunk_sequence` → once `len(received) == total_chunks`, call `reassemble` → `decrypt_bytes` → write to `output/received_image.png`.
- **Verify:** feed it a manually constructed set of out-of-order, duplicated fragments and confirm the output file is written only once, with the correct byte content.

### Phase 7 — Full integration
- `tests/test_integration.py`: launch all 5 node processes (or asyncio tasks) programmatically, run the full pipeline against `assets/input_image.png`, wait for `output/received_image.png`, then:
  - Assert the output file exists.
  - Assert `hashlib.sha256(output_bytes) == hashlib.sha256(input_bytes)`.
  - Assert the image opens correctly with `PIL.Image.open` (not corrupted).
- **Verify:** `pytest tests/test_integration.py -v` passes end-to-end, and manually open `output/received_image.png` to visually confirm it matches the source.
- **This is the primary stop condition for "done."** Do not consider the project complete until this test passes reliably across at least 3 consecutive runs (flooding introduces race conditions — flakiness here is a real bug, not noise).

### Phase 8 — Report artifacts
- `docs/design_notes.md`: architecture diagram (topology), header format table, sequence diagram of one fragment's journey A→B→E and A→C→E (showing duplicate arrival + drop at E).
- Screenshots of logs showing: flooding fan-out, a TTL drop, a duplicate drop, successful reassembly.
- **Verify:** cross-check every claim in `design_notes.md` against actual log output — don't describe behavior that isn't in the logs.

---

## 5. Global Stop Conditions

Halt and flag to the user (don't guess/improvise past these) if:
- A phase's verification step fails after 2 genuine fix attempts — report the failure and root-cause hypothesis instead of proceeding to the next phase.
- The topology or header format needs to diverge from this spec to satisfy an instructor requirement not captured here.
- `output/received_image.png` reassembles correctly on some runs but not others (indicates a concurrency/ordering bug — must be root-caused, not silenced with a retry loop).
- Any node would need to decrypt payloads at B/C/D to make something work — this violates the stated design (intermediates never hold the private key) and signals a design misunderstanding, not a valid fix.

## 6. Non-Goals (explicitly out of scope)
- No real network (no actual multi-machine deployment) — localhost sockets are sufficient and expected.
- No routing optimization/shortest-path logic — pure flood is intentional.
- No production-grade key management — a hardcoded/shared symmetric key is acceptable for a lab simulation; note this explicitly in the report as a simplification.
- No GUI required unless explicitly requested later.

## 7. Definition of Done
- [ ] All unit tests (`packet`, `crypto`, `fragmentation`) pass.
- [ ] Integration test passes 3/3 consecutive runs.
- [ ] Logs clearly show: flooding, TTL decrement/drop, duplicate detection/drop, in-order reassembly at E.
- [ ] `docs/design_notes.md` complete with diagram + header table.
- [ ] `README.md` has exact run commands (how to start B, C, D, E, then A) for a grader to reproduce.