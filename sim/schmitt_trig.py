VDD = 3.3

VOH = VDD - 50e-3
VOL = 50e-3

R2 = 3.3e3
R3 = 10e3

RF = 10e3 #größerer Wert: größere Hysterese

R23 = R2*R2/(R2+R3)
V23 = VDD * R3/(R2+R3)

VTHL = VOH * R23/(R23+RF) + V23*RF/(R23+RF)
VTLH = VOL * R23/(R23+RF) + V23*RF/(R23+RF)


print(f"VTHL: {VTHL}")
print(f"VTLH: {VTLH}")
print(f"Switching center: {(VTHL+VTLH)/2}")
print(f"Hysterese: {VTHL-VTLH}")
