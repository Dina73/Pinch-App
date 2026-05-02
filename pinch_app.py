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

deltaT = st.number_input("Enter ΔTmin", value=10)

if st.button("Calculate Pinch"):

    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    # Shift Temperatures
    hot["Tin_shift"] = hot["Tin"] - deltaT/2
    hot["Tout_shift"] = hot["Tout"] - deltaT/2

    cold["Tin_shift"] = cold["Tin"] + deltaT/2
    cold["Tout_shift"] = cold["Tout"] + deltaT/2

    st.subheader("Shifted Temperatures")
    st.write(pd.concat([hot, cold]))

    # Temperature List
    temps = list(hot["Tin_shift"]) + list(hot["Tout_shift"]) + \
            list(cold["Tin_shift"]) + list(cold["Tout_shift"])

    temps = sorted(set(temps), reverse=True)

    st.subheader("Temperature Intervals")
    st.write(temps)

    # Heat Cascade Calculation
    interval_data = []

    for i in range(len(temps)-1):

        t_high = temps[i]
        t_low = temps[i+1]

        cp_hot = hot[(hot["Tin_shift"] >= t_high) & 
                     (hot["Tout_shift"] <= t_low)]["Cp"].sum()

        cp_cold = cold[(cold["Tout_shift"] >= t_high) & 
                       (cold["Tin_shift"] <= t_low)]["Cp"].sum()

        deltaH = (cp_hot - cp_cold) * (t_high - t_low)

        interval_data.append([t_high, t_low, cp_hot, cp_cold, deltaH])

    cascade = pd.DataFrame(interval_data,
                           columns=["T_high","T_low","Cp_hot","Cp_cold","ΔH"])

    st.subheader("Heat Cascade Table")
    st.write(cascade)

    # Heat Cascade
    heat = [0]

    for q in cascade["ΔH"]:
        heat.append(heat[-1] + q)

    cascade["Heat Cascade"] = heat[1:]

    st.subheader("Heat Cascade")
    st.write(cascade)

    # Minimum Heating
    min_heat = abs(min(heat))

    st.subheader("Minimum Heating Required")
    st.write(min_heat)

    # Shift Cascade
    adjusted = [h + min_heat for h in heat]

    min_cooling = adjusted[-1]

    st.subheader("Minimum Cooling Required")
    st.write(min_cooling)

    # Pinch Temperature
    pinch_index = adjusted.index(min(adjusted))

    pinch_temp = temps[pinch_index]

    st.subheader("Pinch Temperature")
    st.success(pinch_temp)
    
    st.subheader("Composite Curves")

    # Hot Composite Curve
    hot_streams = []

    for index, row in hot.iterrows():
        hot_streams.append([row["Tin_shift"], row["Tout_shift"], row["Cp"]])

    cold_streams = []

    for index, row in cold.iterrows():
        cold_streams.append([row["Tin_shift"], row["Tout_shift"], row["Cp"]])

    # Temperature Range
    all_temps = sorted(temps, reverse=True)

    hot_q = [0]
    cold_q = [0]

    for i in range(len(all_temps)-1):

        t_high = all_temps[i]
        t_low = all_temps[i+1]

        cp_hot = sum([cp for tin,tout,cp in hot_streams 
                      if tin >= t_high and tout <= t_low])

        cp_cold = sum([cp for tin,tout,cp in cold_streams 
                       if tout >= t_high and tin <= t_low])

        dq_hot = cp_hot*(t_high-t_low)
        dq_cold = cp_cold*(t_high-t_low)

        hot_q.append(hot_q[-1] + dq_hot)
        cold_q.append(cold_q[-1] + dq_cold)

    # Plot Composite Curves
    plt.figure()

    plt.plot(hot_q, all_temps, label="Hot Composite")
    plt.plot(cold_q, all_temps, label="Cold Composite")

    plt.xlabel("Heat Flow")
    plt.ylabel("Temperature")

    plt.legend()

    plt.gca().invert_yaxis()

    st.pyplot(plt)
    
    st.subheader("Grand Composite Curve")

    # Grand Composite Curve Data
    gcc_heat = adjusted
    gcc_temp = temps

    plt.figure()

    plt.step(gcc_heat, gcc_temp, where="post")

    plt.xlabel("Net Heat Flow")
    plt.ylabel("Temperature")

    plt.gca().invert_yaxis()

    st.pyplot(plt)
    
    st.subheader("Heat Exchanger Matching")

    matches = []

    # Available Heat Streams
    hot_streams = hot.copy()
    cold_streams = cold.copy()

    for i, h in hot_streams.iterrows():
        for j, c in cold_streams.iterrows():

            # Temperature feasibility
            if h["Tin"] > c["Tout"]:

                # Heat Available
                Q_hot = h["Cp"] * (h["Tin"] - h["Tout"])
                Q_cold = c["Cp"] * (c["Tout"] - c["Tin"])

                Q = min(Q_hot, Q_cold)

                if Q > 0:

                    matches.append([
                        h["Stream"],
                        c["Stream"],
                        round(Q,2)
                    ])

    if matches:

        match_df = pd.DataFrame(
            matches,
            columns=["Hot Stream","Cold Stream","Heat Exchange"]
        )

        st.write("Suggested Heat Exchanger Matches")
        st.write(match_df)

    else:
        st.write("No feasible matches found")
        
    st.subheader("Heat Exchanger Network Diagram")

    for m in matches:
        st.write(f"{m[0]}  →  {m[1]}  :  {m[2]} kW")

    # Display Utilities
    st.subheader("Utility Targets")

    col1, col2 = st.columns(2)

    col1.metric("Minimum Heating", round(min_heat,2))
    col2.metric("Minimum Cooling", round(min_cooling,2))

    # Plot Heat Cascade
    plt.figure()

    plt.plot(adjusted, temps)

    plt.xlabel("Heat Flow")
    plt.ylabel("Temperature")

    plt.gca().invert_yaxis()

    st.pyplot(plt)