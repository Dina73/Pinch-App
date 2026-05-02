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

# Input Table initialized with your specific data from Table 1
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

if st.button("Run Full Pinch Analysis"):
    # Split Data
    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    # --- CALCULATION ENGINE (Using Shifted Temps for Cascade) ---
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
        t_high, t_low = temps[i], temps[i+1]
        cp_hot = hot[(hot["Tin_shift"] >= t_high) & (hot["Tout_shift"] <= t_low)]["Cp"].sum()
        cp_cold = cold[(cold["Tout_shift"] >= t_high) & (cold["Tin_shift"] <= t_low)]["Cp"].sum()
        deltaH = (cp_hot - cp_cold) * (t_high - t_low)
        interval_data.append([t_high, t_low, cp_hot, cp_cold, deltaH])

    cascade_df = pd.DataFrame(interval_data, columns=["T_high", "T_low", "Cp_hot", "Cp_cold", "ΔH"])

    heat_vals = [0]
    for q in cascade_df["ΔH"]:
        heat_vals.append(heat_vals[-1] + q)

    min_heat = abs(min(heat_vals)) if min(heat_vals) < 0 else 0
    adjusted_cascade = [h + min_heat for h in heat_vals]
    min_cooling = adjusted_cascade[-1]

    # --- DISPLAY METRICS ---
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Min Heating (QH)", f"{round(min_heat, 2)} kW")
    col2.metric("Min Cooling (QC)", f"{round(min_cooling, 2)} kW")
    
    # --- CORRECTED PLOTTING (Actual Temperatures) ---
    st.write("### 2. Composite Curves")

    # 1. Separate actual temperatures for Hot and Cold composites
    h_all_t = sorted(list(set(list(hot["Tin"]) + list(hot["Tout"]))), reverse=True)
    c_all_t = sorted(list(set(list(cold["Tin"]) + list(cold["Tout"]))), reverse=False) # Ascending for cold

    # 2. Hot Composite: Calculated from Top to Bottom
    h_q, h_t_plot = [0], [h_all_t[0]]
    for i in range(len(h_all_t)-1):
        t_h, t_l = h_all_t[i], h_all_t[i+1]
        cp = hot[(hot["Tin"] >= t_h) & (hot["Tout"] <= t_l)]["Cp"].sum()
        h_q.append(h_q[-1] + cp * (t_h - t_l))
        h_t_plot.append(t_l)

    # 3. Cold Composite: Starts at min_heat offset (Calculated Bottom to Top)
    c_q, c_t_plot = [min_heat], [c_all_t[0]]
    for i in range(len(c_all_t)-1):
        t_l, t_h = c_all_t[i], c_all_t[i+1]
        cp = cold[(cold["Tout"] >= t_h) & (cold["Tin"] <= t_l)]["Cp"].sum()
        c_q.append(c_q[-1] + cp * (t_h - t_l))
        c_t_plot.append(t_h)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(h_q, h_t_plot, color='red', label='Hot Composite', linewidth=2.5, marker='o', markersize=4)
    ax.plot(c_q, c_t_plot, color='blue', label='Cold Composite', linewidth=2.5, marker='o', markersize=4)
    
    ax.set_xlabel("Enthalpy H (kW)")
    ax.set_ylabel("Temperature T (°C)")
    ax.set_title("Composite Curves (Corrected Enthalpy Offset)")
    ax.grid(True, which='both', linestyle=':', alpha=0.6)
    ax.legend()
    
    st.pyplot(fig)

    with st.expander("Show Detailed Cascade Tables"):
        st.write("#### Interval Net Heat Flow")
        st.dataframe(cascade_df)
