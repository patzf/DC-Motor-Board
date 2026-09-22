import csv
import socket
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pyvisa
# ========================= CONFIG =========================
CHANNELS_TO_ACQUIRE = [1, 2, 3, 4]
CHANNEL_DESCRIPTIONS = {
    1: "Hall_A",
    2: "Motor V+",
    3: "Driver IN1",
    4: "Driver IN2"
}
VISA_ADDRESS = "TCPIP::192.168.1.26::INSTR"
TCP_HOST = "192.168.1.26"
TCP_PORT = 5555
ACQUISITION_MEMORY = 70000
TRIGGER_TIMEOUT_SECONDS = 3600
ARM_TIMEOUT_SECONDS = 3
TCP_CONNECT_TIMEOUT_SECONDS = 10
TCP_READ_TIMEOUT_SECONDS = 120
POLL_INTERVAL_SECONDS = 0.02
COMMAND_DELAY_SECONDS = 0.05
RIGOL_COLORS = {
    1: "#D4B100",
    2: "#00BFFF",
    3: "#FF1493",
    4: "#00008B"
}
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"rigol_raw_{timestamp}.csv"
VALID_CHANNELS = {1, 2, 3, 4}
# ========================= VISA =========================
def visa_write(scope, command):
    scope.write(command)
    if COMMAND_DELAY_SECONDS:
        time.sleep(COMMAND_DELAY_SECONDS)
def visa_query(scope, command):
    return scope.query(command).strip()
def get_trigger_status(scope):
    return visa_query(
        scope,
        ":TRIGger:STATus?"
    ).upper()
def print_trigger_configuration(scope):
    try:
        sweep = visa_query(
            scope,
            ":TRIGger:SWEep?"
        )
    except Exception as e:
        sweep = f"ERROR:{e}"
    try:
        source = visa_query(
            scope,
            ":TRIGger:EDGE:SOURce?"
        )
    except Exception as e:
        source = f"ERROR:{e}"
    try:
        slope = visa_query(
            scope,
            ":TRIGger:EDGE:SLOPe?"
        )
    except Exception as e:
        slope = f"ERROR:{e}"
    try:
        level = visa_query(
            scope,
            ":TRIGger:EDGE:LEVel?"
        )
    except Exception as e:
        level = f"ERROR:{e}"
    print(
        f"Trigger: sweep={sweep}, "
        f"source={source}, "
        f"slope={slope}, "
        f"level={level}"
    )
# ========================= TRIGGER =========================
def arm_single_acquisition(scope):
    print("Arming...")
    before_status = get_trigger_status(scope)
    before_sweep = visa_query(
        scope,
        ":TRIGger:SWEep?"
    ).upper()
    print(
        f"Before: status={before_status}, "
        f"sweep={before_sweep}"
    )
    print_trigger_configuration(scope)
    # Enter SINGLE mode.
    visa_write(scope, ":SINGle")
    start = time.monotonic()
    last_status = None
    saw_td = False
    while time.monotonic() - start < ARM_TIMEOUT_SECONDS:
        status = get_trigger_status(scope)
        if status != last_status:
            print(f"State: {status}")
            last_status = status
        # Normal case:
        # scope is armed and waiting for trigger.
        if status == "WAIT":
            print("Waiting for trigger...")
            return time.monotonic(), False
        # TD immediately after :SINGle can be a transient
        # state while changing from the previous acquisition.
        if status == "TD":
            saw_td = True
            time.sleep(0.05)
            continue
        # IMPORTANT:
        # If SINGLE goes directly to STOP without ever showing
        # WAIT, the trigger may have occurred immediately.
        #
        # If TD was observed first, this is definitely the
        # completed single acquisition.
        if status == "STOP":
            elapsed = time.monotonic() - start
            if saw_td:
                print(
                    f"Triggered immediately "
                    f"after {elapsed:.2f} s"
                )
            else:
                print(
                    f"Single acquisition completed "
                    f"immediately after {elapsed:.2f} s"
                )
            return time.monotonic(), True
        time.sleep(POLL_INTERVAL_SECONDS)
    final_status = get_trigger_status(scope)
    final_sweep = visa_query(
        scope,
        ":TRIGger:SWEep?"
    )
    print(
        f"Arm failed: status={final_status}, "
        f"sweep={final_sweep}"
    )
    print_trigger_configuration(scope)
    raise TimeoutError(
        f"Scope did not arm. "
        f"Final status={final_status!r}, "
        f"sweep={final_sweep!r}"
    )
def wait_for_trigger(scope, armed_time):
    while True:
        status = get_trigger_status(scope)
        # TD may be extremely short-lived.
        if status == "TD":
            elapsed = time.monotonic() - armed_time
            print(
                f"Triggered after {elapsed:.2f} s"
            )
            return
        # Once WAIT was confirmed, STOP means the
        # single acquisition has completed.
        if status == "STOP":
            elapsed = time.monotonic() - armed_time
            print(
                f"Triggered/acquisition complete "
                f"after {elapsed:.2f} s"
            )
            return
        if (
            time.monotonic() - armed_time
            >= TRIGGER_TIMEOUT_SECONDS
        ):
            raise TimeoutError(
                f"No trigger within "
                f"{TRIGGER_TIMEOUT_SECONDS} s"
            )
        time.sleep(POLL_INTERVAL_SECONDS)
# ========================= TCP =========================
def tcp_send(sock, command):
    sock.sendall(
        (command + "\n").encode("ascii")
    )
def tcp_query(sock, command):
    tcp_send(sock, command)
    data = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError(
                f"TCP connection closed waiting "
                f"for {command!r}"
            )
        data.extend(chunk)
        if b"\n" in chunk:
            break
    return bytes(data).split(
        b"\n",
        1
    )[0].decode("ascii").strip()
def tcp_read_exact(sock, number_of_bytes):
    data = bytearray()
    while len(data) < number_of_bytes:
        chunk = sock.recv(
            min(
                65536,
                number_of_bytes - len(data)
            )
        )
        if not chunk:
            raise RuntimeError(
                f"TCP connection closed after "
                f"{len(data)}/{number_of_bytes} bytes"
            )
        data.extend(chunk)
    return bytes(data)
def tcp_read_block(sock):
    prefix = tcp_read_exact(sock, 2)
    if prefix != b"#9":
        raise RuntimeError(
            f"Invalid RIGOL binary block prefix: "
            f"{prefix!r}"
        )
    try:
        byte_count = int(
            tcp_read_exact(sock, 9).decode("ascii")
        )
    except ValueError:
        raise RuntimeError(
            "Invalid RIGOL binary block length"
        )
    payload = tcp_read_exact(
        sock,
        byte_count
    )
    terminator = tcp_read_exact(
        sock,
        1
    )
    if terminator == b"\r":
        old_timeout = sock.gettimeout()
        try:
            sock.settimeout(0.1)
            try:
                next_byte = sock.recv(1)
                if next_byte not in (b"", b"\n"):
                    raise RuntimeError(
                        f"Unexpected byte after CR: "
                        f"{next_byte!r}"
                    )
            except socket.timeout:
                pass
        finally:
            sock.settimeout(old_timeout)
    elif terminator != b"\n":
        raise RuntimeError(
            f"Invalid binary terminator: "
            f"{terminator!r}"
        )
    return payload
# ========================= WAVEFORM =========================
def parse_preamble(preamble):
    parts = [
        item.strip()
        for item in preamble.split(",")
    ]
    if len(parts) < 10:
        raise RuntimeError(
            f"Unexpected waveform preamble: "
            f"{preamble!r}"
        )
    return {
        "format": int(parts[0]),
        "mode": int(parts[1]),
        "points": int(parts[2]),
        "count": int(parts[3]),
        "x_increment": float(parts[4]),
        "x_origin": float(parts[5]),
        "x_reference": float(parts[6]),
        "y_increment": float(parts[7]),
        "y_origin": float(parts[8]),
        "y_reference": float(parts[9])
    }
def acquire_raw_channel(ch):
    print(f"Reading CH{ch}...")
    sock = socket.create_connection(
        (TCP_HOST, TCP_PORT),
        timeout=TCP_CONNECT_TIMEOUT_SECONDS
    )
    sock.settimeout(
        TCP_READ_TIMEOUT_SECONDS
    )
    try:
        tcp_send(
            sock,
            f":WAVeform:SOURce CHANnel{ch}"
        )
        tcp_send(
            sock,
            ":WAVeform:MODE RAW"
        )
        tcp_send(
            sock,
            ":WAVeform:FORMat BYTE"
        )
        tcp_send(
            sock,
            f":WAVeform:POINts "
            f"{ACQUISITION_MEMORY}"
        )
        points_set = int(
            tcp_query(
                sock,
                ":WAVeform:POINts?"
            )
        )
        if points_set != ACQUISITION_MEMORY:
            raise RuntimeError(
                f"CH{ch}: scope accepted "
                f"{points_set} points instead of "
                f"{ACQUISITION_MEMORY}"
            )
        p = parse_preamble(
            tcp_query(
                sock,
                ":WAVeform:PREamble?"
            )
        )
        if p["points"] != ACQUISITION_MEMORY:
            raise RuntimeError(
                f"CH{ch}: preamble reports "
                f"{p['points']} points"
            )
        if p["format"] != 0:
            raise RuntimeError(
                f"CH{ch}: expected BYTE format, "
                f"got {p['format']}"
            )
        if p["mode"] != 2:
            raise RuntimeError(
                f"CH{ch}: expected RAW mode, "
                f"got {p['mode']}"
            )
        tcp_send(
            sock,
            ":WAVeform:RESet"
        )
        tcp_send(
            sock,
            ":WAVeform:BEGin"
        )
        raw_data = bytearray()
        while len(raw_data) < ACQUISITION_MEMORY:
            status = tcp_query(
                sock,
                ":WAVeform:STATus?"
            )
            status_parts = status.split(",")
            read_status = (
                status_parts[0]
                .strip()
                .upper()
            )
            points_read = (
                int(status_parts[1])
                if len(status_parts) > 1
                else -1
            )
            # Request the actual binary waveform data.
            tcp_send(
                sock,
                ":WAVeform:DATA?"
            )
            block = tcp_read_block(sock)
            raw_data.extend(block)
            if len(raw_data) > ACQUISITION_MEMORY:
                raise RuntimeError(
                    f"CH{ch}: received too much "
                    f"data ({len(raw_data)} samples)"
                )
            if len(raw_data) == ACQUISITION_MEMORY:
                break
            if read_status == "IDLE":
                raise RuntimeError(
                    f"CH{ch}: waveform reader finished "
                    f"at {len(raw_data)} samples "
                    f"(scope reports {points_read})"
                )
            time.sleep(0.01)
        tcp_send(
            sock,
            ":WAVeform:END"
        )
        if len(raw_data) != ACQUISITION_MEMORY:
            raise RuntimeError(
                f"CH{ch}: received "
                f"{len(raw_data)} samples"
            )
        print(
            f"CH{ch}: received "
            f"{len(raw_data)} samples"
        )
        voltages = [
            (
                value
                - p["y_reference"]
                - p["y_origin"]
            ) * p["y_increment"]
            for value in raw_data
        ]
        time_axis = [
            p["x_origin"]
            + i * p["x_increment"]
            for i in range(
                ACQUISITION_MEMORY
            )
        ]
        return voltages, time_axis
    finally:
        try:
            sock.close()
        except Exception:
            pass
# ========================= CHANNELS =========================
def get_enabled_channels(scope):
    channels = []
    for ch in CHANNELS_TO_ACQUIRE:
        if ch not in VALID_CHANNELS:
            continue
        state = visa_query(
            scope,
            f":CHANnel{ch}:DISPlay?"
        ).upper()
        if state in ("1", "ON"):
            channels.append(ch)
    if not channels:
        raise RuntimeError(
            "None of the requested channels "
            "are enabled"
        )
    print(f"Channels: {channels}")
    return channels
# ========================= CSV =========================
def save_csv(
    filename,
    time_axis,
    channel_data,
    channels
):
    with open(
        filename,
        "w",
        newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            ["Time (s)"]
            + [
                f"CH{ch} (V)"
                for ch in channels
            ]
        )
        writer.writerows(
            zip(
                time_axis,
                *[
                    channel_data[ch]
                    for ch in channels
                ]
            )
        )
    print(f"Saved: {filename}")
# ========================= PLOT =========================
def plot_waveforms(
    time_axis,
    channel_data,
    channels,
    time_div_seconds
):
    if time_div_seconds < 1e-6:
        factor = 1e9
        unit = "ns"
    elif time_div_seconds < 1e-3:
        factor = 1e6
        unit = "µs"
    elif time_div_seconds < 1:
        factor = 1e3
        unit = "ms"
    else:
        factor = 1
        unit = "s"
    x = [
        t * factor
        for t in time_axis
    ]
    div = time_div_seconds * factor
    fig, ax = plt.subplots(
        figsize=(10, 5)
    )
    for ch in channels:
        ax.plot(
            x,
            channel_data[ch],
            label=CHANNEL_DESCRIPTIONS.get(
                ch,
                f"Channel {ch}"
            ),
            color=RIGOL_COLORS.get(
                ch,
                "#000000"
            )
        )
    ax.xaxis.set_major_formatter(
        ticker.FormatStrFormatter("%g")
    )
    if div > 0:
        ax.xaxis.set_major_locator(
            ticker.MultipleLocator(div)
        )
    ax.set_title(
        f"Rigol Oscilloscope Data Capture "
        f"({div:g} {unit}/Div)"
    )
    ax.set_xlabel(
        f"Time ({unit})"
    )
    ax.set_ylabel(
        "Voltage (V)"
    )
    ax.grid(
        True,
        which="major",
        linestyle="--",
        color="gray",
        alpha=0.7
    )
    ax.legend()
    fig.tight_layout()
    base_filename = csv_filename.rsplit(".", 1)[0]
    fig.savefig(f"{base_filename}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"{base_filename}.pdf", bbox_inches="tight")
    plt.show()
# ========================= MAIN =========================
def main():
    rm = None
    scope = None
    channel_data = {}
    time_axis = []
    try:
        rm = pyvisa.ResourceManager()
        scope = rm.open_resource(
            VISA_ADDRESS
        )
        scope.timeout = 10000
        scope.write_termination = "\n"
        scope.read_termination = "\n"
        print(
            f"Connected: "
            f"{visa_query(scope, '*IDN?')}"
        )
        try:
            visa_write(
                scope,
                "*CLS"
            )
        except Exception:
            pass
        time_div = float(
            visa_query(
                scope,
                ":TIMebase:MAIN:SCALe?"
            )
        )
        memory = int(
            float(
                visa_query(
                    scope,
                    ":ACQuire:MDEPth?"
                )
            )
        )
        if memory != ACQUISITION_MEMORY:
            raise RuntimeError(
                f"Expected "
                f"{ACQUISITION_MEMORY} points, "
                f"scope reports {memory}"
            )
        channels = get_enabled_channels(
            scope
        )
        # ARM SINGLE
        armed_time, already_complete = (
            arm_single_acquisition(scope)
        )
        # WAIT FOR TRIGGER
        if not already_complete:
            wait_for_trigger(
                scope,
                armed_time
            )
        # READ RAW DATA
        if get_trigger_status(scope) != "STOP":
            raise RuntimeError(
                "Scope is not STOPPED after "
                "acquisition"
            )
        for ch in channels:
            voltages, current_time_axis = (
                acquire_raw_channel(ch)
            )
            if not time_axis:
                time_axis = current_time_axis
            elif len(current_time_axis) != len(
                time_axis
            ):
                raise RuntimeError(
                    f"CH{ch}: time axis "
                    f"length mismatch"
                )
            channel_data[ch] = voltages
        # SAVE CSV
        save_csv(
            csv_filename,
            time_axis,
            channel_data,
            channels
        )
        # PLOT
        plot_waveforms(
            time_axis,
            channel_data,
            channels,
            time_div
        )
        print("Done.")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as exc:
        print(
            f"\nERROR: "
            f"{type(exc).__name__}: {exc}"
        )
        if scope is not None:
            try:
                print(
                    f"Scope status: "
                    f"{get_trigger_status(scope)}"
                )
            except Exception:
                pass
        raise
    finally:
        if scope is not None:
            try:
                scope.close()
            except Exception:
                pass
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass
if __name__ == "__main__":
    main()
