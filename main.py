from heap import *
from qiskit_aer import Aer
from qiskit import transpile, QuantumRegister, ClassicalRegister


def main():
  cQAddrValues: QuantumRegister = QuantumRegister(9)
  cQRegValues: QuantumRegister = QuantumRegister(12)
  phase: QuantumRegister = QuantumRegister(1)
  creg: ClassicalRegister = ClassicalRegister(13)
  vector: list[int] = [6, 5, 4, 3, 2, 1, 0]
  bits: int = 3

  fullCircuit = QuantumCircuit(cQAddrValues, cQRegValues, phase, creg)
  fullCircuit.compose(groverSearch(
      vector, bits, cQAddrValues, cQRegValues), inplace=True)
  fullCircuit.draw('mpl', filename='test.jpg')

  fullCircuit.measure(cQAddrValues[0], 12)
  fullCircuit.measure(cQAddrValues[1], 11)
  fullCircuit.measure(cQAddrValues[2], 10)
  fullCircuit.measure(cQAddrValues[3], 9)
  fullCircuit.measure(cQAddrValues[4], 8)
  fullCircuit.measure(cQAddrValues[5], 7)
  fullCircuit.measure(cQAddrValues[6], 6)
  fullCircuit.measure(cQAddrValues[7], 5)
  fullCircuit.measure(cQAddrValues[8], 4)
  fullCircuit.measure(cQRegValues[9], 3)
  fullCircuit.measure(cQRegValues[10], 2)
  fullCircuit.measure(cQRegValues[11], 1)

  simulator = Aer.get_backend('aer_simulator')
  compiled_circuit = transpile(fullCircuit, simulator)

  job = simulator.run(compiled_circuit, shots=1024)
  result = job.result()
  cnt = result.get_counts(compiled_circuit)
  print(cnt)


if __name__ == "__main__":
  main()
