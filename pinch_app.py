import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Heat Integration & Pinch Analysis App")

st.sidebar.title("Heat Integration Tool")
st.sidebar.write("Pinch Analysis Application")
st.sidebar.write("Graduation Project")

st.write("Enter Stream Data")

# =============================
# INPUT TABLE
# =============================
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

# =============================
# MAIN BUTTON
# =============================
if st.button("Calculate Pinch"):

    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    # =============================
    # SHIFT TEMPERATURES
    # =============================
    hot["Tin_s"] = hot["Tin"] - deltaT/2
    hot["Tout_s"] = hot["Tout"] - deltaT/2

    cold["Tin_s"] = cold["Tin"] + deltaT/2
    cold["Tout_s"] = cold["Tout"] + deltaT/2

    st.subheader("Shifted Temperatures")
    st.write(pd.concat([hot, cold]))

    # =============================
    # TEMPERATURE LEVELS
    # =============================
    temps = sorted(set(
        list(hot["Tin_s"]) + list(hot["Tout_s"]) +
        list(cold["Tin_s"]) + list(cold["Tout_s"])
    ), reverse=True)

    st.subheader("Temperature Intervals")
    st.write(temps)

    # =============================
    # HEAT CASCADE
    # =============================
    intervals = []

    for i in range(len(temps)-1):

        t_high = temps[i]
        t_low = temps[i+1]
        dT = t_high - t_low

        cp_hot = hot[
            (hot["Tin_s"] > t_low) & (hot["Tout_s"] < t_high)
        ]["Cp"].sum()

        cp_cold = cold[
            (cold["Tout_s"] > t_low) & (cold["Tin_s"] < t_high)
        ]["Cp"].sum()

        dH = (cp_hot - cp_cold) * dT

        intervals.append([t_high, t_low, cp_hot, cp_cold, dH])

    cascade = pd.DataFrame(
        intervals,
        columns=["T_high","T_low","Cp_hot","Cp_cold","ΔH"]
    )

    st.subheader("Heat Cascade Table")
    st.write(cascade)

    # =============================
    # CASCADE ACCUMULATION
    # =============================
    heat = [0]
    for q in cascade["ΔH"]:
        heat.append(heat[-1] + q)

    cascade["Heat Cascade"] = heat[1:]
    st.write(cascade)

    # =============================
    # UTILITIES
    # =============================
    min_heat = abs(min(heat))
    adjusted = [h + min_heat for h in heat]
    min_cooling = adjusted[-1]

    st.subheader("Minimum Heating Required")
    st.write(min_heat)

    st.subheader("Minimum Cooling Required")
    st.write(min_cooling)

    # =============================
    # PINCH (FIXED)
    # =============================
    pinch_index = adjusted[:-1].index(min(adjusted[:-1]))
    pinch_temp = temps[pinch_index]

    st.subheader("Pinch Temperature")
    st.success(pinch_temp)

    # =============================
    # COMPOSITE CURVES
    # =============================
    st.subheader("Composite Curves")

    hot_streams = [(r["Tin_s"], r["Tout_s"], r["Cp"]) for _, r in hot.iterrows()]
    cold_streams = [(r["Tin_s"], r["Tout_s"], r["Cp"]) for _, r in cold.iterrows()]

    hot_q = [0]
    cold_q = [min_heat]

    for i in range(len(temps)-1):

        t_high = temps[i]
        t_low = temps[i+1]
        dT = t_high - t_low

        cp_hot = sum(cp for tin, tout, cp in hot_streams
                     if tin > t_low and tout < t_high)

        cp_cold = sum(cp for tin, tout, cp in cold_streams
                      if tout > t_low and tin < t_high)

        hot_q.append(hot_q[-1] + cp_hot * dT)
        cold_q.append(cold_q[-1] + cp_cold * dT)

    plt.figure()

    plt.plot(hot_q, temps, marker='o', label="Hot Composite")
    plt.plot(cold_q, temps, marker='o', label="Cold Composite")

    # Pinch marker
    plt.scatter(min_heat, pinch_temp, s=100, label="Pinch Point")

    plt.xlabel("Cumulative Heat (Q)")
    plt.ylabel("Shifted Temperature")

    plt.gca().invert_yaxis()
    plt.legend()
    plt.grid()

    st.pyplot(plt)

    # =============================
    # GRAND COMPOSITE CURVE (FINAL FIX)
    # =============================
    st.subheader("Grand Composite Curve")

    gcc_heat = adjusted[:-1]   # align with temps
    gcc_temp = temps

    plt.figure()
    plt.step(gcc_heat, gcc_temp, where="post")

    plt.xlabel("Net Heat Flow")
    plt.ylabel("Shifted Temperature")

    plt.gca().invert_yaxis()
    plt.grid()

    st.pyplot(plt)

    # =============================
    # SUMMARY
    # =============================
    st.subheader("Utility Targets")

    col1, col2 = st.columns(2)
    col1.metric("Minimum Heating", round(min_heat,2))
    col2.metric("Minimum Cooling", round(min_cooling,2))
