import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Heat Integration & Pinch Analysis App")

st.sidebar.title("Heat Integration Tool")
st.sidebar.write("Pinch Analysis Application")
st.sidebar.write("Graduation Project")

st.write("Enter Stream Data")

# Input Table
data = st.data_editor(
    pd.DataFrame({
        "Stream": ["H1", "C1"],
        "Type": ["Hot", "Cold"],
        "Tin": [180, 30],
        "Tout": [40, 150],
        "Cp": [2.3, 1.8]
    }),
    num_rows="dynamic"
)

deltaT = st.number_input("Enter ΔTmin", value=10.0)

if st.button("Calculate Pinch"):

    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    # 🔵 Shift Temperatures
    hot["Tin_shift"] = hot["Tin"] - deltaT/2
    hot["Tout_shift"] = hot["Tout"] - deltaT/2

    cold["Tin_shift"] = cold["Tin"] + deltaT/2
    cold["Tout_shift"] = cold["Tout"] + deltaT/2

    st.subheader("Shifted Temperatures")
    st.write(pd.concat([hot, cold]))

    # 🔵 Unique temperature levels
    temps = list(hot["Tin_shift"]) + list(hot["Tout_shift"]) + \
            list(cold["Tin_shift"]) + list(cold["Tout_shift"])

    temps = sorted(set(temps), reverse=True)

    st.subheader("Temperature Intervals")
    st.write(temps)

    # 🔵 Heat Cascade Table (FIXED LOGIC)
    interval_data = []

    for i in range(len(temps)-1):

        t_high = temps[i]
        t_low = temps[i+1]
        dT = t_high - t_low

        # ✅ FIX: overlap logic
        cp_hot = hot[
            (hot["Tin_shift"] > t_low) & (hot["Tout_shift"] < t_high)
        ]["Cp"].sum()

        cp_cold = cold[
            (cold["Tout_shift"] > t_low) & (cold["Tin_shift"] < t_high)
        ]["Cp"].sum()

        deltaH = (cp_hot - cp_cold) * dT

        interval_data.append([t_high, t_low, cp_hot, cp_cold, deltaH])

    cascade = pd.DataFrame(
        interval_data,
        columns=["T_high","T_low","Cp_hot","Cp_cold","ΔH"]
    )

    st.subheader("Heat Cascade Table")
    st.write(cascade)

    # 🔵 Heat Cascade Calculation
    heat = [0]
    for q in cascade["ΔH"]:
        heat.append(heat[-1] + q)

    cascade["Heat Cascade"] = heat[1:]

    st.subheader("Heat Cascade")
    st.write(cascade)

    # 🔵 Utilities
    min_heat = abs(min(heat))
    adjusted = [h + min_heat for h in heat]
    min_cooling = adjusted[-1]

    st.subheader("Minimum Heating Required")
    st.write(min_heat)

    st.subheader("Minimum Cooling Required")
    st.write(min_cooling)

    # 🔵 Pinch Temperature
    pinch_index = adjusted.index(min(adjusted))
    pinch_temp = temps[pinch_index]

    st.subheader("Pinch Temperature")
    st.success(pinch_temp)

    # =========================================================
    # 🔥 COMPOSITE CURVES (FULLY FIXED)
    # =========================================================

    st.subheader("Composite Curves")

    hot_streams = [(r["Tin_shift"], r["Tout_shift"], r["Cp"]) for _, r in hot.iterrows()]
    cold_streams = [(r["Tin_shift"], r["Tout_shift"], r["Cp"]) for _, r in cold.iterrows()]

    all_temps = temps

    hot_q = [0]
    cold_q = [min_heat]   # 🔥 critical fix

    for i in range(len(all_temps) - 1):

        t_high = all_temps[i]
        t_low = all_temps[i+1]
        dT = t_high - t_low

        cp_hot = sum(cp for tin, tout, cp in hot_streams
                     if tin > t_low and tout < t_high)

        cp_cold = sum(cp for tin, tout, cp in cold_streams
                      if tout > t_low and tin < t_high)

        hot_q.append(hot_q[-1] + cp_hot * dT)
        cold_q.append(cold_q[-1] + cp_cold * dT)

    plt.figure()

    plt.plot(hot_q, all_temps, marker='o', label="Hot Composite")
    plt.plot(cold_q, all_temps, marker='o', label="Cold Composite")

    plt.xlabel("Cumulative Heat (Q)")
    plt.ylabel("Shifted Temperature")

    plt.gca().invert_yaxis()
    plt.legend()
    plt.grid()

    st.pyplot(plt)

    # =========================================================
    # 🔵 GRAND COMPOSITE CURVE
    # =========================================================

    st.subheader("Grand Composite Curve")

    plt.figure()
    plt.step(adjusted, temps + [temps[-1]], where="post")

    plt.xlabel("Net Heat Flow")
    plt.ylabel("Temperature")

    plt.gca().invert_yaxis()
    plt.grid()

    st.pyplot(plt)

    # =========================================================
    # 🔵 SIMPLE MATCHING (unchanged logic)
    # =========================================================

    st.subheader("Heat Exchanger Matching")

    matches = []

    for _, h in hot.iterrows():
        for _, c in cold.iterrows():

            if h["Tin"] > c["Tout"]:

                Q_hot = h["Cp"] * (h["Tin"] - h["Tout"])
                Q_cold = c["Cp"] * (c["Tout"] - c["Tin"])

                Q = min(Q_hot, Q_cold)

                if Q > 0:
                    matches.append([h["Stream"], c["Stream"], round(Q,2)])

    if matches:
        match_df = pd.DataFrame(matches,
            columns=["Hot Stream","Cold Stream","Heat Exchange"])
        st.write(match_df)
    else:
        st.write("No feasible matches found")

    # 🔵 Utilities Summary
    st.subheader("Utility Targets")

    col1, col2 = st.columns(2)
    col1.metric("Minimum Heating", round(min_heat,2))
    col2.metric("Minimum Cooling", round(min_cooling,2))
