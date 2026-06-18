from qiskit import QuantumCircuit, QuantumRegister


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


def selectAccess(values: list[int], bits: int) -> QuantumCircuit:
  qAddrReg = QuantumRegister((len(values) - 1).bit_length(), "address")
  qValueReg = QuantumRegister(bits, "values")
  qc = QuantumCircuit(qAddrReg, qValueReg)

  qc.x(qAddrReg[1])

  qc.barrier()

  binAddress: str
  binValue: str
  for i in range(len(values)):
    binAddress = bin(i)[2:].zfill((len(values) - 1).bit_length())
    print(binAddress)
    for j in range(len(binAddress)):
      if (binAddress[j] == '0'):
        qc.x(qAddrReg[j])

    binValue = bin(values[i])[2:].zfill(bits)
    for j in range(len(binValue)):
      if binValue[j] == '1':
        qc.mcx(qAddrReg, qValueReg[j])

    for j in range(len(binAddress)):
      if (binAddress[j] == '0'):
        qc.x(qAddrReg[j])
    qc.barrier()

  return qc
