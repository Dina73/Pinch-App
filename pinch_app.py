import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Heat Integration & Pinch Analysis App")

st.sidebar.title("Heat Integration Tool")
st.sidebar.write("Pinch Analysis Application")
st.sidebar.write("Graduation Project")

st.write("Enter Stream Data")

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
# Utilities
# -----------------------------
def shift_temps(df, dTmin):
    df = df.copy()
    if (df["Type"] == "Hot").any():
        pass
    df["Tin_shift"] = np.where(df["Type"] == "Hot", df["Tin"] - dTmin/2, df["Tin"] + dTmin/2)
    df["Tout_shift"] = np.where(df["Type"] == "Hot", df["Tout"] - dTmin/2, df["Tout"] + dTmin/2)
    return df

def interval_endpoints_from_shifted(hot, cold):
    temps = list(hot["Tin_shift"]) + list(hot["Tout_shift"]) + \
            list(cold["Tin_shift"]) + list(cold["Tout_shift"])
    temps = sorted(set(temps), reverse=True)
    return temps

def interval_cp_full_coverage(streams_df, Th, Tl):
    """
    For temperature interval (Th -> Tl) with Th > Tl, a stream contributes
    only if its shifted temperature range fully covers the interval:
      Tin_shift >= Th and Tout_shift <= Tl   (for hot-like orientation)
    However, because users may not always input Tin/Tout correctly,
    we use min/max of shifted endpoints to determine the span, then require:
      span_high >= Th and span_low <= Tl
    """
    total = 0.0
    for _, r in streams_df.iterrows():
        s1 = r["Tin_shift"]
        s2 = r["Tout_shift"]
        span_high = max(s1, s2)
        span_low  = min(s1, s2)

        # Full interval coverage test
        if (span_high >= Th) and (span_low <= Tl):
            total += float(r["Cp"])
    return total

# -----------------------------
# Main
# -----------------------------
if st.button("Calculate Pinch"):

    if data is None or data.empty:
        st.error("Please enter at least one stream.")
        st.stop()

    required = {"Stream", "Type", "Tin", "Tout", "Cp"}
    if not required.issubset(set(data.columns)):
        st.error(f"Missing columns. Required: {required}")
        st.stop()

    # Split
    all_df = data.copy()
    hot = all_df[all_df["Type"] == "Hot"].copy()
    cold = all_df[all_df["Type"] == "Cold"].copy()

    if hot.empty or cold.empty:
        st.error("Please include at least one Hot stream and one Cold stream.")
        st.stop()

    # Shift temps
    all_shifted = shift_temps(all_df, deltaT)
    hot = all_shifted[all_shifted["Type"] == "Hot"].copy()
    cold = all_shifted[all_shifted["Type"] == "Cold"].copy()

    st.subheader("Shifted Temperatures")
    st.write(pd.concat([hot, cold], ignore_index=True))

    # Temperature grid
    temps = interval_endpoints_from_shifted(hot, cold)
    if len(temps) < 2:
        st.error("Not enough unique shifted temperatures to form intervals.")
        st.stop()

    st.subheader("Temperature Intervals (shifted endpoints)")
    st.write(temps)

    intervals = list(zip(temps[:-1], temps[1:]))  # (Th, Tl), Th > Tl

    # Heat cascade using Cp interval full coverage
    interval_rows = []
    for Th, Tl in intervals:
        dT = Th - Tl
        Cp_hot = interval_cp_full_coverage(hot, Th, Tl)
        Cp_cold = interval_cp_full_coverage(cold, Th, Tl)

        dH = (Cp_hot - Cp_cold) * dT
        interval_rows.append([Th, Tl, Cp_hot, Cp_cold, dH])

    cascade = pd.DataFrame(interval_rows, columns=["T_high", "T_low", "Cp_hot", "Cp_cold", "ΔH"])
    st.subheader("Heat Cascade Table")
    st.write(cascade)

    # Running heat with points at interval endpoints
    # heat[0]=0 at temps[0], then add each interval ΔH
    heat_points = [0.0]
    for dh in cascade["ΔH"].tolist():
        heat_points.append(heat_points[-1] + float(dh))

    # Ensure alignment: heat_points length == len(temps)
    # cascade length == len(temps)-1
    min_heat = min(heat_points)
    adj = [h - min_heat for h in heat_points]  # shift so minimum is at 0

    min_heating_required = -min_heat  # positive number
    min_cooling_required = adj[-1]    # final adjusted heat

    st.subheader("Cascade Running Heat (unadjusted)")
    tmp = pd.DataFrame({"Temperature (shifted)": temps, "Heat (running)": heat_points})
    st.write(tmp)

    st.subheader("Utilities Targets")
    col1, col2 = st.columns(2)
    col1.metric("Minimum Heating Required", round(min_heating_required, 4))
    col2.metric("Minimum Cooling Required", round(min_cooling_required, 4))

    # Pinch index: where adjusted cascade is minimal (which is 0 after shift)
    pinch_indices = [i for i, v in enumerate(adj) if abs(v - min(adj)) < 1e-9]
    pinch_index = pinch_indices[0]
    pinch_temp = temps[pinch_index]

    st.subheader("Pinch Temperature (shifted)")
    st.success(f"{pinch_temp}")

    # Plot Heat Cascade
    st.subheader("Heat Cascade Plot")
    plt.figure()
    plt.step(adj, temps, where="post")
    plt.xlabel("Adjusted Heat Flow")
    plt.ylabel("Temperature (shifted)")
    plt.gca().invert_yaxis()
    st.pyplot(plt)

    # -----------------------------
    # Composite curves (FIXED)
    # -----------------------------
    # Build cumulative heat for hot and cold composite curves:
    # Qhot_cum(i+1) = Qhot_cum(i) + Cp_hot(i)*ΔT_i
    # Qcold_cum(i+1)= Qcold_cum(i) + Cp_cold(i)*ΔT_i
    hot_q = [0.0]
    cold_q = [0.0]
    hot_T = [temps[0]]
    cold_T = [temps[0]]

    for Th, Tl in intervals:
        dT = Th - Tl
        Cp_hot = interval_cp_full_coverage(hot, Th, Tl)
        Cp_cold = interval_cp_full_coverage(cold, Th, Tl)

        hot_q.append(hot_q[-1] + Cp_hot * dT)
        cold_q.append(cold_q[-1] + Cp_cold * dT)

        hot_T.append(Tl)
        cold_T.append(Tl)

    st.subheader("Composite Curves (shifted temperatures)")
    plt.figure()
    plt.step(hot_q, hot_T, where="post", label="Hot Composite")
    plt.step(cold_q, cold_T, where="post", label="Cold Composite")
    plt.xlabel("Heat Flow (cumulative)")
    plt.ylabel("Temperature (shifted)")
    plt.gca().invert_yaxis()
    plt.legend()
    st.pyplot(plt)

    # Grand composite curve:
    # Often shown as net heat cascade vs temperature; here we use adjusted cascade adj
    st.subheader("Grand Composite Curve (shifted)")
    plt.figure()
    plt.step(adj, temps, where="post")
    plt.xlabel("Net Heat Flow (adjusted)")
    plt.ylabel("Temperature (shifted)")
    plt.gca().invert_yaxis()
    st.pyplot(plt)

    # -----------------------------
    # Matching (kept simple)
    # -----------------------------
    st.subheader("Heat Exchanger Matching (simple heuristic)")
    matches = []

    hot_orig = hot.copy()
    cold_orig = cold.copy()

    for _, h in hot_orig.iterrows():
        hTin, hTout = float(h["Tin"]), float(h["Tout"])
        hHigh = max(hTin, hTout)
        hLow = min(hTin, hTout)

        for _, c in cold_orig.iterrows():
            cTin, cTout = float(c["Tin"]), float(c["Tout"])
            cHigh = max(cTin, cTout)
            cLow = min(cTin, cTout)

            if (hHigh <= cLow) or (cHigh <= hLow):
                continue

            overlap_hi = min(hHigh, cHigh)
            overlap_lo = max(hLow, cLow)
            if overlap_hi <= overlap_lo:
                continue

            dTo = overlap_hi - overlap_lo
            Qh = float(h["Cp"]) * dTo
            Qc = float(c["Cp"]) * dTo
            Q = min(Qh, Qc)

            if Q > 1e-9:
                matches.append([h["Stream"], c["Stream"], round(Q, 6)])

    if matches:
        match_df = pd.DataFrame(matches, columns=["Hot Stream", "Cold Stream", "Heat Exchange (Q)"])
        st.write("Suggested Heat Exchanger Matches")
        st.write(match_df)
        st.subheader("Heat Exchanger Network Diagram (text)")
        for m in matches:
            st.write(f"{m[0]}  →  {m[1]}  :  {m[2]} kW")
    else:
        st.write("No feasible matches found")
