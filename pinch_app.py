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
        "Tin": [118.0, 103.0, 30.0, 65.0],
        "Tout": [103.0, 84.0, 65.0, 85.0],
        "Cp": [3116.4, 1148.4, 519.5, 485.1]
    }),
    num_rows="dynamic"
)

deltaT = st.number_input("Enter ΔTmin (°C)", value=10.0)

# -----------------------------
# Utilities
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
        st.error("Requires both Hot and Cold streams for Pinch Analysis.")
        st.stop()

    # 1. Problem Table Method (Shifted)
    all_shifted = shift_temps(all_df, deltaT)
    hot_s = all_shifted[all_shifted["Type"] == "Hot"]
    cold_s = all_shifted[all_shifted["Type"] == "Cold"]
    
    temps_s = sorted(set(all_shifted["Tin_shift"].tolist() + all_shifted["Tout_shift"].tolist()), reverse=True)
    intervals = list(zip(temps_s[:-1], temps_s[1:]))

    interval_heat = []
    for Th, Tl in intervals:
        dT = Th - Tl
        Cp_h = interval_cp_full_coverage(hot_s, Th, Tl)
        Cp_c = interval_cp_full_coverage(cold_s, Th, Tl)
        dH = (Cp_h - Cp_c) * dT
        interval_heat.append(dH)

    # 2. Heat Cascade & Utility Targets
    heat_points = [0.0]
    for dh in interval_heat:
        heat_points.append(heat_points[-1] + dh)
    
    min_heat = min(heat_points)
    min_heating_required = -min_heat if min_heat < 0 else 0.0
    adj_cascade = [h + min_heating_required for h in heat_points]
    min_cooling_required = adj_cascade[-1]

    # 3. Find Pinch
    pinch_idx = adj_cascade.index(min(adj_cascade))
    pinch_temp_s = temps_s[pinch_idx]

    # 4. Results Metrics
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Shifted Pinch Temp", f"{pinch_temp_s} °C")
    col2.metric("Min Heating ($Q_{H,min}$)", f"{min_heating_required:,.2f} kW")
    col3.metric("Min Cooling ($Q_{C,min}$)", f"{min_cooling_required:,.2f} kW")

    # 5. Composite Curves Logic (Robust version)
    def build_composite(df_type):
        # Sort temperatures from low to high to build enthalpy cumulatively
        t_pts = sorted(set(df_type["Tin"].tolist() + df_type["Tout"].tolist()))
        q_cum = [0.0]
        for i in range(len(t_pts)-1):
            t_low, t_high = t_pts[i], t_pts[i+1]
            cp_sum = sum(r["Cp"] for _, r in df_type.iterrows() 
                         if min(r["Tin"], r["Tout"]) <= t_low and max(r["Tin"], r["Tout"]) >= t_high)
            q_cum.append(q_cum[-1] + cp_sum * (t_high - t_low))
        return np.array(q_cum), np.array(t_pts)

    h_q, h_t = build_composite(hot)
    c_q, c_t = build_composite(cold)

    # SHIFT COLD CURVE: Move the blue line by the cooling utility requirement
    c_q_shifted = c_q + min_cooling_required

    # 6. Plots
    st.write("### Process Visualization")
    plot_col1, plot_col2 = st.columns(2)

    with plot_col1:
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
        fig2, ax2 = plt.subplots()
        ax2.plot(adj_cascade, temps_s, 'g-o', label="Grand Composite", markersize=4)
        ax2.axvline(0, color='black', linewidth=1, linestyle='--')
        ax2.set_xlabel("Net Heat Flow (kW)")
        ax2.set_ylabel("Shifted Temperature (°C)")
        ax2.set_title("Grand Composite Curve")
        ax2.grid(True, linestyle='--', alpha=0.6)
        ax2.legend()
        st.pyplot(fig2)

    st.success(f"Pinch Point: Hot {pinch_temp_s + deltaT/2}°C | Cold {pinch_temp_s - deltaT/2}°C")
