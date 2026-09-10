import csv
from datetime import datetime
import time
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pyvisa

# CONFIGURATION
CHANNELS_TO_ACQUIRE = [1, 2, 3, 4]  # Liste mit den gewuenschten Kanaelen
CHANNEL_DESCRIPTIONS = {
    1: "Hall_A",
    2: "Motor V+",
    3: "Driver IN1",
    4: "Driver IN2"
}
VISA_ADDRESS = "TCPIP::192.168.1.26::INSTR"

# Rigol Hardware-Farben fuer das Plotten definieren
RIGOL_COLORS = {
    1: "#D4B100",  # Dunkelgelb/Gold fuer bessere Lesbarkeit auf weissem Grund
    2: "#00BFFF",  # Deep Sky Blue / Cyan (Rigol Hellblau)
    3: "#FF1493",  # Deep Pink (Rigol Pink)
    4: "#00008B"   # Dark Blue (Rigol Dunkelblau)
}

# 1. Generate a unique filename using the current date and time
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"rigol_snapshot_{timestamp}.csv"

# Initialize VISA connection
rm = pyvisa.ResourceManager()
scope = rm.open_resource(VISA_ADDRESS)

# Expliziten Timeout erhoehen (5000 ms = 5 Sekunden), um Netzwerk-Timeouts zu verhindern
scope.timeout = 5000

channel_data = {}
time_axis = []
validated_channels = []
valid_options = (1, 2, 3, 4)

try:
    # 2. Force the scope into NORMAL trigger sweep mode (NOT Auto)
    print("Setting scope trigger sweep mode to SINGLE...")
    scope.write(":RUN")
    scope.write(":TRIGger:SWEep SINGle")
    #print(scope.query(":TRIGger:SWEep?"))
    
    # Put the scope in RUN mode so it actively looks for the trigger
    #scope.write(":RUN")
    
    # 3. Interactive User-Loop for Trigger Check
    print("\nThe scope is now armed in SINGLE mode and waiting for your trigger.")
    
    while True:

        # Check if the scope has actually triggered
        # Rigol Status values: RUN, WAIT, T'D, STOP
        status = scope.query(":TRIGger:STATus?").strip()
        
        if status == "WAIT":
            #print("\nNo trigger has happened yet! The scope is still waiting for a signal.")
            #print("Try again once the event occurred.\n")
            continue
        else:
            # Trigger has happened (Status is T'D or STOP)
            print(f"\nTrigger confirmed! Scope status is: {status}")
            break
    input("Press [ENTER] to acquire data...")

    # 4. Read the current time division from the scope (in seconds, e.g. 0.005)
    time_div_seconds = float(scope.query(":TIMebase:MAIN:SCALe?").strip())

    # 5. Freeze the display buffer to lock the currently shown waveform
    print("Freezing buffer (STOP)...")
    scope.write(":STOP")
    
    # WICHTIG: Kurze Pause einlegen (200ms), damit sich die Rigol-Firmware nach 
    # dem STOP-Befehl fangen kann, bevor wir den Bus mit Abfragen fluten.
    time.sleep(0.2)

    # 6. Verify user-requested channels are actually active on the scope screen
    for ch in CHANNELS_TO_ACQUIRE:
        if ch not in valid_options:
            print(f"Skipping invalid channel number: CH{ch}")
            continue

        is_on = scope.query(f":CHANnel{ch}:DISPlay?").strip()
        if is_on in ["1", "ON"]:
            validated_channels.append(ch)
        else:
            print(
                f"Warning: CH{ch} is turned OFF on the scope screen. Skipping."
            )

    if not validated_channels:
        print(
            "Error: None of the requested channels are visible on the scope screen. Exiting."
        )
        exit()

    print(f"Capturing screen data for channels: {validated_channels}")

    # 7. Pull screen buffer data for each validated channel
    for ch in validated_channels:
        # Sequenz um den Rigol "input invalid" Bug zu umgehen
        scope.write(f":WAVeform:SOURce CHANnel{ch}")
        scope.write(":WAVeform:MODE NORMAl")  
        scope.write(":WAVeform:FORMAT BYTE")  

        # Get calibration data for scaling using explicit list indices
        preamble = scope.query(":WAVeform:PREamble?").split(",")
        x_inc = float(preamble[4])
        x_orig = float(preamble[5])
        y_inc = float(preamble[7])
        y_orig = float(preamble[8])
        y_ref = float(preamble[9])

        # Download the fast, raw ADC screen bytes
        raw_data = scope.query_binary_values(
            ":WAVeform:DATA?", datatype="B", container=list, header_fmt="ieee"
        )

        # Lock down the master time axis using the first channel processed
        if not time_axis:
            time_axis = [x_orig + (idx * x_inc) for idx in range(len(raw_data))]

        # Transform ADC integers into real-world Voltages
        voltages = []
        for raw_value in raw_data:
            volt_val = (raw_value - y_ref - y_orig) * y_inc
            voltages.append(volt_val)

        channel_data[ch] = voltages

    # 8. Generate the synchronized multi-column CSV
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.writer(file)

        # Header layout (e.g., Time (s), CH1 (V), CH2 (V))
        headers = ["Time (s)"] + [f"CH{ch} (V)" for ch in validated_channels]
        writer.writerow(headers)

        # Merge the lists vertically row by row
        voltage_lists = [channel_data[ch] for ch in validated_channels]
        for row_data in zip(time_axis, *voltage_lists):
            writer.writerow(row_data)

    print(
        f"Success! Saved screen snapshot ({len(time_axis)} points) to '{csv_filename}'"
    )

    # 9. Determine Best Scaling Unit for the Plot
    if time_div_seconds < 1e-6:
        time_factor = 1e9
        unit_label = "Time (ns)"
        title_unit = "ns"
    elif time_div_seconds < 1e-3:
        time_factor = 1e6
        unit_label = "Time (µs)"
        title_unit = "µs"
    elif time_div_seconds < 1.0:
        time_factor = 1e3
        unit_label = "Time (ms)"
        title_unit = "ms"
    else:
        time_factor = 1.0
        unit_label = "Time (s)"
        title_unit = "s"

    # Scale time axis and time division for plotting
    time_axis_scaled = [t * time_factor for t in time_axis]
    time_div_scaled = time_div_seconds * time_factor

    # 10. Matplotlib Plotting Block (Scope Simulation)
    fig, ax = plt.subplots(figsize=(10, 5))
    for ch in validated_channels:
        label_text = CHANNEL_DESCRIPTIONS.get(ch, f"Channel {ch}")
        trace_color = RIGOL_COLORS.get(ch, "#000000")
        ax.plot(time_axis_scaled, channel_data[ch], label=label_text, color=trace_color)

    # Standard-Flisskommaformat fuer die Ticks zwingen (keine Suffixe an den Zahlen)
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%g'))

    # Zwinge die Gitterlinien exakt auf die skalierte Time/Div
    ax.xaxis.set_major_locator(ticker.MultipleLocator(time_div_scaled))


    # Titel und Label mit sauber getrennten Einheiten setzen
    plt.title(f"Rigol Oscilloscope Data Capture ({time_div_scaled:g} {title_unit}/Div)")
    plt.xlabel(unit_label)
    plt.ylabel("Voltage (V)")
    
    plt.grid(True, which='major', linestyle='--', color='gray', alpha=0.7)
    plt.legend()
    plt.show()

finally:
    # Always clean up instrument hooks safely
    scope.close()
