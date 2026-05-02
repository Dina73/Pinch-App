import streamlit as st
import pandas as pd
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

    # =============================
    # 🔵 SHIFT TEMPERATURES
    # =============================
    hot["Tin_shift"] = hot["Tin"] - deltaT/2
    hot["Tout_shift"] = hot["Tout"] - deltaT/2

    cold["Tin_shift"] = cold["Tin"] + deltaT/2
    cold["Tout_shift"] = cold["Tout"] + deltaT/2

    st.subheader("Shifted Temperatures")
    st.write(pd.concat([hot, cold]))

    # =============================
    # 🔵 TEMPERATURE LEVELS
    # =============================
    temps = sorted(set(
        list(hot["Tin_shift"]) + list(hot["Tout_shift"]) +
        list(cold["Tin_shift"]) + list(cold["Tout_shift"])
    ), reverse=True)

    st.subheader("Temperature Intervals")
    st.write(temps)

    # =============================
    # 🔵 HEAT CASCADE
    # =============================
    interval_data = []

    for i in range(len(temps)-1):

        t_high = temps[i]
        t_low = temps[i+1]
        dT = t_high - t_low

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

    # Cascade accumulation
    heat = [0]
    for q in cascade["ΔH"]:
        heat.append(heat[-1] + q)

    cascade["Heat Cascade"] = heat[1:]
    st.write(cascade)

    # =============================
    # 🔵 UTILITIES
    # =============================
    min_heat = abs(min(heat))
    adjusted = [h + min_heat for h in heat]
    min_cooling = adjusted[-1]

    st.subheader("Minimum Heating Required")
    st.write(min_heat)

    st.subheader("Minimum Cooling Required")
    st.write(min_cooling)

    # =============================
    # 🔵 PINCH
    # =============================
    pinch_index = adjusted.index(min(adjusted))
    pinch_temp = temps[pinch_index]

    st.subheader("Pinch Temperature")
    st.success(pinch_temp)

    # =============================
    # 🔥 COMPOSITE CURVES
    # =============================
    st.subheader("Composite Curves")

    hot_streams = [(r["Tin_shift"], r["Tout_shift"], r["Cp"]) for _, r in hot.iterrows()]
    cold_streams = [(r["Tin_shift"], r["Tout_shift"], r["Cp"]) for _, r in cold.iterrows()]

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

    # 🔥 Plot + pinch point
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
    # 🔵 GRAND COMPOSITE CURVE (FIXED)
    # =============================
    st.subheader("Grand Composite Curve")

    gcc_heat = adjusted[:-1]   # fix length mismatch
    gcc_temp = temps

    plt.figure()

    plt.step(gcc_heat, gcc_temp, where="post")

    plt.xlabel("Net Heat Flow")
    plt.ylabel("Shifted Temperature")

    plt.gca().invert_yaxis()
    plt.grid()

    st.pyplot(plt)

    # =============================
    # 🔵 UTILITIES SUMMARY
    # =============================
    st.subheader("Utility Targets")

    col1, col2 = st.columns(2)
    col1.metric("Minimum Heating", round(min_heat,2))
    col2.metric("Minimum Cooling", round(min_cooling,2))
