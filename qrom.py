import pennylane as qp
import matplotlib.pyplot as plt


bitstrings = ["011", "110", "111"]

control_wires = [0, 1]
target_wires = [2, 3, 4]

Ui = [qp.BasisState(int(bitstring, 2), target_wires)
      for bitstring in bitstrings]

dev = qp.device("default.qubit")


# This line is included for drawing purposes only.
@qp.set_shots(1)
@qp.qnode(dev)
def circuit(index):
  qp.BasisState(index, wires=control_wires)
  qp.Select(Ui, control=control_wires)
  return qp.sample(wires=target_wires)


for i in range(len(bitstrings)):
  print(f"The bitstring stored in index {i} is: {circuit(i)[0]}")

qp.draw_mpl(circuit, style="pennylane", level="device")(3)
plt.savefig("pio.png")
