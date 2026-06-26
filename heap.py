from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Gate
from math import pi, sqrt


def constructQuantumVector(v: list[int], d: int) -> QuantumCircuit:
  qc = QuantumCircuit()
  length = len(v)
  qr: QuantumRegister
  binaryString: str
  bitsSetToOne: list[int]

  for i in range(length):
    qr = QuantumRegister(d, f'v[{str(i)}]')
    qc.add_register(qr)
    binaryString = '0'*(d-len(bin(v[i])[2:]))+bin(v[i])[2:]
    bitsSetToOne = [qr[j] for j in range(d) if binaryString[j] == '1']
    qc.x(bitsSetToOne)

  return qc


def accessElementClassically(qc: QuantumCircuit, i: int, d: int) -> QuantumCircuit:
  qr = QuantumRegister(d, 'access')
  qc.add_register(qr)

  for j in range(d):
    qc.cx(i * d + j, qr[j])

  return qc


def selectAccess(values: list[int], bits: int, index: int | None = None, customQAddrReg: QuantumRegister | None = None, customQRegValues: QuantumRegister | None = None, addrStartIndex: int = 0, valuesStartIndex: int = 0) -> Gate:
  qAddrReg = QuantumRegister(
      (len(values) - 1).bit_length(), "address") if customQAddrReg is None else customQAddrReg
  qValueReg = QuantumRegister(
      bits, "values") if customQRegValues is None else customQRegValues
  qc = QuantumCircuit(qAddrReg, qValueReg)

  if (index):
    binIndex: str = bin(index)[2:].zfill((len(values) - 1).bit_length())
    for i in range(len(binIndex)):
      if (binIndex[i] == '1'):
        qc.x(qAddrReg[i])

  binAddress: str
  binValue: str
  for i in range(len(values)):
    binAddress = bin(i)[2:].zfill((len(values) - 1).bit_length())
    for j in range(len(binAddress)):
      if (binAddress[j] == '0'):
        qc.x(qAddrReg[j + addrStartIndex])

    binValue = bin(values[i])[2:].zfill(bits)
    for j in range(len(binValue)):
      if binValue[j] == '1':
        qc.mcx(qAddrReg[addrStartIndex:addrStartIndex + bits],
               qValueReg[j + valuesStartIndex])

    for j in range(len(binAddress)):
      if (binAddress[j] == '0'):
        qc.x(qAddrReg[j + addrStartIndex])

  return qc.to_gate()


def leftChildCircuit(bits: int, customQAddrReg: QuantumRegister | None = None, customQRegValues: QuantumRegister | None = None, addrStartIndex: int = 0) -> Gate:
  if customQAddrReg is not None and customQRegValues is not None:
    qc = QuantumCircuit(customQAddrReg, customQRegValues)
  else:
    qc = QuantumCircuit(addrStartIndex + 2 * bits)
  for j in range(bits - 1):
    qc.cx(bits - 1 - j, 2 * bits - 2 - j + addrStartIndex)
  qc.x(2 * bits - 1 + addrStartIndex)
  return qc.to_gate()


def rightChildCircuit(bits: int, customQAddrReg: QuantumRegister | None = None, customQRegValues: QuantumRegister | None = None, addrStartIndex: int = 0) -> Gate:
  if customQAddrReg is not None and customQRegValues is not None:
    qc = QuantumCircuit(customQAddrReg, customQRegValues)
  else:
    qc = QuantumCircuit(addrStartIndex + 2 * bits)
  for j in range(bits - 1):
    qc.cx(bits - 1 - j, 2 * bits - 2 - j + addrStartIndex)
  for k in range(bits - 2, -1, -1):
    controls = [2 * bits - 2 - m + addrStartIndex for m in range(k)]
    target = 2 * bits - 2 - k + addrStartIndex
    if controls:
      qc.mcx(controls, target)
    else:
      qc.x(target)
  return qc.to_gate()


def greaterThan(bits: int, qregs: list[QuantumRegister] | None = None, firstValueStartIndex: int = 0, secondValueStartIndex: int = 0, outIndex: int = 0) -> Gate:
  if qregs is not None:
    qc = QuantumCircuit(*qregs)
  else:
    qc = QuantumCircuit(QuantumRegister(bits, 'x'),
                        QuantumRegister(bits, 'y'), QuantumRegister(1, 'out'))

  for i in range(bits):
    qc.x(secondValueStartIndex + i)
    qc.mcx(
        [firstValueStartIndex + i] + list(range(secondValueStartIndex, secondValueStartIndex + i+1)), outIndex)
    qc.x(secondValueStartIndex + i)
    if (i < bits-1):
      qc.cx(firstValueStartIndex + i, secondValueStartIndex + i)
      qc.x(secondValueStartIndex + i)
  for i in range(bits-1):
    j = bits-i-2
    qc.x(secondValueStartIndex + j)
    qc.cx(firstValueStartIndex + j, secondValueStartIndex + j)
  return qc.to_gate()


def propertyVerifier(vector: list[int], bits: int, cQAddrValues: QuantumRegister = None, cQRegValues: QuantumRegister = None) -> QuantumCircuit:
  if cQAddrValues is None and cQRegValues is None:
    cQAddrValues = QuantumRegister(3 * bits, 'address')
    cQRegValues = QuantumRegister(3 * bits + 3, 'values')

  qc = QuantumCircuit(cQAddrValues, cQRegValues)

  qc.compose(leftChildCircuit(
      bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues), inplace=True)
  qc.compose(rightChildCircuit(
      bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues, addrStartIndex=bits), inplace=True)
  qc.compose(selectAccess(
      vector, bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues), inplace=True)
  qc.compose(selectAccess(
      vector, bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues, addrStartIndex=bits, valuesStartIndex=bits), inplace=True)
  qc.compose(selectAccess(
      vector, bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues, addrStartIndex=bits * 2, valuesStartIndex=bits * 2), inplace=True)

  qc.compose(greaterThan(
      bits, qregs=[cQAddrValues, cQRegValues], firstValueStartIndex=bits * 3, secondValueStartIndex=bits * 3 + bits, outIndex=bits * 3 + bits * 3), inplace=True)

  qc.compose(greaterThan(
      bits, qregs=[cQAddrValues, cQRegValues], firstValueStartIndex=bits * 3, secondValueStartIndex=bits * 3 + bits * 2, outIndex=bits * 3 + bits * 3 + 1), inplace=True)

  qc.ccx(cQRegValues[-3], cQRegValues[-2], cQRegValues[-1])
  return qc.to_gate()


def groverSearch(vector: list[int], bits: int,
                 cQAddrValues: QuantumRegister = None,
                 cQRegValues: QuantumRegister = None) -> QuantumCircuit:

  def grover_diffuser(qc, qubits):
    qc.h(qubits)
    qc.x(qubits)
    qc.h(qubits[-1])
    qc.mcx(qubits[:-1], qubits[-1])
    qc.h(qubits[-1])
    qc.x(qubits)
    qc.h(qubits)

  if cQAddrValues is None and cQRegValues is None:
    cQAddrValues = QuantumRegister(3 * bits, 'address')
    cQRegValues = QuantumRegister(3 * bits + 3, 'values')

  phase_kick = QuantumRegister(1, 'phase')
  qc = QuantumCircuit(cQAddrValues, cQRegValues, phase_kick)

  search_qubits = list(cQAddrValues[1:bits])
  flag = cQRegValues[-1]

  qc.h(search_qubits)

  qc.x(phase_kick)
  qc.h(phase_kick)

  qc.barrier()

  N = 2 ** (bits - 1)
  iterations = int((pi / 4) * sqrt(N))
  pv = propertyVerifier(vector, bits, cQAddrValues, cQRegValues)

  for _ in range(iterations):
    qc.compose(pv, inplace=True)
    qc.barrier()

    qc.x(flag)
    qc.cx(flag, phase_kick[0])
    qc.x(flag)
    qc.barrier()

    qc.compose(pv.inverse(), inplace=True)
    qc.barrier()

    grover_diffuser(qc, search_qubits)
    qc.barrier()

  return qc
