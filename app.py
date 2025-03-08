import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np

# Set page layout
st.set_page_config(layout="wide")

# Define file paths
file_paths = {
    "Logic A": "logic a.csv",
    "Logic B": "logic b.csv",
    "Logic C": "logic c new.csv",
    "Logic D": "logic d.csv",
}

# Common columns and logic-related columns
common_columns = [
    "product_id", "product_name", "vendor_id", "primary_vendor_name", 
    "business_tagging", "location_id", "Pareto", "Ship Date"
]
logic_columns = ['coverage', 'New DOI Policy WH', 'New RL Qty', 'New RL Value', 'Landed DOI']

# Load and normalize data
dfs = []
for key, path in file_paths.items():
    try:
        df = pd.read_csv(path, dtype={"product_id": int})
        logic_cols = [col for col in df.columns if any(lc in col for lc in logic_columns)]
        df = df[common_columns + logic_cols]
        df = df.rename(columns={col: col.split(') ')[-1] for col in df.columns})
        df["Logic"] = key
        dfs.append(df)
    except Exception as e:
        st.error(f"Error reading {key}: {e}")

# Merge data
data = pd.concat(dfs, ignore_index=True).sort_values(
    by=["product_id", "Logic"], key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4})
)

# Convert columns to appropriate types
data["coverage"] = pd.to_datetime(data["coverage"], errors="coerce").dt.date
data["New RL Value"] = data["New RL Value"].astype(str).str.replace(",", "", regex=True).astype(float)

# Load JI Dry data
ji_dry = pd.read_csv("JI Dry new.csv")
if "product_id" in data.columns and "product_id" in ji_dry.columns:
    ji_dry["product_id"] = ji_dry["product_id"].astype(str)
    ji_dry["Jarak Inbound"] = pd.to_numeric(ji_dry["Jarak Inbound"], errors="coerce").fillna(0).astype(int)
    data = data.merge(ji_dry, on="product_id", how="left").fillna({"Jarak Inbound": 7})
    data["Landed DOI - JI"] = data["Landed DOI"] - data["Jarak Inbound"]

# Sidebar navigation
page = st.sidebar.selectbox("Choose a page", ["Inbound Quantity Simulation", "OOS Projection WH"])

if page == "OOS Projection WH":
    st.title("Comparison of RL Quantity Logics")
    
    # Sidebar filters
    view_option = st.sidebar.radio("View by", ["Product ID", "Vendor"])
    
    if view_option == "Product ID":
        product_options = data[['product_id', 'product_name']].drop_duplicates()
        product_options['product_display'] = product_options['product_id'] + " - " + product_options['product_name']
        selected_product = st.sidebar.selectbox("Select Product", product_options['product_display'])
        selected_data = data[data["product_id"] == selected_product.split(" - ")[0]]
    
    else:  # Vendor selection
        data["vendor_display"] = np.where(
            data["primary_vendor_name"] == "0", 
            data["vendor_id"].astype(str), 
            data["vendor_id"].astype(str) + " - " + data["primary_vendor_name"]
        )
        selected_vendor = st.sidebar.selectbox("Select Vendor", data["vendor_display"].unique())
        selected_vendor_id = selected_vendor.split(" - ")[0].strip()
        selected_data = data[data["vendor_id"].astype(str) == selected_vendor_id]
    
    # Aggregation and formatting
    agg_dict = {
        "New RL Qty": "sum",
        "New RL Value": "sum",
        "coverage": "max",
        "New DOI Policy WH": "mean",
        "Landed DOI": "mean",
        "Landed DOI - JI": "mean",
        "Jarak Inbound": "min"
    }

    st.write("Available columns in selected_data:", selected_data.columns.tolist())

    # Ensure required columns exist
    required_cols = {"vendor_id", "primary_vendor_name", "Logic"}
    missing_cols = required_cols - set(selected_data.columns)
    if missing_cols:
        st.error(f"Missing columns in selected_data: {missing_cols}")
    selected_data = selected_data.groupby(["vendor_id", "primary_vendor_name", "Logic"], as_index=False).agg(agg_dict)
    selected_data["Verdict"] = selected_data.apply(lambda row: "Tidak Aman" if row["Landed DOI"] < 5 else "Aman", axis=1)
    
    # Table display with formatting
    def highlight_cells(val):
        return "background-color: red; color: white;" if val == "Tidak Aman" else ""
    
    formatted_df = selected_data.style.applymap(highlight_cells, subset=["Verdict"]).format({
        "New RL Value": "{:,.0f}",
        "New DOI Policy WH": "{:.2f}",
        "Landed DOI": "{:.2f}"
    })
    
    st.markdown("### Comparison Table")
    st.dataframe(formatted_df, use_container_width=True)
    
    # Visualization
    fig = go.Figure()
    for index, row in selected_data.iterrows():
        fig.add_trace(go.Bar(
            x=[row["Logic"]],
            y=[row["Landed DOI"]],
            name=f"{row['Logic']} - Landed DOI",
            marker=dict(color="lightgreen" if row["Landed DOI"] >= row["Jarak Inbound"] else "red")
        ))
        fig.add_annotation(
            x=row["Logic"],
            y=row["Landed DOI - JI"] + 0.5,
            text=f"{round(row['Landed DOI'] - row['Landed DOI - JI'], 2)}",
            showarrow=False,
            font=dict(color="black", size=12),
            bgcolor="yellow",
            borderpad=4,
        )
    
    fig.update_layout(
        xaxis_title="Logic", yaxis_title="Days", width=1000, height=500, showlegend=False
    )
    st.plotly_chart(fig)

