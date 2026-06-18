from heap import *
from qiskit_aer import Aer
from qiskit import transpile, QuantumRegister, ClassicalRegister


def main():
  quantumVectorCircuit = selectAccess([4, 5, 6, 7], 3)

  quantumVectorCircuit.add_register(ClassicalRegister(3))
  quantumVectorCircuit.measure(2, 2)
  quantumVectorCircuit.measure(3, 1)
  quantumVectorCircuit.measure(4, 0)

  quantumVectorCircuit.draw('mpl', filename="image.jpg")

  simulator = Aer.get_backend('aer_simulator')
  compiled_circuit = transpile(quantumVectorCircuit, simulator)

  job = simulator.run(compiled_circuit, shots=1024)
  result = job.result()
  cnt = result.get_counts(compiled_circuit)
  print(cnt)


if __name__ == "__main__":
  main()
