from math import pi, sqrt

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Gate
from qiskit.circuit.library import PermutationGate


class QuantumHeap:
  """Build quantum circuits for detecting max-heap violations.

  Provide coherent heap-value lookups using controlled gates (``"circuit"``)
  or a bit-encoded memory register with controlled cyclic rotations (``"bit"``).
  Experiments use 3 or 4 bits, respectively 3 or 7 positive heap values.
  The verifier intentionally implements strict greater-than comparisons.

  Attributes:
      vector: Heap values in array order.
      bits: Qubits used to encode each value or address.
      access_mode: Selected memory-access implementation.
      memory_words: Number of memory words, including two zero-filled words.
  """

  def __init__(self, vector: list[int], bits: int, access_mode: str = "circuit"):
    """Initialize the heap and choose the memory-access implementation.

    Args:
        vector: Strictly positive integer values in heap array order.
        bits: Value and address width, either 3 or 4 qubits.
        access_mode: ``"circuit"`` or ``"bit"``; defaults to ``"circuit"``.

    Raises:
        ValueError: If the access mode, bit width, heap length, or any value
            is outside the supported experimental domain.
    """
    if access_mode not in ("circuit", "bit"):
      raise ValueError("access_mode must be 'circuit' or 'bit'")
    if bits not in (3, 4):
      raise ValueError("the supported experiments use 3 or 4 bits")
    if len(vector) != 2 ** (bits - 1) - 1:
      raise ValueError("expected 2 ** (bits - 1) - 1 heap elements")
    if any(not isinstance(value, int) or not 0 < value < 2**bits for value in vector):
      raise ValueError(
          "heap values must be positive integers fitting into bits")
    self.vector = list(vector)
    self.bits = bits
    self.access_mode = access_mode
    self.memory_words = len(vector) + 2

  def construct_quantum_vector(self) -> QuantumCircuit:
    """Prepare the heap values as computational-basis quantum registers.

    Returns:
        QuantumCircuit: A circuit with one ``bits``-qubit register for each
        heap value, initialized to its binary representation.
    """
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
    """Construct a reversible circuit-based lookup gate.

    XOR the value selected by the address into the output subregister.
    Addresses absent from the heap encode zero and leave the output unchanged.

    Args:
        index: Optional computational-basis address mask applied before lookup.
            A value of ``None`` or ``0`` leaves the address unmodified.
        address_register: Address register, created automatically if omitted.
        values_register: Output register, created automatically if omitted.
        address_start_index: Starting qubit offset of the address subregister.
        values_start_index: Starting qubit offset of the output subregister.

    Returns:
        Gate: Reversible gate performing the controlled lookup.
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
    """Construct a cyclic qubit permutation using ``PermutationGate``.

    Args:
        n: Number of qubit positions in the rotated register.
        s: Rotation offset; reduced modulo ``n``.

    Returns:
        Gate: Cyclic rotation with the orientation used by bit-based lookup.
    """
    s %= n
    qc = QuantumCircuit(n)
    permutation = [(position + s) % n for position in range(n)]
    qc.append(PermutationGate(permutation), range(n))
    return qc.decompose().to_gate(label=f"R_{s}")

  def quantum_character_rotation(self, n: int, char_size: int) -> QuantumCircuit:
    """Construct an address-controlled rotation of fixed-width words.

    Args:
        n: Number of words in the memory register.
        char_size: Number of qubits encoding each word.

    Returns:
        QuantumCircuit: Rotation circuit acting on ``ceil(log2(n))`` index
        qubits followed by ``n * char_size`` memory qubits.
    """
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

  def _prepare_bit_memory(self, memory_register: QuantumRegister) -> QuantumCircuit:
    """Encode the heap and two trailing zero words into a memory register.

    Args:
        memory_register: Register holding ``memory_words * bits`` qubits.

    Returns:
        QuantumCircuit: Basis-state preparation circuit for the padded heap.

    Raises:
        ValueError: If the memory register has an unexpected width.
    """
    qc = QuantumCircuit(memory_register)
    if len(memory_register) != self.memory_words * self.bits:
      raise ValueError("incorrect bit-memory register size")
    for position, value in enumerate(self.vector):
      for bit, digit in enumerate(format(value, f"0{self.bits}b")):
        if digit == "1":
          qc.x(memory_register[position * self.bits + bit])
    return qc

  def bit_access(
      self,
      address_register: QuantumRegister,
      values_register: QuantumRegister,
      memory_register: QuantumRegister,
      address_start_index: int = 0,
      values_start_index: int = 0,
  ) -> QuantumCircuit:
    """XOR a selected memory word into the output without changing memory.

    Rotate the selected word to the first position, copy its bits with CNOT
    gates, and undo the rotation. The two padded words return zero for the
    missing child addresses; unsupported addresses may wrap cyclically.

    Args:
        address_register: Register holding the addressed location.
        values_register: Register receiving the selected word through XOR.
        memory_register: Register holding the padded, bit-encoded heap.
        address_start_index: Starting offset of the address subregister.
        values_start_index: Starting offset of the output subregister.

    Returns:
        QuantumCircuit: Reversible read circuit that restores the memory.

    Raises:
        ValueError: If memory width or address/output offsets are invalid.
    """
    if len(memory_register) != self.memory_words * self.bits:
      raise ValueError("incorrect bit-memory register size")
    qc = QuantumCircuit(address_register, values_register, memory_register)
    address = address_register[address_start_index:address_start_index + self.bits]
    output = values_register[values_start_index:values_start_index + self.bits]
    if len(address) != self.bits or len(output) != self.bits:
      raise ValueError("invalid address/output register offsets")
    rotation = self.quantum_character_rotation(
        self.memory_words, self.bits)
    rotation_qubits = [*address, *memory_register]
    qc.compose(rotation, qubits=rotation_qubits, inplace=True)
    for bit in range(self.bits):
      qc.cx(memory_register[bit], output[bit])
    qc.compose(rotation.inverse(), qubits=rotation_qubits, inplace=True)
    return qc

  def left_child_circuit(
      self,
      address_register: QuantumRegister | None = None,
      values_register: QuantumRegister | None = None,
      address_start_index: int = 0,
  ) -> Gate:
    """Compute the left-child address from a parent index.

    The address ``2 * i + 1`` is written into the designated child-address
    subregister by reversible gates.

    Args:
        address_register: Optional register containing address subregisters.
        values_register: Optional companion register in the larger circuit.
        address_start_index: Offset of the destination child-address bits.

    Returns:
        Gate: Reversible left-child address computation.
    """
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
    """Compute the right-child address from a parent index.

    The address ``2 * i + 2`` is written into the designated child-address
    subregister by reversible gates.

    Args:
        address_register: Optional register containing address subregisters.
        values_register: Optional companion register in the larger circuit.
        address_start_index: Offset of the destination child-address bits.

    Returns:
        Gate: Reversible right-child address computation.
    """
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
    """Compute the strict unsigned greater-than comparison.

    Toggle the output qubit when the first operand exceeds the second.
    Equal values do not satisfy the comparison.

    Args:
        registers: Optional ordered registers for embedding the comparison.
            When omitted, separate operand and flag registers are created.
        first_value_start_index: Global qubit offset of the first operand.
        second_value_start_index: Global qubit offset of the second operand.
        out_index: Global qubit index of the comparison flag.

    Returns:
        Gate: Reversible strict-comparison circuit.
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
      memory_register: QuantumRegister | None = None,
  ) -> QuantumCircuit:
    """Build the verifier for both parent-child max-heap comparisons.

    The last value-register qubit is one only if the parent is strictly
    greater than both children. Intermediate results are left available for
    subsequent uncomputation. Bit access initializes its memory register.

    Args:
        address_register: Address register for parent and two children;
            created automatically with the value register if both are absent.
        values_register: Register for three values and three output flags;
            created automatically with the address register if both are absent.
        memory_register: Padded heap memory for ``"bit"`` access; created
            automatically when omitted and unused for ``"circuit"`` access.

    Returns:
        QuantumCircuit: Circuit computing the heap-property flag.

    Raises:
        ValueError: If a memory register is passed in circuit-access mode,
            or a bit-memory register has an invalid width.
    """
    if address_register is None and values_register is None:
      address_register = QuantumRegister(3 * self.bits, "address")
      values_register = QuantumRegister(3 * self.bits + 3, "values")

    if self.access_mode == "bit":
      if memory_register is None:
        memory_register = QuantumRegister(
            self.memory_words * self.bits, "memory")
      qc = QuantumCircuit(
          address_register, values_register, memory_register)
      qc.compose(self._prepare_bit_memory(memory_register),
                 qubits=memory_register, inplace=True)
    else:
      if memory_register is not None:
        raise ValueError(
            "circuit access does not require a memory register")
      qc = QuantumCircuit(address_register, values_register)

    qc.compose(self.left_child_circuit(
        address_register, values_register), inplace=True)
    qc.compose(
        self.right_child_circuit(
            address_register, values_register, self.bits),
        inplace=True,
    )
    for offset in (0, self.bits, 2 * self.bits):
      if self.access_mode == "bit":
        access = self.bit_access(
            address_register, values_register, memory_register,
            address_start_index=offset, values_start_index=offset,
        )
      else:
        access = self.select_access(
            address_register=address_register,
            values_register=values_register,
            address_start_index=offset,
            values_start_index=offset,
        )
      qc.compose(access, inplace=True)
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
      memory_register: QuantumRegister | None = None,
  ) -> QuantumCircuit:
    """Build Grover search for addresses violating the heap property.

    Only the final ``bits - 2`` parent-address qubits are put into
    superposition. The oracle phase-marks a zero verifier flag, uncomputes
    auxiliary registers, then applies diffusion. The iteration count assumes
    one marked address.

    Args:
        address_register: Optional register for the parent and child addresses.
            Created automatically with the value register if both are absent.
        values_register: Optional register for selected values and flags.
            Created automatically with the address register if both are absent.
        memory_register: Optional padded memory register for ``"bit"`` access;
            not accepted for ``"circuit"`` access.

    Returns:
        QuantumCircuit: Unmeasured Grover circuit, including the phase qubit
        and, in bit mode, the memory register.

    Raises:
        ValueError: If a memory register is passed in circuit-access mode,
            or a bit-memory register has an invalid width.
    """

    def grover_diffuser(qc: QuantumCircuit, qubits: list) -> None:
      """Apply inversion about the mean to the search-address qubits.

      Args:
          qc: Circuit to modify in place.
          qubits: Address qubits on which to apply the diffuser.

      Returns:
          None: The input circuit is modified in place.
      """
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
    if self.access_mode == "bit":
      if memory_register is None:
        memory_register = QuantumRegister(
            self.memory_words * self.bits, "memory")
      qc = QuantumCircuit(address_register, values_register,
                          memory_register, phase_register)
    else:
      if memory_register is not None:
        raise ValueError(
            "circuit access does not require a memory register")
      qc = QuantumCircuit(
          address_register, values_register, phase_register)
    search_qubits = list(address_register[2:self.bits])
    flag = values_register[-1]

    qc.h(search_qubits)
    qc.x(phase_register)
    qc.h(phase_register)
    qc.barrier()

    search_space_size = 2 ** (self.bits - 2)
    iterations = int((pi / 4) * sqrt(search_space_size))
    oracle = self.property_verifier(
        address_register, values_register, memory_register)

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
