from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


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


def accessElement(qc: QuantumCircuit, i: int, d: int) -> QuantumCircuit:
  qr = QuantumRegister(d, 'access')
  qc.add_register(qr)

  for j in range(d):
    qc.cx(i * d + j, qr[j])

  return qc
