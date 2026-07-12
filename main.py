from heap import *
from qiskit_aer import Aer
from qiskit import transpile, QuantumRegister, ClassicalRegister


def main():
  cQAddrValues: QuantumRegister = QuantumRegister(12)
  cQRegValues: QuantumRegister = QuantumRegister(15)
  phase: QuantumRegister = QuantumRegister(1)
  creg: ClassicalRegister = ClassicalRegister(27)
  vector: list[int] = [7, 6, 2, 4, 3, 1, 5]
  bits: int = 4

  fullCircuit = QuantumCircuit(cQAddrValues, cQRegValues, phase, creg)

  fullCircuit.compose(groverSearch(
      vector, bits, cQAddrValues, cQRegValues), inplace=True)

  # fullCircuit.draw('mpl', filename='test.jpg')

  fullCircuit.barrier()

  fullCircuit.measure(cQAddrValues[0], 26)
  fullCircuit.measure(cQAddrValues[1], 25)
  fullCircuit.measure(cQAddrValues[2], 24)
  fullCircuit.measure(cQAddrValues[3], 23)
  fullCircuit.measure(cQAddrValues[4], 22)
  fullCircuit.measure(cQAddrValues[5], 21)
  fullCircuit.measure(cQAddrValues[6], 20)
  fullCircuit.measure(cQAddrValues[7], 19)
  fullCircuit.measure(cQAddrValues[8], 18)
  fullCircuit.measure(cQAddrValues[9], 17)
  fullCircuit.measure(cQAddrValues[10], 16)
  fullCircuit.measure(cQAddrValues[11], 15)

  fullCircuit.measure(cQRegValues[0], 14)
  fullCircuit.measure(cQRegValues[1], 13)
  fullCircuit.measure(cQRegValues[2], 12)
  fullCircuit.measure(cQRegValues[3], 11)
  fullCircuit.measure(cQRegValues[4], 10)
  fullCircuit.measure(cQRegValues[5], 9)
  fullCircuit.measure(cQRegValues[6], 8)
  fullCircuit.measure(cQRegValues[7], 7)
  fullCircuit.measure(cQRegValues[8], 6)
  fullCircuit.measure(cQRegValues[9], 5)
  fullCircuit.measure(cQRegValues[10], 4)
  fullCircuit.measure(cQRegValues[11], 3)

  fullCircuit.measure(cQRegValues[12], 2)
  fullCircuit.measure(cQRegValues[13], 1)
  fullCircuit.measure(cQRegValues[14], 0)

  simulator = Aer.get_backend('aer_simulator')
  compiled_circuit = transpile(fullCircuit, simulator)

  job = simulator.run(compiled_circuit, shots=1024)
  result = job.result()
  cnt = result.get_counts(compiled_circuit)
  print(cnt)


if __name__ == "__main__":
  main()
