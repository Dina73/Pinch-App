import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Calculation Engine (Same as before to find qh correctly)
# ... [Assuming calculation of 'qh' is performed] ...

# 2. Final Plotting Logic (The Fix)
st.write("### Composite Curves")

# Hot Composite: Calculate High-to-Low, starting at 0
h_temps = sorted(list(set(list(hot["Tin"]) + list(hot["Tout"]))), reverse=True)
h_q, h_t = [0], [h_temps[0]]
for i in range(len(h_temps)-1):
    th, tl = h_temps[i], h_temps[i+1]
    cp = hot[(hot["Tin"] >= th) & (hot["Tout"] <= tl)]["Cp"].sum()
    h_q.append(h_q[-1] + cp * (th - tl))
    h_t.append(tl)

# Cold Composite: Calculate High-to-Low, STARTING AT qh
c_temps = sorted(list(set(list(cold["Tin"]) + list(cold["Tout"]))), reverse=True)
c_q, c_t = [qh], [c_temps[0]] # This 'qh' is the horizontal shift you need[cite: 1]
for i in range(len(c_temps)-1):
    th, tl = c_temps[i], c_temps[i+1]
    cp = cold[(cold["Tout"] >= th) & (cold["Tin"] <= tl)]["Cp"].sum()
    c_q.append(c_q[-1] + cp * (th - tl))
    c_t.append(tl)

# 3. Visualization
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(h_q, h_t, color='red', label='Hot Composite', linewidth=2)
ax.plot(c_q, c_t, color='blue', label='Cold Composite', linewidth=2)

ax.set_xlim(0, 100000)
ax.set_ylim(30, 150)
ax.set_xlabel("Enthalpy H (kW)")
ax.set_ylabel("Temperature T (°C)")
ax.grid(True, which='both', linestyle=':', alpha=0.6)
ax.legend()
st.pyplot(fig)
