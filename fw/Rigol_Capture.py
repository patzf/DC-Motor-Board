import serial
import csv
import numpy as np
import matplotlib.pyplot as plt

with serial.Serial('COM3', 115200, timeout=None) as ser:

    ser.flushInput()

    raw = ser.read(2000)

    # Convert 800 bytes -> 200 floats
    values = np.frombuffer(raw, dtype='<f4')

    # Save to CSV
    with open('data.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(values)

    print("written raw data to csv")

    # Time axis: 1 ms per sample
    t = np.arange(len(values))  # 0, 1, 2, ... ms

    # Plot
    plt.plot(t, values)
    plt.xlabel("Time [ms]")
    plt.ylabel("RPM")
    plt.grid()
    plt.show()
