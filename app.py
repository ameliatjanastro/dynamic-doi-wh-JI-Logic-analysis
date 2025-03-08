import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

pareto_order = ["X", "A", "B", "C", "D", "New SKU A", "New SKU B", "New SKU C", "New SKU D", "No Sales L3M"]
custom_colors = ["#2C5F34", "#228B22", "#88E788", "#CD5C5C"]  # Light Blue & Gray Tones
st.set_page_config(layout="wide")

# Define file paths
file_paths = {
    "Logic A": "logic a.csv",
    "Logic B": "logic b.csv",
    "Logic C": "logic c new.csv",
    "Logic D": "logic d.csv",
}

# Load and normalize data
common_columns = ["product_id", "product_name", "vendor_id", "primary_vendor_name", "business_tagging", "location_id", "Pareto", "Ship Date"]
logic_columns = ['coverage', 'New DOI Policy WH', 'New RL Qty', 'New RL Value', 'Landed DOI']

dfs = []
for key, path in file_paths.items():
    try:
        df = pd.read_csv(path, dtype={"product_id": str})
        logic_cols = [col for col in df.columns if any(lc in col for lc in logic_columns)]
        df = df[[col for col in common_columns + logic_cols if col in df.columns]]  # Ensure columns exist
        df = df.rename(columns={col: col.split(') ')[-1] for col in df.columns})
        df["Logic"] = key
        dfs.append(df)
    except Exception as e:
        st.error(f"Error reading {key}: {e}")

if dfs:
    data = pd.concat(dfs, ignore_index=True)
    logic_order = {"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4}
    data = data.sort_values(by="Logic", key=lambda x: x.map(logic_order))
else:
    st.error("No valid data was loaded.")
    st.stop()

# Convert 'New RL Value' to numeric
if "New RL Value" in data.columns:
    data["New RL Value"] = data["New RL Value"].astype(str).str.replace(",", "", regex=True).astype(float)

# Load JI Dry Data
try:
    ji_dry = pd.read_csv("JI Dry new.csv", dtype={"product_id": str})
    if {"product_id", "Jarak Inbound"}.issubset(ji_dry.columns):
        ji_dry["Jarak Inbound"] = pd.to_numeric(ji_dry["Jarak Inbound"], errors="coerce").fillna(0).astype(int)
    else:
        ji_dry = pd.DataFrame(columns=["product_id", "Jarak Inbound"])
except Exception as e:
    st.error(f"Error loading JI Dry new.csv: {e}")
    ji_dry = pd.DataFrame(columns=["product_id", "Jarak Inbound"])

# Merge with JI Dry Data
if "product_id" in data.columns:
    data = data.merge(ji_dry, on="product_id", how="left").fillna({"Jarak Inbound": 7})

# Ensure "Landed DOI" is numeric
if "Landed DOI" in data.columns:
    data["Landed DOI"] = pd.to_numeric(data["Landed DOI"], errors="coerce").fillna(0).astype(int)
    data["Landed DOI - JI"] = data["Landed DOI"] - data["Jarak Inbound"]

# Sidebar Navigation
page = st.sidebar.selectbox("Choose a page", ["Inbound Quantity Simulation", "OOS Projection WH"])

if page == "OOS Projection WH":
    st.title("Comparison of RL Quantity Logics")

    # Sidebar filters
    view_option = st.sidebar.radio("View by", ["Product ID", "Vendor"])

    if view_option == "Product ID":
        product_options = data[["product_id", "product_name"]].drop_duplicates()
        product_options["product_display"] = product_options["product_id"] + " - " + product_options["product_name"]
        selected_product = st.sidebar.selectbox("Select Product", product_options["product_display"])
        selected_data = data[data["product_id"] == selected_product.split(" - ")[0]]

    elif view_option == "Vendor":
        data["vendor_display"] = np.where(
            data["primary_vendor_name"] == "0",
            data["vendor_id"].astype(str),
            data["vendor_id"].astype(str) + " - " + data["primary_vendor_name"]
        )
        selected_vendor = st.sidebar.selectbox("Select Vendor", data.sort_values(by="vendor_id")["vendor_display"].unique())
        selected_vendor_id = selected_vendor.split(" - ")[0].strip()
        selected_data = data[data["vendor_id"].astype(str).str.strip() == selected_vendor_id]

    if selected_data.empty:
        st.warning("No data available for the selected criteria.")
        st.stop()

    # Aggregate Data
    agg_dict = {
        "New RL Qty": "sum",
        "New RL Value": "sum",
        "coverage": "max",
        "New DOI Policy WH": "mean",
        "Landed DOI": "mean",
        "Landed DOI - JI": "mean",
        "Jarak Inbound": "min"
    }
    selected_data = selected_data.groupby(["vendor_id", "primary_vendor_name", "Logic"], as_index=False).agg({k: v for k, v in agg_dict.items() if k in selected_data.columns})

    # Sort by Logic
    selected_data = selected_data.sort_values(by="Logic", key=lambda x: x.map(logic_order))

    # Verdict Column
    if "Landed DOI" in selected_data.columns:
        selected_data["Verdict"] = selected_data["Landed DOI"].apply(lambda x: "Tidak Aman" if x < 5 else "Aman")

    # Display Table
    st.markdown("### Comparison Table")
    table_columns = ["Logic", "coverage", "New RL Qty", "New RL Value", "New DOI Policy WH", "Landed DOI", "Verdict"]
    formatted_df = selected_data[table_columns].style.applymap(lambda val: "background-color: red; color: white;" if val == "Tidak Aman" else "", subset=["Verdict"]).format({
        "New RL Value": "{:,.0f}",
        "New DOI Policy WH": "{:.2f}",
        "Landed DOI": "{:.2f}",
    })

    st.dataframe(formatted_df, hide_index=True, use_container_width=True)

elif page == "Inbound Quantity Simulation":
    st.title("Inbound Quantities Simulation by Ship Date")

    st.markdown(
        """
        <style>
        html {
            overflow-y: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Sidebar Filters
    chart_type = st.sidebar.radio("Select Chart Type", ["Line Chart", "Bar Chart"])
    pareto_options = sorted(data["Pareto"].dropna().unique())

    selected_location = st.sidebar.selectbox("Select Location ID", sorted(data["location_id"].dropna().unique()))
    selected_pareto = st.sidebar.multiselect("Select Pareto", pareto_options, default=pareto_options[:3])  # Default to first 3
    selected_business_tag = st.sidebar.multiselect("Select Business Tag", sorted(data["business_tagging"].dropna().unique()))

    # Apply filters
    filtered_data = data[
        (data["Pareto"].isin(selected_pareto) if selected_pareto else data["Pareto"].notna()) &
        (data["location_id"] == selected_location if selected_location else data["location_id"].notna()) &
        (data["business_tagging"].isin(selected_business_tag) if selected_business_tag else data["business_tagging"].notna())
    ]

    # Group data
    filtered_logic_data = filtered_data[filtered_data["primary_vendor_name"] != "0"]
    logic_options = sorted(filtered_logic_data["Logic"].unique())

    st.markdown(
        """
        <style>
        div[data-testid="stSelectbox"] {
            width: auto !important;
            display: inline-block !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Select Logic
    selected_logic = st.selectbox("", logic_options, key="logic_dropdown", label_visibility="collapsed")

    # Compute values
    inbound_data_week = filtered_logic_data.loc[filtered_logic_data["Logic"] == selected_logic, "New RL Qty"].sum()
    tidakaman = filtered_logic_data.loc[
        (filtered_logic_data["Logic"] == selected_logic) & 
        (filtered_logic_data["Landed DOI"] < 5), 
        "New RL Qty"
    ].count()

    st.markdown(f"##### Total RL Qty for **{selected_logic}**: {inbound_data_week} | Total SKU Tidak Aman (Landed DOI < 5): <span style='color:red; font-weight:bold;'>{tidakaman}</span>", 
        unsafe_allow_html=True)

    # Table for "Tidak Aman" SKUs
    table_tidakaman = ["Logic", "product_id", "product_name", "Pareto", "primary_vendor_name", "New RL Qty", "New RL Value", "New DOI Policy WH", "Landed DOI"]
    
    if "Logic" in filtered_logic_data.columns:
        tidakaman_df = filtered_logic_data[(filtered_logic_data["Landed DOI"] < 5) & (filtered_logic_data["Logic"] == selected_logic)][table_tidakaman]
        tidakaman_df = tidakaman_df.sort_values(by="Logic", key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4}))
    else:
        st.error("Error: 'Logic' column is missing in the dataset.")
        st.stop()

    # Download button
    csv = tidakaman_df.to_csv(index=False)
    st.download_button("📥 Download SKU Tidak Aman", csv, "tidakamanlist.csv", "text/csv")

    st.markdown("---")

    # ✅ Create Visualization
    inbound_data = filtered_logic_data.groupby(["Ship Date", "Logic"], as_index=False)["New RL Qty"].sum()

    if chart_type == "Line Chart":
        fig = px.line(
            inbound_data, 
            x="Ship Date", 
            y="New RL Qty", 
            color="Logic",
            markers=True,  
            title="Inbound Quantity Line Chart"
        )
    else:
        fig = px.bar(
            inbound_data, 
            x="Ship Date", 
            y="New RL Qty", 
            color="Logic",
            text=inbound_data["New RL Qty"].astype(str),  
            title="Inbound Quantity Bar Chart"
        )

    st.plotly_chart(fig, use_container_width=True)

    # ✅ Add Logic Details Table
    logic_details = {
        "Logic Name": ["Logic A", "Logic B", "Logic C", "Logic D"],
        "Logic Details": [
            "COV sesuai RL everyday, dynamic DOI 50% * JI",
            "COV sesuai RL everyday, dynamic DOI JI",
            "COV sesuai RL everyday, dynamic DOI JI * FR Performance weight",
            "COV 14 Days, DOI Policy 5"
        ]
    }
    logic_df = pd.DataFrame(logic_details)
    st.dataframe(logic_df, hide_index=True, use_container_width=True)

    st.write("**📝 Note:** All logics assume LDP LBH per 10 Feb 2025 → LDP+LBH 85% are added to SOH, thus SOH might not be entirely accurate 🙂")
    
    # ✅ Define Logic Details Data
    logic_details = {
        "Logic Name": ["Logic A", "Logic B", "Logic C", "Logic D"],
        "Logic Details": [
            "cov sesuai RL everyday, dynamic DOI 50% * JI",
            "cov sesuai RL everyday, dynamic DOI JI",
            "cov sesuai RL everyday, dynamic DOI JI*FR Performance weight",
            "cov 14 Days, DOI Policy 5"
        ]
    }
    
    # ✅ Convert to DataFrame & Display Table
    logic_df = pd.DataFrame(logic_details)
    st.dataframe(logic_df, hide_index=True, use_container_width=True)

