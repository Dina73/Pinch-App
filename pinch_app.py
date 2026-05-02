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

if st.button("Generate Composite Curves"):
    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    # 2. Pinch Calculations (Shifted Temperatures)
    hot["Ts"] = hot["Tin"] - deltaT/2
    hot["Tt"] = hot["Tout"] - deltaT/2
    cold["Ts"] = cold["Tin"] + deltaT/2
    cold["Tt"] = cold["Tout"] + deltaT/2

    temps = sorted(list(set(list(hot["Ts"]) + list(hot["Tt"]) + list(cold["Ts"]) + list(cold["Tt"]))), reverse=True)
    
    dh_intervals = []
    for i in range(len(temps)-1):
        th, tl = temps[i], temps[i+1]
        cp_h = hot[(hot["Ts"] >= th) & (hot["Tt"] <= tl)]["Cp"].sum()
        cp_c = cold[(cold["Tt"] >= th) & (cold["Ts"] <= tl)]["Cp"].sum()
        dh_intervals.append((cp_h - cp_c) * (th - tl))

    cascade = [0]
    for dh in dh_intervals:
        cascade.append(cascade[-1] + dh)
    
    min_heat = abs(min(cascade)) if min(cascade) < 0 else 0

    # 3. Plotting Composite Curves (Actual Temperatures)
    # Hot Composite: Calculate from Top to Bottom
    h_all_t = sorted(list(set(list(hot["Tin"]) + list(hot["Tout"]))), reverse=True)
    h_q, h_t_plot = [0], [h_all_t[0]]
    for i in range(len(h_all_t)-1):
        th, tl = h_all_t[i], h_all_t[i+1]
        cp = hot[(hot["Tin"] >= th) & (hot["Tout"] <= tl)]["Cp"].sum()
        h_q.append(h_q[-1] + cp * (th - tl))
        h_t_plot.append(tl)

    # Cold Composite: Calculate from Bottom to Top, starting at min_heat
    c_all_t = sorted(list(set(list(cold["Tin"]) + list(cold["Tout"]))), reverse=False)
    c_q, c_t_plot = [min_heat], [c_all_t[0]]
    for i in range(len(c_all_t)-1):
        tl, th = c_all_t[i], c_all_t[i+1]
        cp = cold[(cold["Tout"] >= th) & (cold["Tin"] <= tl)]["Cp"].sum()
        c_q.append(c_q[-1] + cp * (th - tl))
        c_t_plot.append(th)

    # Visualization[cite: 1]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(h_q, h_t_plot, color='red', label='Hot Composite', linewidth=1.5)
    ax.plot(c_q, c_t_plot, color='blue', label='Cold Composite', linewidth=1.5)
    
    # Matching the 'clear one.jpg' style
    ax.set_xlim(0, 100000)
    ax.set_ylim(30, 200)
    ax.set_xticks(np.arange(0, 110000, 10000))
    ax.set_yticks(np.arange(30, 210, 20))
    ax.set_xlabel("H (kW)")
    ax.set_ylabel("T (°C)")
    ax.grid(True, which='both', color='gray', linestyle='-', linewidth=0.5)
    ax.legend()
    
    st.pyplot(fig)
