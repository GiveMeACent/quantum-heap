from heap import *
from qiskit_aer import Aer
from qiskit import transpile, QuantumRegister, ClassicalRegister


def main():
  cQAddrValues: QuantumRegister = QuantumRegister(6, 'address')
  cQRegValues: QuantumRegister = QuantumRegister(9, 'values')
  creg: ClassicalRegister = ClassicalRegister(9, 'result')
  vector: list[int] = [2, 1, 3, 0]
  bits: int = 2

  fullCircuit = QuantumCircuit(cQAddrValues, cQRegValues, creg)
  fullCircuit.compose(leftChildCircuit(
      bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues), inplace=True)
  fullCircuit.compose(rightChildCircuit(
      bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues, addrStartIndex=2), inplace=True)
  fullCircuit.compose(selectAccess(
      vector, bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues), inplace=True)
  fullCircuit.compose(selectAccess(
      vector, bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues, addrStartIndex=2, valuesStartIndex=2), inplace=True)
  fullCircuit.compose(selectAccess(
      vector, bits, customQAddrReg=cQAddrValues, customQRegValues=cQRegValues, addrStartIndex=4, valuesStartIndex=4), inplace=True)

  fullCircuit.compose(greaterThan(
      bits, qregs=[cQAddrValues, cQRegValues], firstValueStartIndex=6, secondValueStartIndex=8, outIndex=12), inplace=True)

  fullCircuit.compose(greaterThan(
      bits, qregs=[cQAddrValues, cQRegValues], firstValueStartIndex=6, secondValueStartIndex=10, outIndex=13), inplace=True)

  fullCircuit.ccx(cQRegValues[6], cQRegValues[7], cQRegValues[8])
  fullCircuit.draw('mpl', filename='test.jpg')

  fullCircuit.measure(cQRegValues[0], 8)
  fullCircuit.measure(cQRegValues[1], 7)
  fullCircuit.measure(cQRegValues[2], 6)
  fullCircuit.measure(cQRegValues[3], 5)
  fullCircuit.measure(cQRegValues[4], 4)
  fullCircuit.measure(cQRegValues[5], 3)
  fullCircuit.measure(cQRegValues[6], 2)
  fullCircuit.measure(cQRegValues[7], 1)
  fullCircuit.measure(cQRegValues[8], 0)

  simulator = Aer.get_backend('aer_simulator')
  compiled_circuit = transpile(fullCircuit, simulator)

  job = simulator.run(compiled_circuit, shots=1024)
  result = job.result()
  cnt = result.get_counts(compiled_circuit)
  print(cnt)


if __name__ == "__main__":
  main()
