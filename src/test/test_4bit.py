import unittest

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator

from heap import QuantumHeap


BITS = 4
SEARCH_SIZE = 2 ** (BITS - 2)
HEAP_SIZE = 2 ** (BITS - 1) - 1
SHOTS = 1024
SEED = 42
TOLERANCE = 0.10


class TestGrover4Bit(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.simulator = AerSimulator(method="matrix_product_state")

  def _counts(self, circuit):
    compiled = transpile(circuit, self.simulator, optimization_level=0)
    result = self.simulator.run(
        compiled, shots=SHOTS, seed_simulator=SEED
    ).result()
    return result.get_counts()

  @staticmethod
  def _measure_index(circuit, addresses, classical):
    for offset, qubit in enumerate(addresses[2:BITS]):
      circuit.measure(qubit, classical[BITS - 3 - offset])

  def _check_oracle(self, heap, expected_violations):
    addresses = QuantumRegister(3 * BITS, "address")
    values = QuantumRegister(3 * BITS + 3, "values")
    output = ClassicalRegister(BITS - 1, "oracle")
    circuit = QuantumCircuit(addresses, values, output)

    circuit.h(addresses[2:BITS])
    circuit.compose(heap.property_verifier(
        addresses, values), inplace=True)
    self._measure_index(circuit, addresses, output)
    circuit.measure(values[-1], output[BITS - 2])

    observed = {index: set() for index in range(SEARCH_SIZE)}
    for bitstring in self._counts(circuit):
      index = int(bitstring[1:], 2)
      flag = int(bitstring[0])
      observed[index].add(flag)

    for index in range(SEARCH_SIZE):
      expected_flag = 0 if index in expected_violations else 1
      self.assertEqual(observed[index], {expected_flag})

  def _check_case(self, label, vector, expected_violations, expected_distribution):
    self.assertEqual(len(vector), HEAP_SIZE)
    self.assertTrue(all(0 < value < 2**BITS for value in vector))

    pairs = {
        (parent, child)
        for parent in range(SEARCH_SIZE)
        for child in (2 * parent + 1, 2 * parent + 2)
        if vector[parent] <= (vector[child] if child < len(vector) else 0)
    }
    classical_violations = {parent for parent, _ in pairs}
    self.assertEqual(classical_violations, expected_violations)

    heap = QuantumHeap(vector, BITS)
    self._check_oracle(heap, expected_violations)

    addresses = QuantumRegister(3 * BITS, "address")
    values = QuantumRegister(3 * BITS + 3, "values")
    phase = QuantumRegister(1, "phase")
    output = ClassicalRegister(BITS - 2, "index")
    circuit = QuantumCircuit(addresses, values, phase, output)
    circuit.compose(heap.grover_search(addresses, values), inplace=True)
    self._measure_index(circuit, addresses, output)

    counts = self._counts(circuit)
    frequencies = {
        index: counts.get(format(index, f"0{BITS - 2}b"), 0) / SHOTS
        for index in range(SEARCH_SIZE)
    }
    print(
        f"\n[4 bit] {label} | array={vector} | "
        f"confronti violati={len(pairs)} | "
        f"nodi marcati={sorted(expected_violations)}"
    )
    print(f"        Distribuzione Grover: {frequencies}")

    self.assertEqual(set(expected_distribution), set(range(SEARCH_SIZE)))
    for index, expected_probability in expected_distribution.items():
      self.assertAlmostEqual(
          frequencies[index], expected_probability, delta=TOLERANCE
      )

  def test_01_heap_valido(self):
    self._check_case(
        "M=0",
        [15, 14, 13, 12, 11, 10, 9],
        set(),
        {0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25},
    )

  def test_02_una_violazione(self):
    self._check_case(
        "M=1",
        [6, 7, 5, 4, 3, 2, 1],
        {0},
        {0: 1.0, 1: 0.0, 2: 0.0, 3: 0.0},
    )

  def test_03_due_violazioni(self):
    self._check_case(
        "M=2",
        [7, 3, 2, 4, 6, 1, 5],
        {1, 2},
        {0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25},
    )

  def test_04_tre_violazioni(self):
    self._check_case(
        "M=3",
        [2, 3, 4, 5, 6, 7, 8],
        {0, 1, 2},
        {0: 0.0, 1: 0.0, 2: 0.0, 3: 1.0},
    )

  def test_05_tesi_heap_valido(self):
    self._check_case(
        "Tesi: heap valido",
        [7, 6, 5, 4, 3, 2, 1],
        set(),
        {0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25},
    )

  def test_06_tesi_violazione_nodo_2(self):
    self._check_case(
        "Tesi: violazione nel nodo 2",
        [7, 6, 2, 4, 3, 1, 5],
        {2},
        {0: 0.0, 1: 0.0, 2: 1.0, 3: 0.0},
    )

  def test_07_tesi_violazione_nodo_1(self):
    self._check_case(
        "Tesi: violazione nel nodo 1",
        [7, 3, 5, 4, 6, 2, 1],
        {1},
        {0: 0.0, 1: 1.0, 2: 0.0, 3: 0.0},
    )


if __name__ == "__main__":
  unittest.main(verbosity=2)
