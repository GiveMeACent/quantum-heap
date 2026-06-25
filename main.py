from heap import *
from qiskit_aer import Aer
from qiskit import transpile, QuantumRegister, ClassicalRegister


def main():
  cQAddrValues: QuantumRegister = QuantumRegister(9, 'address')
  cQRegValues: QuantumRegister = QuantumRegister(12, 'values')
  creg: ClassicalRegister = ClassicalRegister(12, 'result')
  vector: list[int] = [6, 5, 4, 3, 2, 1, 0]
  bits: int = 3

  fullCircuit = QuantumCircuit(cQAddrValues, cQRegValues, creg)

  fullCircuit.h(1)
  fullCircuit.h(2)

  fullCircuit.compose(propertyVerifier(
      vector, bits, cQAddrValues, cQRegValues), inplace=True)

  fullCircuit.draw('mpl', filename='test.jpg')

  fullCircuit.measure(cQRegValues[0], 11)
  fullCircuit.measure(cQRegValues[1], 10)
  fullCircuit.measure(cQRegValues[2], 9)
  fullCircuit.measure(cQRegValues[3], 8)
  fullCircuit.measure(cQRegValues[4], 7)
  fullCircuit.measure(cQRegValues[5], 6)
  fullCircuit.measure(cQRegValues[6], 5)
  fullCircuit.measure(cQRegValues[7], 4)
  fullCircuit.measure(cQRegValues[8], 3)
  fullCircuit.measure(cQRegValues[9], 2)
  fullCircuit.measure(cQRegValues[10], 1)
  fullCircuit.measure(cQRegValues[11], 0)

  fullCircuit.draw('mpl', filename='test.jpg')

  simulator = Aer.get_backend('aer_simulator')
  compiled_circuit = transpile(fullCircuit, simulator)

  job = simulator.run(compiled_circuit, shots=1024)
  result = job.result()
  cnt = result.get_counts(compiled_circuit)
  print(cnt)


if __name__ == "__main__":
  main()
