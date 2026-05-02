import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Pinch Analysis Tool", layout="wide")

st.title("Heat Integration & Pinch Analysis App")

st.sidebar.title("Heat Integration Tool")
st.sidebar.write("Pinch Analysis Application")
st.sidebar.write("Graduation Project")

st.write("### 1. Enter Stream Data")

# Pre-loaded with your specific data for convenience
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

if st.button("Generate Right Curve"):
    # 1. Calculation Engine (Shifted Temps for Cascade Analysis)
    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    hot["Tin_shift"] = hot["Tin"] - deltaT/2
    hot["Tout_shift"] = hot["Tout"] - deltaT/2
    cold["Tin_shift"] = cold["Tin"] + deltaT/2
    cold["Tout_shift"] = cold["Tout"] + deltaT/2

    temps = sorted(list(set(
        list(hot["Tin_shift"]) + list(hot["Tout_shift"]) + 
        list(cold["Tin_shift"]) + list(cold["Tout_shift"])
    )), reverse=True)

    interval_data = []
    for i in range(len(temps)-1):
        t_h, t_l = temps[i], temps[i+1]
        cp_h = hot[(hot["Tin_shift"] >= t_h) & (hot["Tout_shift"] <= t_l)]["Cp"].sum()
        cp_c = cold[(cold["Tout_shift"] >= t_h) & (cold["Tin_shift"] <= t_l)]["Cp"].sum()
        interval_data.append([t_h, t_l, (cp_h - cp_c) * (t_h - t_l)])

    cascade = [0]
    for _, _, dh in interval_data:
        cascade.append(cascade[-1] + dh)

    min_heat = abs(min(cascade)) if min(cascade) < 0 else 0
    min_cooling = cascade[-1] + min_heat

    # 2. Results Header
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Min Heating ($Q_H$)", f"{round(min_heat, 2)} kW")
    c2.metric("Min Cooling ($Q_C$)", f"{round(min_cooling, 2)} kW")

    # 3. Generating the Composite Curves (Actual Temps)
    st.write("### 2. Composite Curves")

    # Hot Curve Calculation
    h_temps = sorted(list(set(list(hot["Tin"]) + list(hot["Tout"]))), reverse=True)
    h_q, h_t_plot = [0], [h_temps[0]]
    for i in range(len(h_temps)-1):
        t_h, t_l = h_temps[i], h_temps[i+1]
        cp = hot[(hot["Tin"] >= t_h) & (hot["Tout"] <= t_l)]["Cp"].sum()
        h_q.append(h_q[-1] + cp * (t_h - t_l))
        h_t_plot.append(t_l)

    # Cold Curve Calculation (Offset by min_heat to create the 'right' curve)
    c_temps = sorted(list(set(list(cold["Tin"]) + list(cold["Tout"]))), reverse=False)
    c_q, c_t_plot = [min_heat], [c_temps[0]]
    for i in range(len(c_temps)-1):
        t_l, t_h = c_temps[i], c_temps[i+1]
        cp = cold[(cold["Tout"] >= t_h) & (cold["Tin"] <= t_l)]["Cp"].sum()
        c_q.append(c_q[-1] + cp * (t_h - t_l))
        c_t_plot.append(t_h)

    # Plotting
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(h_q, h_t_plot, color='red', label='Hot Composite', linewidth=2.5)
    ax.plot(c_q, c_t_plot, color='blue', label='Cold Composite', linewidth=2.5)
    
    ax.set_xlabel("Enthalpy H (kW)")
    ax.set_ylabel("Temperature T (°C)")
    ax.set_title("Corrected Composite Curves")
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend()
    
    st.pyplot(fig)
