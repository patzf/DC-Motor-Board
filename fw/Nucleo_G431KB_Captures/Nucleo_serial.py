import serial
import csv
import numpy as np
import matplotlib.pyplot as plt

with serial.Serial('COM5', 460800, timeout=None) as ser: #//460800

    ser.flushInput()

    raw = ser.read(2000) # 500 floats * 4bytes

    # Convert bytes -> floats
    values = np.frombuffer(raw, dtype='<f4')

    print(len(values))
    print(values)

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
