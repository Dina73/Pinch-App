import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Pinch Analysis Tool", layout="wide")
st.title("Heat Integration & Pinch Analysis App")

# 1. Input Section
data = st.data_editor(
    pd.DataFrame({
        "Stream": ["H1", "H2", "H3", "H4", "H5", "H6", "C1", "C2", "C3", "C4", "C5"],
        "Type": ["Hot", "Hot", "Hot", "Hot", "Hot", "Hot", "Cold", "Cold", "Cold", "Cold", "Cold"],
        "Tin": [118, 103, 84, 118, 104, 85, 30, 65, 85, 95, 110],
        "Tout": [103, 84, 53, 104, 85, 54, 65, 85, 105, 110, 118],
        "Cp": [3116.4, 1148.4, 360.5, 194.0, 155.1, 113.2, 519.5, 485.1, 450.1, 417.6, 302.9]
    }),
    num_rows="dynamic"
)

deltaT = st.number_input("Enter ΔTmin (°C)", value=10)

if st.button("Generate Final Correct Curve"):
    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    # --- CALCULATION ENGINE ---
    # Shifted temps for Cascade
    hot["Ts_shift"] = hot["Tin"] - deltaT/2
    hot["Tt_shift"] = hot["Tout"] - deltaT/2
    cold["Ts_shift"] = cold["Tin"] + deltaT/2
    cold["Tt_shift"] = cold["Tout"] + deltaT/2

    # Get all shifted temperature breakpoints
    temps_shifted = sorted(list(set(list(hot["Ts_shift"]) + list(hot["Tt_shift"]) + 
                                    list(cold["Ts_shift"]) + list(cold["Tt_shift"]))), reverse=True)

    # Calculate intervals and QH
    dh_intervals = []
    for i in range(len(temps_shifted)-1):
        th, tl = temps_shifted[i], temps_shifted[i+1]
        cp_h = hot[(hot["Ts_shift"] >= th) & (hot["Tt_shift"] <= tl)]["Cp"].sum()
        cp_c = cold[(cold["Tt_shift"] >= th) & (cold["Ts_shift"] <= tl)]["Cp"].sum()
        dh_intervals.append((cp_h - cp_c) * (th - tl))

    cascade = [0]
    for dh in dh_intervals:
        cascade.append(cascade[-1] + dh)
    
    qh = abs(min(cascade)) if min(cascade) < 0 else 0

    # --- PLOTTING LOGIC (The "Clear One" Method) ---
    # We must use actual temperatures and cumulative enthalpy[cite: 1]
    
    # 1. Hot Composite[cite: 1]
    h_temps = sorted(list(set(list(hot["Tin"]) + list(hot["Tout"]))), reverse=True)
    h_q_plot, h_t_plot = [0], [h_temps[0]]
    for i in range(len(h_temps)-1):
        th, tl = h_temps[i], h_temps[i+1]
        cp = hot[(hot["Tin"] >= th) & (hot["Tout"] <= tl)]["Cp"].sum()
        h_q_plot.append(h_q_plot[-1] + cp * (th - tl))
        h_t_plot.append(tl)

    # 2. Cold Composite[cite: 1]
    c_temps = sorted(list(set(list(cold["Tin"]) + list(cold["Tout"]))), reverse=True)
    c_q_plot, c_t_plot = [qh], [c_temps[0]] # Start at QH offset[cite: 1]
    for i in range(len(c_temps)-1):
        th, tl = c_temps[i], c_temps[i+1]
        cp = cold[(cold["Tout"] >= th) & (cold["Tin"] <= tl)]["Cp"].sum()
        c_q_plot.append(c_q_plot[-1] + cp * (th - tl))
        c_t_plot.append(tl)

    # 3. Professional Visualization[cite: 1]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(h_q_plot, h_t_plot, color='red', label='Hot Composite', linewidth=1.5)
    ax.plot(c_q_plot, c_t_plot, color='blue', label='Cold Composite', linewidth=1.5)
    
    # Match "clear one" grid and scale[cite: 1]
    ax.set_xlim(0, 100000)
    ax.set_ylim(30, 200)
    ax.set_xticks(np.arange(0, 110000, 10000))
    ax.set_yticks(np.arange(30, 210, 20))
    ax.set_xlabel("Enthalpy H (kW)")
    ax.set_ylabel("Temperature T (°C)")
    ax.grid(True, which='both', color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
    ax.legend()
    
    st.pyplot(fig)
