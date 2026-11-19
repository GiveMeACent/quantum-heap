import os
import unittest

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator

from heap import QuantumHeap


BITS = 3
SEARCH_SIZE = 2 ** (BITS - 2)
HEAP_SIZE = 2 ** (BITS - 1) - 1
SHOTS = 1024
SEED = 2026
TOLERANCE = 0.10
RUN_BIT_SIMULATIONS = os.environ.get("RUN_BIT_SIMULATIONS") == "1"


class TestGrover3Bit(unittest.TestCase):
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
    memory = (
        QuantumRegister(heap.memory_words * BITS, "memory")
        if heap.access_mode == "bit" else None
    )
    registers = [addresses, values] + \
        ([memory] if memory is not None else [])
    circuit = QuantumCircuit(*registers, output)

    circuit.h(addresses[2:BITS])
    circuit.compose(heap.property_verifier(
        addresses, values, memory), inplace=True)
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

  def _check_case(self, label, vector, expected_pairs, expected_violations):
    self.assertEqual(len(vector), HEAP_SIZE)
    self.assertTrue(all(0 < value < 2**BITS for value in vector))

    pairs = {
        (parent, child)
        for parent in range(SEARCH_SIZE)
        for child in (2 * parent + 1, 2 * parent + 2)
        if vector[parent] <= (vector[child] if child < len(vector) else 0)
    }
    self.assertEqual(pairs, expected_pairs)
    self.assertEqual({parent for parent, _ in pairs}, expected_violations)

    circuit_frequencies = self._evaluate_mode(
        "circuit", label, vector, expected_violations, None
    )
    if RUN_BIT_SIMULATIONS:
      bit_frequencies = self._evaluate_mode(
          "bit", label, vector, expected_violations, None
      )
      for index in range(SEARCH_SIZE):
        self.assertAlmostEqual(
            circuit_frequencies[index], bit_frequencies[index],
            delta=TOLERANCE,
        )

  def _evaluate_mode(self, mode, label, vector, expected_violations, expected_distribution):
    heap = QuantumHeap(vector, BITS, access_mode=mode)
    self._check_oracle(heap, expected_violations)

    addresses = QuantumRegister(3 * BITS, "address")
    values = QuantumRegister(3 * BITS + 3, "values")
    memory = (
        QuantumRegister(heap.memory_words * BITS, "memory")
        if mode == "bit" else None
    )
    phase = QuantumRegister(1, "phase")
    output = ClassicalRegister(BITS - 2, "index")
    registers = [addresses, values] + \
        ([memory] if memory is not None else [])
    circuit = QuantumCircuit(*registers, phase, output)
    circuit.compose(heap.grover_search(
        addresses, values, memory), inplace=True)
    self._measure_index(circuit, addresses, output)

    counts = self._counts(circuit)
    frequencies = {
        index: counts.get(format(index, f"0{BITS - 2}b"), 0) / SHOTS
        for index in range(SEARCH_SIZE)
    }
    pairs = {
        (parent, child)
        for parent in range(SEARCH_SIZE)
        for child in (2 * parent + 1, 2 * parent + 2)
        if vector[parent] <= (vector[child] if child < len(vector) else 0)
    }
    print(
        f"\n[3 bit, {mode}] {label} | array={vector} | "
        f"confronti violati={len(pairs)} | "
        f"nodi marcati={sorted(expected_violations)}"
    )
    print(f"        Distribuzione Grover: {frequencies}")

    for index in range(SEARCH_SIZE):
      self.assertAlmostEqual(
          frequencies[index], 0.5, delta=TOLERANCE
      )
    return frequencies

  def test_access_mode_and_memory_shape(self):
    vector = list(range(HEAP_SIZE, 0, -1))
    circuit_heap = QuantumHeap(vector, BITS)
    bit_heap = QuantumHeap(vector, BITS, access_mode="bit")
    self.assertEqual(circuit_heap.access_mode, "circuit")
    self.assertEqual(bit_heap.memory_words, HEAP_SIZE + 2)
    with self.assertRaises(ValueError):
      QuantumHeap(vector, BITS, access_mode="unsupported")

  @unittest.skipUnless(RUN_BIT_SIMULATIONS, "Set RUN_BIT_SIMULATIONS=1 to simulate bit memory")
  def test_bit_access_all_real_and_empty_addresses(self):
    vector = list(range(HEAP_SIZE, 0, -1))
    heap = QuantumHeap(vector, BITS, access_mode="bit")
    for index in range(HEAP_SIZE + 2):
      with self.subTest(index=index):
        addresses = QuantumRegister(BITS, "address")
        values = QuantumRegister(BITS, "value")
        memory = QuantumRegister(heap.memory_words * BITS, "memory")
        output = ClassicalRegister(BITS, "output")
        memory_output = ClassicalRegister(len(memory), "memory_out")
        circuit = QuantumCircuit(
            addresses, values, memory, output, memory_output)
        for bit, digit in enumerate(format(index, f"0{BITS}b")):
          if digit == "1":
            circuit.x(addresses[bit])
        circuit.compose(heap._prepare_bit_memory(memory),
                        qubits=memory, inplace=True)
        access = heap.bit_access(addresses, values, memory)
        circuit.compose(access, inplace=True)
        for bit in range(BITS):
          circuit.measure(values[bit], output[BITS - 1 - bit])
        circuit.measure(memory, memory_output)
        expected = vector[index] if index < HEAP_SIZE else 0
        padded_values = vector + [0, 0]
        bits_in_memory = "".join(
            format(value, f"0{BITS}b") for value in padded_values
        )
        expected_memory = bits_in_memory[::-1]
        self.assertEqual(
            self._counts(circuit),
            {f"{expected_memory} {format(expected, f'0{BITS}b')}": SHOTS},
        )

  @unittest.skipUnless(RUN_BIT_SIMULATIONS, "Set RUN_BIT_SIMULATIONS=1 to simulate bit memory")
  def test_bit_access_is_reversible(self):
    vector = list(range(HEAP_SIZE, 0, -1))
    heap = QuantumHeap(vector, BITS, access_mode="bit")
    addresses = QuantumRegister(BITS, "address")
    values = QuantumRegister(BITS, "value")
    memory = QuantumRegister(heap.memory_words * BITS, "memory")
    output = ClassicalRegister(BITS, "output")
    circuit = QuantumCircuit(addresses, values, memory, output)
    circuit.h(addresses)
    circuit.compose(heap._prepare_bit_memory(memory),
                    qubits=memory, inplace=True)
    access = heap.bit_access(addresses, values, memory)
    circuit.compose(access, inplace=True)
    circuit.compose(access, inplace=True)
    for bit in range(BITS):
      circuit.measure(values[bit], output[BITS - 1 - bit])
    self.assertEqual(self._counts(circuit), {"0" * BITS: SHOTS})

  def test_01_heap_valido(self):
    self._check_case("M=0", [7, 6, 5], set(), set())

  def test_02_radice_un_confronto_violato(self):
    self._check_case("M=1, un confronto", [5, 6, 4], {(0, 1)}, {0})

  def test_03_radice_entrambi_i_confronti_violati(self):
    self._check_case(
        "M=1, due confronti", [3, 5, 4], {(0, 1), (0, 2)}, {0}
    )


if __name__ == "__main__":
  unittest.main(verbosity=2)
