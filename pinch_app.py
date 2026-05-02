import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Heat Integration & Pinch Analysis App")

st.sidebar.title("Heat Integration Tool")
st.sidebar.write("Pinch Analysis Application")
st.sidebar.write("Graduation Project")

st.write("Enter Stream Data")

# -----------------------------
# Input
# -----------------------------
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

# -----------------------------
# Helpers (Pinch math)
# -----------------------------
def build_shifted(streams_hot, streams_cold, dTmin):
    hot = streams_hot.copy()
    cold = streams_cold.copy()

    # Shift temperatures
    hot["Tin_shift"] = hot["Tin"] - dTmin/2
    hot["Tout_shift"] = hot["Tout"] - dTmin/2

    cold["Tin_shift"] = cold["Tin"] + dTmin/2
    cold["Tout_shift"] = cold["Tout"] + dTmin/2

    return hot, cold

def interval_overlap_cp(streams_df, Th, Tl, kind="hot"):
    """
    Returns sum(Cp) of streams overlapping the shifted temperature interval [Tl, Th]
    where Th > Tl (since temps are sorted descending).
    We treat a stream as overlapping if its shifted temperature range intersects the interval.
    """
    total_cp = 0.0
    for _, r in streams_df.iterrows():
        sTin = r["Tin_shift"]
        sTout = r["Tout_shift"]

        # A stream might be expressed with Tin > Tout or Tin < Tout depending on user,
        # but for pinch interval logic we just want its temperature span.
        sHi = max(sTin, sTout)
        sLo = min(sTin, sTout)

        # Overlap if: interval (Tl..Th) intersects stream span (sLo..sHi)
        if (sHi > Tl) and (sLo < Th):
            total_cp += r["Cp"]
    return total_cp

def compute_temperature_intervals(hot, cold):
    temps = list(hot["Tin_shift"]) + list(hot["Tout_shift"]) + \
            list(cold["Tin_shift"]) + list(cold["Tout_shift"])
    temps = sorted(set(temps), reverse=True)
    return temps

# -----------------------------
# Main
# -----------------------------
if st.button("Calculate Pinch"):

    # Basic validation
    if data.empty:
        st.error("Please enter at least one stream.")
        st.stop()

    if "Type" not in data.columns or "Tin" not in data.columns or "Tout" not in data.columns or "Cp" not in data.columns:
        st.error("Missing required columns: Stream, Type, Tin, Tout, Cp.")
        st.stop()

    hot = data[data["Type"] == "Hot"].copy()
    cold = data[data["Type"] == "Cold"].copy()

    if hot.empty or cold.empty:
        st.error("Please include at least one Hot and one Cold stream.")
        st.stop()

    # Shift Temperatures
    hot, cold = build_shifted(hot, cold, deltaT)

    st.subheader("Shifted Temperatures (ΔTmin method)")
    st.write(pd.concat([hot, cold], ignore_index=True))

    # Temperature List / Intervals
    temps = compute_temperature_intervals(hot, cold)
    st.subheader("Temperature Intervals (shifted endpoints)")
    st.write(temps)

    # -----------------------------
    # Heat Cascade (interval-based)
    # -----------------------------
    interval_data = []
    intervals = list(zip(temps[:-1], temps[1:]))  # (T_high, T_low)

    for Th, Tl in intervals:
        dT = Th - Tl

        cp_hot = interval_overlap_cp(hot, Th, Tl, kind="hot")
        cp_cold = interval_overlap_cp(cold, Th, Tl, kind="cold")

        # Heat balance using shifted intervals:
        # Q interval = (Cp_hot - Cp_cold) * dT
        deltaH = (cp_hot - cp_cold) * dT

        interval_data.append([Th, Tl, cp_hot, cp_cold, deltaH])

    cascade = pd.DataFrame(interval_data, columns=["T_high", "T_low", "Cp_hot", "Cp_cold", "ΔH"])
    st.subheader("Heat Cascade Table")
    st.write(cascade)

    # Build cascade running heat
    heat = [0.0]
    for q in cascade["ΔH"].tolist():
        heat.append(heat[-1] + q)

    cascade["Heat Cascade"] = heat[1:]  # align with intervals

    st.subheader("Heat Cascade (running)")
    st.write(cascade)

    # Minimum heating required
    min_heat = abs(min(heat))
    st.subheader("Minimum Heating Required (Qh,min)")
    st.write(round(min_heat, 6))

    # Shift cascade by minimum heating
    adjusted = [h + min_heat for h in heat]
    min_cooling = adjusted[-1]
    st.subheader("Minimum Cooling Required (Qc,min)")
    st.write(round(min_cooling, 6))

    # Pinch temperature
    # Pinch occurs at the interval where the adjusted cascade reaches minimum.
    # Using the heat points corresponds to temps endpoints.
    pinch_index = adjusted.index(min(adjusted))
    # adjusted has length len(temps); pinch temperature corresponds to temps[pinch_index]
    pinch_temp = temps[pinch_index]

    st.subheader("Pinch Temperature (shifted)")
    st.success(f"{pinch_temp}")

    # -----------------------------
    # Composite Curves (FIXED)
    # -----------------------------
    st.subheader("Composite Curves (shifted temperatures, interval-overlap)")

    # Build cumulative heat for Hot and Cold composite curves as step functions
    hot_q = [0.0]
    cold_q = [0.0]

    # Temperature points for step: start at temps[0], then each interval ends at Tl
    comp_hot_T = [temps[0]]
    comp_cold_T = [temps[0]]

    for Th, Tl in intervals:
        dT = Th - Tl
        cpH = interval_overlap_cp(hot, Th, Tl, kind="hot")
        cpC = interval_overlap_cp(cold, Th, Tl, kind="cold")

        hot_q.append(hot_q[-1] + cpH * dT)
        cold_q.append(cold_q[-1] + cpC * dT)

        comp_hot_T.append(Tl)
        comp_cold_T.append(Tl)

    plt.figure()
    plt.step(hot_q, comp_hot_T, where="post", label="Hot Composite")
    plt.step(cold_q, comp_cold_T, where="post", label="Cold Composite")
    plt.xlabel("Heat Flow (cum.)")
    plt.ylabel("Temperature (shifted)")
    plt.gca().invert_yaxis()
    plt.legend()
    st.pyplot(plt)

    # -----------------------------
    # Grand Composite Curve (from adjusted cascade)
    # -----------------------------
    st.subheader("Grand Composite Curve (from adjusted cascade)")

    # adjusted length == len(temps), heat points correspond to interval endpoints
    plt.figure()
    plt.step(adjusted, temps, where="post")
    plt.xlabel("Net Heat Flow (Adjusted)")
    plt.ylabel("Temperature (shifted)")
    plt.gca().invert_yaxis()
    st.pyplot(plt)

    # -----------------------------
    # Heat Exchanger Matching (simple heuristic)
    # NOTE: This part was also simplistic originally; it uses unshifted temps and a single-stream Cp assumption.
    # We'll keep it but make it more consistent and avoid obvious issues.
    # -----------------------------
    st.subheader("Heat Exchanger Matching (simple heuristic)")

    matches = []

    # Use original hot/cold for matching feasibility
    hot_orig = hot.copy()
    cold_orig = cold.copy()

    for _, h in hot_orig.iterrows():
        for _, c in cold_orig.iterrows():
            # Feasibility: hot at some point must be able to cool into cold at some point.
            # Basic overlap test on original temps.
            hHi = max(h["Tin"], h["Tout"])
            hLo = min(h["Tin"], h["Tout"])
            cHi = max(c["Tin"], c["Tout"])
            cLo = min(c["Tin"], c["Tout"])

            # If spans do not overlap at all, skip
            if (hHi <= cLo) or (hLo >= cHi):
                continue

            # Conservative estimate of exchangeable heat:
            # hot can provide Cp * overlap_dT, cold can absorb Cp * overlap_dT
            # approximate overlap in temperature span:
            overlap_hi = min(hHi, cHi)
            overlap_lo = max(hLo, cLo)
            if overlap_hi <= overlap_lo:
                continue

            Q_hot = h["Cp"] * (overlap_hi - overlap_lo)
            Q_cold = c["Cp"] * (overlap_hi - overlap_lo)
            Q = min(Q_hot, Q_cold)

            if Q > 1e-9:
                matches.append([h["Stream"], c["Stream"], round(Q, 6)])

    if matches:
        match_df = pd.DataFrame(matches, columns=["Hot Stream", "Cold Stream", "Heat Exchange (Q)"])
        st.write("Suggested Heat Exchanger Matches")
        st.write(match_df)
    else:
        st.write("No feasible matches found")

    st.subheader("Heat Exchanger Network Diagram (text)")

    if matches:
        for m in matches:
            st.write(f"{m[0]}  →  {m[1]}  :  {m[2]} kW")

    # -----------------------------
    # Utilities
    # -----------------------------
    st.subheader("Utility Targets")
    col1, col2 = st.columns(2)
    col1.metric("Minimum Heating (Qh,min)", round(min_heat, 2))
    col2.metric("Minimum Cooling (Qc,min)", round(min_cooling, 2))

    # Plot Heat Cascade (same)
    st.subheader("Heat Cascade Plot")
    plt.figure()
    # cascade points: adjusted vs temps
    plt.plot(adjusted, temps)
    plt.xlabel("Heat Flow (Adjusted)")
    plt.ylabel("Temperature (shifted)")
    plt.gca().invert_yaxis()
    st.pyplot(plt)
