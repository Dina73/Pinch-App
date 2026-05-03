import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# App Title and Sidebar
st.set_page_config(page_title="Pinch Analysis Tool", layout="wide")
st.title("Heat Integration & Pinch Analysis App")

st.sidebar.title("Heat Integration Tool")
st.sidebar.write("Pinch Analysis Application")
st.sidebar.write("Graduation Project")

st.write("### Enter Stream Data")

# Input Data Editor
data = st.data_editor(
    pd.DataFrame({
        "Stream": ["H1", "H2", "C1", "C2"],
        "Type": ["Hot", "Hot", "Cold", "Cold"],
        "Tin": [180.0, 150.0, 30.0, 60.0],
        "Tout": [40.0, 60.0, 150.0, 170.0],
        "Cp": [2.3, 1.5, 1.8, 2.0]
    }),
    num_rows="dynamic"
)

deltaT = st.number_input("Enter ΔTmin (°C)", value=10.0)

# -----------------------------
# Utilities & Calculation Logic
# -----------------------------
def shift_temps(df, dTmin):
    df = df.copy()
    df["Tin_shift"] = np.where(df["Type"] == "Hot", df["Tin"] - dTmin/2, df["Tin"] + dTmin/2)
    df["Tout_shift"] = np.where(df["Type"] == "Hot", df["Tout"] - dTmin/2, df["Tout"] + dTmin/2)
    return df

def interval_cp_full_coverage(streams_df, Th, Tl):
    total = 0.0
    for _, r in streams_df.iterrows():
        s1, s2 = r["Tin_shift"], r["Tout_shift"]
        span_high, span_low = max(s1, s2), min(s1, s2)
        if (span_high >= Th) and (span_low <= Tl):
            total += float(r["Cp"])
    return total

def get_composite_data(df_type):
    # Uses ACTUAL temperatures for the Composite Curve visualization
    t_points = sorted(set(df_type["Tin"].tolist() + df_type["Tout"].tolist()), reverse=True)
    q_values = [0.0]
    t_values = [t_points[0]]
    
    for i in range(len(t_points)-1):
        Th, Tl = t_points[i], t_points[i+1]
        dT = Th - Tl
        cp_sum = sum(row["Cp"] for _, row in df_type.iterrows() 
                     if max(row["Tin"], row["Tout"]) >= Th and min(row["Tin"], row["Tout"]) <= Tl)
        q_values.append(q_values[-1] + cp_sum * dT)
        t_values.append(Tl)
    return np.array(q_values), np.array(t_values)

# -----------------------------
# Main Calculation
# -----------------------------
if st.button("Calculate Pinch"):
    if data is None or data.empty:
        st.error("Please enter stream data.")
        st.stop()

    all_df = data.copy()
    hot = all_df[all_df["Type"] == "Hot"].copy()
    cold = all_df[all_df["Type"] == "Cold"].copy()

    if hot.empty or cold.empty:
        st.error("Requires both Hot and Cold streams to perform Pinch Analysis.")
        st.stop()

    # 1. Problem Table Method (using Shifted Temperatures)
    all_shifted = shift_temps(all_df, deltaT)
    hot_s = all_shifted[all_shifted["Type"] == "Hot"]
    cold_s = all_shifted[all_shifted["Type"] == "Cold"]
    
    # Create temperature grid from shifted endpoints
    temps = sorted(set(all_shifted["Tin_shift"].tolist() + all_shifted["Tout_shift"].tolist()), reverse=True)
    intervals = list(zip(temps[:-1], temps[1:]))

    # Calculate net heat flow per interval
    interval_rows = []
    for Th, Tl in intervals:
        dT = Th - Tl
        Cp_h = interval_cp_full_coverage(hot_s, Th, Tl)
        Cp_c = interval_cp_full_coverage(cold_s, Th, Tl)
        dH = (Cp_h - Cp_c) * dT
        interval_rows.append(dH)

    # 2. Heat Cascade & Utility Targets
    heat_points = [0.0]
    for dh in interval_rows:
        heat_points.append(heat_points[-1] + dh)
    
    min_heat = min(heat_points)
    min_heating_required = -min_heat if min_heat < 0 else 0.0
    adj_cascade = [h + min_heating_required for h in heat_points]
    min_cooling_required = adj_cascade[-1]

    # 3. Results Metrics
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    # Find Pinch Index (where adjusted cascade is zero)
    pinch_idx = adj_cascade.index(min(adj_cascade))
    pinch_temp_s = temps[pinch_idx]
    
    col1.metric("Shifted Pinch Temp", f"{pinch_temp_s} °C")
    col2.metric("Min Heating Required", f"{min_heating_required:,.2f} kW")
    col3.metric("Min Cooling Required", f"{min_cooling_required:,.2f} kW")

    # 4. Process Plots
    st.write("### Process Visualization")
    plot_col1, plot_col2 = st.columns(2)

    with plot_col1:
        # Composite Curves (Actual T vs Cumulative Q)
        h_q, h_t = get_composite_data(hot)
        c_q, c_t = get_composite_data(cold)
        
        # Shift the cold curve horizontally by the cooling target
        c_q_shifted = c_q + min_cooling_required

        fig1, ax1 = plt.subplots()
        ax1.plot(h_q, h_t, 'r-o', label="Hot Composite", markersize=4)
        ax1.plot(c_q_shifted, c_t, 'b-o', label="Cold Composite", markersize=4)
        ax1.set_xlabel("Enthalpy (kW)")
        ax1.set_ylabel("Temperature (°C)")
        ax1.set_title("Composite Curves")
        ax1.grid(True, linestyle='--', alpha=0.6)
        ax1.legend()
        st.pyplot(fig1)

    with plot_col2:
        # Grand Composite Curve (Shifted T vs Net Q)
        fig2, ax2 = plt.subplots()
        ax2.plot(adj_cascade, temps, 'g-o', label="Grand Composite", markersize=4)
        ax2.axvline(0, color='black', linewidth=1, linestyle='--')
        ax2.set_xlabel("Net Heat Flow (kW)")
        ax2.set_ylabel("Shifted Temperature (°C)")
        ax2.set_title("Grand Composite Curve")
        ax2.grid(True, linestyle='--', alpha=0.6)
        ax2.legend()
        st.pyplot(fig2)

    st.success(f"Pinch Point Details: Hot Stream Side = {pinch_temp_s + deltaT/2}°C | Cold Stream Side = {pinch_temp_s - deltaT/2}°C")
