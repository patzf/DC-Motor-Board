import csv
from datetime import datetime
import time
import socket
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pyvisa
CHANNELS_TO_ACQUIRE=[1,2,3,4]
CHANNEL_DESCRIPTIONS={1:"Hall_A",2:"Motor V+",3:"Driver IN1",4:"Driver IN2"}
VISA_ADDRESS="TCPIP::192.168.1.26::INSTR"
TCP_HOST="192.168.1.26"
TCP_PORT=5555
RIGOL_COLORS={1:"#D4B100",2:"#00BFFF",3:"#FF1493",4:"#00008B"}
MEMORY_OPTIONS={7000:"7k",70000:"70k",700000:"700k",7000000:"7M"}
print("Select acquisition memory depth.")
print("1 = 7k")
print("2 = 70k")
print("3 = 700k")
print("4 = 7M")
selection=input("Enter selection [1-4]: ").strip()
selection_map={"1":7000,"2":70000,"3":700000,"4":7000000}
if selection not in selection_map:
    raise ValueError("Invalid selection. Enter 1, 2, 3, or 4.")
ACQUISITION_MEMORY=selection_map[selection]
MEMORY_LABEL=MEMORY_OPTIONS[ACQUISITION_MEMORY]
print(f"Selected acquisition memory: {MEMORY_LABEL}")
print(f"IMPORTANT: Set the scope manually to {MEMORY_LABEL} before continuing.")
input("Press [ENTER] when the scope memory depth is set...")
timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename=f"rigol_raw_{MEMORY_LABEL}_{timestamp}.csv"
rm=pyvisa.ResourceManager()
scope=rm.open_resource(VISA_ADDRESS)
scope.timeout=5000
channel_data={}
time_axis=[]
validated_channels=[]
valid_options=(1,2,3,4)
def tcp_send(sock,cmd):
    sock.sendall((cmd+"\n").encode())
def tcp_query(sock,cmd):
    tcp_send(sock,cmd)
    data=b""
    while not data.endswith(b"\n"):
        chunk=sock.recv(4096)
        if not chunk:
            raise RuntimeError("TCP connection closed")
        data+=chunk
    return data.decode().strip()
def tcp_read_block(sock):
    header=b""
    while len(header)<11:
        chunk=sock.recv(11-len(header))
        if not chunk:
            raise RuntimeError("TCP connection closed while reading binary header")
        header+=chunk
    if header[:2]!=b"#9":
        raise RuntimeError(f"Unexpected binary header: {header!r}")
    count=int(header[2:11])
    data=b""
    while len(data)<count:
        chunk=sock.recv(min(65536,count-len(data)))
        if not chunk:
            raise RuntimeError("TCP connection closed during binary transfer")
        data+=chunk
    terminator=sock.recv(1)
    if terminator not in (b"\n",b"\r"):
        raise RuntimeError(f"Unexpected binary terminator: {terminator!r}")
    return data
def acquire_raw_channel(ch):
    sock=socket.create_connection((TCP_HOST,TCP_PORT),timeout=10)
    sock.settimeout(120)
    try:
        tcp_send(sock,f":WAVeform:SOURce CHANnel{ch}")
        tcp_send(sock,":WAVeform:MODE RAW")
        preamble=tcp_query(sock,":WAVeform:PREamble?")
        print(f"CH{ch} PREAMBLE:",preamble)
        p=preamble.split(",")
        points=int(p[2])
        x_inc=float(p[4])
        x_orig=float(p[5])
        y_inc=float(p[7])
        y_orig=float(p[8])
        y_ref=float(p[9])
        print(f"CH{ch} ACQUISITION POINTS:",points)
        if points!=ACQUISITION_MEMORY:
            raise RuntimeError(f"CH{ch} scope memory is {points} samples instead of selected {ACQUISITION_MEMORY}")
        tcp_send(sock,f":WAVeform:POINts {ACQUISITION_MEMORY}")
        points_set=int(tcp_query(sock,":WAVeform:POINts?"))
        print(f"CH{ch} POINTS SET:",points_set)
        if points_set!=ACQUISITION_MEMORY:
            raise RuntimeError(f"CH{ch} scope did not accept {ACQUISITION_MEMORY} waveform points; returned {points_set}")
        tcp_send(sock,":WAVeform:RESet")
        tcp_send(sock,":WAVeform:BEGin")
        time.sleep(1)
        total=0
        blocks=0
        raw_data=bytearray()
        while total<ACQUISITION_MEMORY:
            status=tcp_query(sock,":WAVeform:STATus?")
            print(f"CH{ch} STATUS:",status)
            tcp_send(sock,":WAVeform:DATA?")
            block=tcp_read_block(sock)
            raw_data.extend(block)
            total+=len(block)
            blocks+=1
            print(f"CH{ch} BLOCK:",blocks,"BYTES:",len(block),"TOTAL:",total)
            if status.startswith("IDLE"):
                break
            time.sleep(0.2)
        tcp_send(sock,":WAVeform:END")
        print(f"CH{ch} FINAL BYTES:",total)
        print(f"CH{ch} BLOCKS:",blocks)
        print(f"CH{ch} EXPECTED POINTS:",ACQUISITION_MEMORY)
        if total!=ACQUISITION_MEMORY:
            raise RuntimeError(f"CH{ch} received {total} samples instead of {ACQUISITION_MEMORY}")
        voltages=[(raw_value-y_ref-y_orig)*y_inc for raw_value in raw_data]
        current_time_axis=[x_orig+(idx*x_inc) for idx in range(ACQUISITION_MEMORY)]
        return voltages,current_time_axis
    finally:
        sock.close()
try:
    print(f"Verifying scope acquisition memory is {MEMORY_LABEL}...")
    memory_depth=int(scope.query(":ACQuire:MDEPth?").strip())
    print("SCOPE MEMORY:",memory_depth)
    if memory_depth!=ACQUISITION_MEMORY:
        raise RuntimeError(f"Scope memory is {memory_depth} samples, but {MEMORY_LABEL} was selected in the script. Set the scope manually to {MEMORY_LABEL} and run again.")
    print(f"Memory depth confirmed: {MEMORY_LABEL}")
    print("Setting scope trigger sweep mode to SINGLE...")
    scope.write(":RUN")
    scope.write(":TRIGger:SWEep SINGle")
    print("\nThe scope is now armed in SINGLE mode and waiting for your trigger.")
    while True:
        status=scope.query(":TRIGger:STATus?").strip()
        if status=="WAIT":
            continue
        else:
            print(f"\nTrigger confirmed! Scope status is: {status}")
            break
    input("Press [ENTER] to acquire data...")
    time_div_seconds=float(scope.query(":TIMebase:MAIN:SCALe?").strip())
    print("Freezing buffer (STOP)...")
    scope.write(":STOP")
    time.sleep(0.2)
    memory_depth=int(scope.query(":ACQuire:MDEPth?").strip())
    print("ACQUISITION MEMORY:",memory_depth)
    if memory_depth!=ACQUISITION_MEMORY:
        raise RuntimeError(f"Scope memory changed to {memory_depth} samples. Expected {ACQUISITION_MEMORY}.")
    for ch in CHANNELS_TO_ACQUIRE:
        if ch not in valid_options:
            print(f"Skipping invalid channel number: CH{ch}")
            continue
        is_on=scope.query(f":CHANnel{ch}:DISPlay?").strip()
        if is_on in ["1","ON"]:
            validated_channels.append(ch)
        else:
            print(f"Warning: CH{ch} is turned OFF on the scope screen. Skipping.")
    if not validated_channels:
        print("Error: None of the requested channels are visible on the scope screen. Exiting.")
        exit()
    print(f"Capturing FULL {MEMORY_LABEL} RAW data for channels: {validated_channels}")
    for ch in validated_channels:
        print(f"\nStarting FULL {MEMORY_LABEL} RAW acquisition for CH{ch}...")
        voltages,current_time_axis=acquire_raw_channel(ch)
        channel_data[ch]=voltages
        if not time_axis:
            time_axis=current_time_axis
    with open(csv_filename,mode="w",newline="") as file:
        writer=csv.writer(file)
        headers=["Time (s)"]+[f"CH{ch} (V)" for ch in validated_channels]
        writer.writerow(headers)
        voltage_lists=[channel_data[ch] for ch in validated_channels]
        for row_data in zip(time_axis,*voltage_lists):
            writer.writerow(row_data)
    print(f"Success! Saved FULL {MEMORY_LABEL} RAW waveform ({len(time_axis)} points) to '{csv_filename}'")
    if time_div_seconds<1e-6:
        time_factor=1e9
        unit_label="Time (ns)"
        title_unit="ns"
    elif time_div_seconds<1e-3:
        time_factor=1e6
        unit_label="Time (µs)"
        title_unit="µs"
    elif time_div_seconds<1.0:
        time_factor=1e3
        unit_label="Time (ms)"
        title_unit="ms"
    else:
        time_factor=1.0
        unit_label="Time (s)"
        title_unit="s"
    time_axis_scaled=[t*time_factor for t in time_axis]
    time_div_scaled=time_div_seconds*time_factor
    fig,ax=plt.subplots(figsize=(10,5))
    for ch in validated_channels:
        label_text=CHANNEL_DESCRIPTIONS.get(ch,f"Channel {ch}")
        trace_color=RIGOL_COLORS.get(ch,"#000000")
        ax.plot(time_axis_scaled,channel_data[ch],label=label_text,color=trace_color)
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%g'))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(time_div_scaled))
    plt.title(f"Rigol Oscilloscope Data Capture ({MEMORY_LABEL}, {time_div_scaled:g} {title_unit}/Div)")
    plt.xlabel(unit_label)
    plt.ylabel("Voltage (V)")
    plt.grid(True,which="major",linestyle="--",color="gray",alpha=0.7)
    plt.legend()
    plt.show()
finally:
    scope.close()
    rm.close()
