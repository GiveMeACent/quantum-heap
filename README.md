# quantum-heap

A Qiskit research prototype for checking the **max-heap property** with quantum circuits and searching for violations using **Grover's algorithm**. It provides two interchangeable memory-access implementations within the `QuantumHeap` class.

## Requirements

Python, Qiskit, Qiskit Aer, and NumPy:

```bash
python -m pip install qiskit qiskit-aer numpy
```

## Memory access

- **`circuit` (default):** implements a reversible address-to-value lookup using controlled gates, without an explicit quantum memory register.
- **`bit`:** encodes the heap in a register of qubits and selects words with address-controlled cyclic rotations. The value is copied into the output using CNOT gates, then the rotation is undone to restore the memory.

The bit-based approach adapts **controlled cyclic rotations from published research**, not a new rotation technique proposed by this project. See [Cantone et al., *Quantum LCS in Practice: Circuits, Optimizations, and Evaluation* (HPDC 2026)](https://doi.org/10.1145/3806645.3816161), the paper used as a reference for this implementation. For the construction of controlled cyclic-rotation gates themselves, see [Pavone and Viola, *The Quantum Cyclic Rotation Gate* (2024)](https://doi.org/10.1007/s42979-024-03141-4). This project uses Qiskit's `PermutationGate` to implement the rotations.

The experiments use complete binary heaps with the specific shape `2 ** (bits - 1) - 1`, strictly positive values, and the following configurations:

| `bits` | Heap elements | Search indices | Bit-memory words |
| --- | ---: | --- | ---: |
| 3 | 3 | 0, 1 | 5 |
| 4 | 7 | 0, 1, 2, 3 | 9 |

Only `bits - 2` address qubits receive Hadamard gates. The additional bit-memory words hold zero so that reads of nonexistent children return **zero**, rather than wrapping to real heap elements. This guarantee applies to the addresses used by these experiments; larger addresses may wrap cyclically. The verifier currently uses **strict `>`** comparisons, so equal parent-child values are not treated as satisfying the property.

## Usage

```python
from heap import QuantumHeap

values = [7, 6, 2, 4, 3, 1, 5]
heap = QuantumHeap(values, bits=4, access_mode="circuit")
verifier = heap.property_verifier()
search = heap.grover_search()

bit_heap = QuantumHeap(values, bits=4, access_mode="bit")
```

Run the thesis example with circuit-based access:

```bash
python main.py --access-mode circuit
```

## Tests

From the directory containing `heap.py`:

```bash
python -m unittest discover -s test -p "test_*.py" -v
```

The suite covers three 3-bit scenarios (no violation, one failed comparison, two failed comparisons at the root), four 4-bit marked-node counts (`M=0,1,2,3`), and the three original 4-bit thesis examples. Here, `M` counts **marked parent indices**, not failed comparisons.

Bit-mode simulation is opt-in via `RUN_BIT_SIMULATIONS=1`. On Linux/macOS, run all **3-bit** comparisons with:

```bash
RUN_BIT_SIMULATIONS=1 python -m unittest discover -s test -p "test_*3bit.py" -v
```

For **4-bit bit-mode access tests only**, without full Grover simulation:

```bash
RUN_BIT_SIMULATIONS=1 python -m unittest discover -s test -p "test_*4bit.py" -k bit_access -v
```

Full **4-bit Grover with bit-based memory uses 64 qubits** and exceeds the 63-qubit target limit reported by the tested Aer configuration. It is therefore intentionally excluded from the recommended test commands.
