from math import pi, sqrt

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Gate
from qiskit.circuit.library import PermutationGate


class QuantumHeap:
  """Build quantum circuits to verify and search for max-heap violations.

  Store the classical vector and its bit width to construct a circuit-based
  access oracle. An address absent from the vector returns the value zero.
  The Grover search superposes only address qubits from index 2 to ``bits - 1``.

  The heap experiments assume strictly positive values and use
  ``2 ** (bits - 1) - 1`` elements, including a leaf in the search space.
  The current verifier uses strict greater-than comparisons.
  """

  def __init__(self, vector: list[int], bits: int):
    """Initialize the data vector and its representation width."""
    self.vector = list(vector)
    self.bits = bits

  def construct_quantum_vector(self) -> QuantumCircuit:
    """Prepare a quantum register per value in the computational basis."""
    qc = QuantumCircuit()

    for index, value in enumerate(self.vector):
      register = QuantumRegister(self.bits, f"v[{index}]")
      qc.add_register(register)
      binary_value = bin(value)[2:].zfill(self.bits)
      ones = [register[bit]
              for bit in range(self.bits) if binary_value[bit] == "1"]
      if ones:
        qc.x(ones)

    return qc

  def select_access(
      self,
      index: int | None = None,
      address_register: QuantumRegister | None = None,
      values_register: QuantumRegister | None = None,
      address_start_index: int = 0,
      values_start_index: int = 0,
  ) -> Gate:
    """Build a reversible, circuit-based address-to-value access gate.

    XOR the selected vector value into the requested output qubits.
    Accesses outside the vector leave the output unchanged (value zero).
    Custom registers and offsets select subregisters of a larger circuit.

    Returns:
        A gate implementing the classical lookup coherently.
    """
    q_address = (
        QuantumRegister((len(self.vector) - 1).bit_length(), "address")
        if address_register is None else address_register
    )
    q_values = (
        QuantumRegister(self.bits, "values")
        if values_register is None else values_register
    )
    qc = QuantumCircuit(q_address, q_values)

    if index:
      binary_index = bin(index)[2:].zfill(self.bits)
      for bit, digit in enumerate(binary_index):
        if digit == "1":
          qc.x(q_address[bit])

    for position, value in enumerate(self.vector):
      binary_address = bin(position)[2:].zfill(self.bits)
      for bit, digit in enumerate(binary_address):
        if digit == "0":
          qc.x(q_address[bit + address_start_index])

      binary_value = bin(value)[2:].zfill(self.bits)
      for bit, digit in enumerate(binary_value):
        if digit == "1":
          qc.mcx(
              q_address[address_start_index:address_start_index + self.bits],
              q_values[bit + values_start_index],
          )

      for bit, digit in enumerate(binary_address):
        if digit == "0":
          qc.x(q_address[bit + address_start_index])

    return qc.to_gate()

  def quantum_rotation(self, n: int, s: int) -> Gate:
    """Construct a cyclic permutation of ``n`` qubits by ``s`` positions."""
    s %= n
    qc = QuantumCircuit(n)
    permutation = [(position - s) % n for position in range(n)]
    qc.append(PermutationGate(permutation), range(n))
    return qc.decompose().to_gate(label=f"R_{s}")

  def quantum_character_rotation(self, n: int, char_size: int) -> QuantumCircuit:
    """Control cyclic rotations of ``n`` fixed-width data words by an index."""
    address_bits = int(np.ceil(np.log2(n)))
    index_register = QuantumRegister(address_bits, "j")
    data_register = QuantumRegister(n * char_size, "q")
    qc = QuantumCircuit(index_register, data_register)

    for bit in range(address_bits):
      controlled_rotation = self.quantum_rotation(n, 2**bit).control(1)
      for character_bit in range(char_size):
        lines = [data_register[position * char_size + character_bit]
                 for position in range(n)]
        qc.compose(
            controlled_rotation,
            [index_register[address_bits - 1 - bit], *lines],
            inplace=True,
        )

    return qc

  def left_child_circuit(
      self,
      address_register: QuantumRegister | None = None,
      values_register: QuantumRegister | None = None,
      address_start_index: int = 0,
  ) -> Gate:
    """Compute the left-child address ``2 * i + 1`` into its register."""
    if address_register is not None and values_register is not None:
      qc = QuantumCircuit(address_register, values_register)
    else:
      qc = QuantumCircuit(address_start_index + 2 * self.bits)

    for bit in range(self.bits - 1):
      qc.cx(self.bits - 1 - bit, 2 * self.bits -
            2 - bit + address_start_index)
    qc.x(2 * self.bits - 1 + address_start_index)
    return qc.to_gate()

  def right_child_circuit(
      self,
      address_register: QuantumRegister | None = None,
      values_register: QuantumRegister | None = None,
      address_start_index: int = 0,
  ) -> Gate:
    """Compute the right-child address ``2 * i + 2`` into its register."""
    if address_register is not None and values_register is not None:
      qc = QuantumCircuit(address_register, values_register)
    else:
      qc = QuantumCircuit(address_start_index + 2 * self.bits)

    for bit in range(self.bits - 1):
      qc.cx(self.bits - 1 - bit, 2 * self.bits -
            2 - bit + address_start_index)
    for bit in range(self.bits - 2, -1, -1):
      controls = [2 * self.bits - 2 - previous +
                  address_start_index for previous in range(bit)]
      target = 2 * self.bits - 2 - bit + address_start_index
      if controls:
        qc.mcx(controls, target)
      else:
        qc.x(target)
    return qc.to_gate()

  def greater_than(
      self,
      registers: list[QuantumRegister] | None = None,
      first_value_start_index: int = 0,
      second_value_start_index: int = 0,
      out_index: int = 0,
  ) -> Gate:
    """Set an output qubit when the first unsigned value exceeds the second.

    The comparison is strict: equal values do not set the output qubit.
    Register offsets identify the two operands and the output flag.
    """
    if registers is not None:
      qc = QuantumCircuit(*registers)
    else:
      qc = QuantumCircuit(
          QuantumRegister(self.bits, "x"),
          QuantumRegister(self.bits, "y"),
          QuantumRegister(1, "out"),
      )

    for bit in range(self.bits):
      qc.x(second_value_start_index + bit)
      qc.mcx(
          [first_value_start_index + bit]
          + list(range(second_value_start_index,
                 second_value_start_index + bit + 1)),
          out_index,
      )
      qc.x(second_value_start_index + bit)
      if bit < self.bits - 1:
        qc.cx(first_value_start_index + bit,
              second_value_start_index + bit)
        qc.x(second_value_start_index + bit)

    for bit in range(self.bits - 1):
      index = self.bits - bit - 2
      qc.x(second_value_start_index + index)
      qc.cx(first_value_start_index + index,
            second_value_start_index + index)
    return qc.to_gate()

  def property_verifier(
      self,
      address_register: QuantumRegister | None = None,
      values_register: QuantumRegister | None = None,
  ) -> QuantumCircuit:
    """Evaluate the two parent-child comparisons and their conjunction.

    The last value-register qubit is one if the parent is strictly
    greater than both children, and zero otherwise. Intermediate
    registers are left populated so the circuit can be uncomputed.
    """
    if address_register is None and values_register is None:
      address_register = QuantumRegister(3 * self.bits, "address")
      values_register = QuantumRegister(3 * self.bits + 3, "values")

    qc = QuantumCircuit(address_register, values_register)
    qc.compose(
        self.left_child_circuit(address_register, values_register),
        inplace=True,
    )
    qc.compose(
        self.right_child_circuit(
            address_register, values_register, self.bits),
        inplace=True,
    )
    qc.compose(
        self.select_access(
            address_register=address_register,
            values_register=values_register,
        ),
        inplace=True,
    )
    qc.compose(
        self.select_access(
            address_register=address_register,
            values_register=values_register,
            address_start_index=self.bits,
            values_start_index=self.bits,
        ),
        inplace=True,
    )
    qc.compose(
        self.select_access(
            address_register=address_register,
            values_register=values_register,
            address_start_index=2 * self.bits,
            values_start_index=2 * self.bits,
        ),
        inplace=True,
    )
    qc.compose(
        self.greater_than(
            registers=[address_register, values_register],
            first_value_start_index=3 * self.bits,
            second_value_start_index=4 * self.bits,
            out_index=6 * self.bits,
        ),
        inplace=True,
    )
    qc.compose(
        self.greater_than(
            registers=[address_register, values_register],
            first_value_start_index=3 * self.bits,
            second_value_start_index=5 * self.bits,
            out_index=6 * self.bits + 1,
        ),
        inplace=True,
    )
    qc.ccx(values_register[-3], values_register[-2], values_register[-1])
    return qc

  def grover_search(
      self,
      address_register: QuantumRegister | None = None,
      values_register: QuantumRegister | None = None,
  ) -> QuantumCircuit:
    """Search for violating nodes using phase kickback and Grover diffusion.

    Keep the first two address qubits at zero and superpose the remaining
    ``bits - 2`` qubits. A violating node has verifier flag zero, which
    triggers a phase flip. The iteration count assumes one marked node.

    Returns:
        An unmeasured circuit including the phase ancilla.
    """

    def grover_diffuser(qc: QuantumCircuit, qubits: list) -> None:
      """Apply Grover diffusion to exactly the search-address qubits."""
      if len(qubits) == 1:
        qc.x(qubits[0])
        return

      qc.h(qubits)
      qc.x(qubits)
      qc.h(qubits[-1])
      qc.mcx(qubits[:-1], qubits[-1])
      qc.h(qubits[-1])
      qc.x(qubits)
      qc.h(qubits)

    if address_register is None and values_register is None:
      address_register = QuantumRegister(3 * self.bits, "address")
      values_register = QuantumRegister(3 * self.bits + 3, "values")

    phase_register = QuantumRegister(1, "phase")
    qc = QuantumCircuit(address_register, values_register, phase_register)
    search_qubits = list(address_register[2:self.bits])
    flag = values_register[-1]

    qc.h(search_qubits)
    qc.x(phase_register)
    qc.h(phase_register)
    qc.barrier()

    search_space_size = 2 ** (self.bits - 2)
    iterations = int((pi / 4) * sqrt(search_space_size))
    oracle = self.property_verifier(address_register, values_register)

    for _ in range(iterations):
      qc.compose(oracle, inplace=True)
      qc.barrier()
      qc.x(flag)
      qc.cx(flag, phase_register[0])
      qc.x(flag)
      qc.barrier()
      qc.compose(oracle.inverse(), inplace=True)
      qc.barrier()
      grover_diffuser(qc, search_qubits)
      qc.barrier()

    return qc
