from heap import *
from qiskit_aer import Aer
from qiskit import transpile, QuantumRegister, ClassicalRegister


def main():
  quantumVectorCircuit = constructQuantumVector([7, 6, 5], 3)

  quantumAccessCircuit = accessElement(quantumVectorCircuit, 0, 3)

  quantumAccessCircuit.draw('mpl', filename="image.jpg")

  # simulator = Aer.get_backend('aer_simulator')
  # compiled_circuit = transpile(quantumAccessCircuit, simulator)

  # job = simulator.run(compiled_circuit, shots=1024)
  # result = job.result()
  # cnt = result.get_counts(compiled_circuit)
  # print(cnt)


if __name__ == "__main__":
  main()
