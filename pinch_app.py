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

# Input Table with default values
data = st.data_editor(
    pd.DataFrame({
        "Stream": ["H1", "H2", "C1", "C2"],
        "Type": ["Hot", "Hot", "Cold", "Cold"],
        "Tin": [180, 150, 30, 60],
        "Tout": [40, 40, 150, 100],
        "Cp": [2.0, 3.0, 2.5, 3.0]
    }),
    num_rows="dynamic"
)

deltaT = st.number_input("Enter ΔTmin (°C)", value=10)

if st.button("Run Full Pinch Analysis"):
    # Split Data
    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    # --- CALCULATION ENGINE ---
    # Shift Temperatures for Cascade
    hot["Tin_shift"] = hot["Tin"] - deltaT/2
    hot["Tout_shift"] = hot["Tout"] - deltaT/2
    cold["Tin_shift"] = cold["Tin"] + deltaT/2
    cold["Tout_shift"] = cold["Tout"] + deltaT/2

    # Identify Temperature Intervals
    temps = sorted(list(set(
        list(hot["Tin_shift"]) + list(hot["Tout_shift"]) + 
        list(cold["Tin_shift"]) + list(cold["Tout_shift"])
    )), reverse=True)

    # Heat Cascade Calculation
    interval_data = []
    for i in range(len(temps)-1):
        t_high, t_low = temps[i], temps[i+1]
        
        # Check which streams exist in this interval
        cp_hot = hot[(hot["Tin_shift"] >= t_high) & (hot["Tout_shift"] <= t_low)]["Cp"].sum()
        cp_cold = cold[(cold["Tout_shift"] >= t_high) & (cold["Tin_shift"] <= t_low)]["Cp"].sum()
        
        deltaH = (cp_hot - cp_cold) * (t_high - t_low)
        interval_data.append([t_high, t_low, cp_hot, cp_cold, deltaH])

    cascade_df = pd.DataFrame(interval_data, columns=["T_high", "T_low", "Cp_hot", "Cp_cold", "ΔH"])

    # Calculate Cumulative Heat
    heat_vals = [0]
    for q in cascade_df["ΔH"]:
        heat_vals.append(heat_vals[-1] + q)

    # Determine Minimum Utilities
    min_heat = abs(min(heat_vals)) if min(heat_vals) < 0 else 0
    adjusted_cascade = [h + min_heat for h in heat_vals]
    min_cooling = adjusted_cascade[-1]

    # Find Pinch Temperature
    pinch_idx = adjusted_cascade.index(0)
    pinch_temp_shifted = temps[pinch_idx]

    # --- DISPLAY RESULTS ---
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Min Heating (QH)", f"{round(min_heat, 2)} kW")
    col2.metric("Min Cooling (QC)", f"{round(min_cooling, 2)} kW")
    col3.metric("Pinch (Shifted)", f"{pinch_temp_shifted} °C")

    # --- PLOTTING SECTION ---
    st.write("### 2. Visualization")
    plot_col1, plot_col2 = st.columns(2)

    with plot_col1:
        st.subheader("Composite Curves")
        # Use ACTUAL temps for Composite Curve display
        h_all_t = sorted(list(set(list(hot["Tin"]) + list(hot["Tout"]))), reverse=True)
        c_all_t = sorted(list(set(list(cold["Tin"]) + list(cold["Tout"]))), reverse=True)

        # Hot Composite Calculation
        h_q, h_t_plot = [0], [h_all_t[0]]
        for i in range(len(h_all_t)-1):
            t_h, t_l = h_all_t[i], h_all_t[i+1]
            cp = hot[(hot["Tin"] >= t_h) & (hot["Tout"] <= t_l)]["Cp"].sum()
            h_q.append(h_q[-1] + cp*(t_h - t_l))
            h_t_plot.append(t_l)

        # Cold Composite Calculation (Offset by min_heat)
        c_q, c_t_plot = [min_heat], [c_all_t[0]]
        for i in range(len(c_all_t)-1):
            t_h, t_l = c_all_t[i], c_all_t[i+1]
            cp = cold[(cold["Tout"] >= t_h) & (cold["Tin"] <= t_l)]["Cp"].sum()
            c_q.append(c_q[-1] + cp*(t_h - t_l))
            c_t_plot.append(t_l)

        fig1, ax1 = plt.subplots()
        ax1.plot(h_q, h_t_plot, color='red', label='Hot Composite', linewidth=2, marker='o')
        ax1.plot(c_q, c_t_plot, color='blue', label='Cold Composite', linewidth=2, marker='o')
        ax1.set_xlabel("Enthalpy (kW)")
        ax1.set_ylabel("Actual Temperature (°C)")
        ax1.grid(True, linestyle=':', alpha=0.6)
        ax1.legend()
        st.pyplot(fig1)

    with plot_col2:
        st.subheader("Grand Composite Curve")
        # GCC uses shifted temperatures
        fig2, ax2 = plt.subplots()
        ax2.plot(adjusted_cascade, temps, color='purple', linewidth=2)
        ax2.fill_betweenx(temps, adjusted_cascade, color='purple', alpha=0.1)
        ax2.set_xlabel("Net Heat Flow (kW)")
        ax2.set_ylabel("Shifted Temperature (°C)")
        ax2.grid(True, linestyle=':', alpha=0.6)
        # Mark the pinch point
        ax2.annotate(f'Pinch: {pinch_temp_shifted}°C', 
                     xy=(0, pinch_temp_shifted), xytext=(min_heat, pinch_temp_shifted+10),
                     arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5))
        st.pyplot(fig2)

    # Data Tables
    with st.expander("Show Detailed Calculation Tables"):
        st.write("#### Interval Analysis")
        st.dataframe(cascade_df)
        st.write("#### Final Heat Cascade")
        st.write(pd.DataFrame({"Shifted Temp": temps, "Net Heat": adjusted_cascade}))
