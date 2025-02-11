import pandas as pd
import streamlit as st

# Define file paths
file_paths = {
    "Logic A": "logic a.csv",
    "Logic B": "logic b.csv",
    "Logic C": "logic c.csv",
    "Logic D": "logic d.csv",
}

# Load and normalize data
common_columns = [
    'product_id', 'product_name', 'location_id', 'business_tagging', 'product_type_name',
    'vendor_id', 'primary_vendor_name', 'max_doi_final', 'Pareto', 'active_hub'
]
logic_columns = [
    'coverage', 'New DOI Policy WH', 'New RL Qty', 'New RL Value', 'Order Date', 'Landed DOI'
]

dfs = []
for key, path in file_paths.items():
    try:
        df = pd.read_csv(path, dtype={"product_id": str, "location_id": str, "vendor_id": str})
        df = df[common_columns + [col for col in df.columns if any(lc in col for lc in logic_columns)]]
        df = df.rename(columns={col: col.split(') ')[-1] for col in df.columns})
        df["Logic"] = key
        dfs.append(df)
    except Exception as e:
        st.error(f"Error reading {key}: {e}")

# Merge data
data = pd.concat(dfs, ignore_index=True).sort_values(by=["product_id"])

# Streamlit UI
st.title("Comparison of RL Quantity Logics")

# Sidebar filters
st.sidebar.header("Filters")
view_by = st.sidebar.radio("View By", ["Product ID", "Vendor"])
selected_pareto = st.sidebar.multiselect("Filter by Pareto", data["Pareto"].unique())
selected_location = st.sidebar.multiselect("Filter by Location ID", data["location_id"].unique())
selected_business_tag = st.sidebar.multiselect("Filter by Business Tag", data["business_tagging"].unique())

# Apply filters
filtered_data = data.copy()
if selected_pareto:
    filtered_data = filtered_data[filtered_data["Pareto"].isin(selected_pareto)]
if selected_location:
    filtered_data = filtered_data[filtered_data["location_id"].isin(selected_location)]
if selected_business_tag:
    filtered_data = filtered_data[filtered_data["business_tagging"].isin(selected_business_tag)]

# Aggregation logic
if view_by == "Vendor":
    summary_data = filtered_data.groupby(["vendor_id", "primary_vendor_name", "Logic"]).agg({
        "New RL Qty": "sum",
        "New RL Value": "sum",
        "New DOI Policy WH": "mean",
        "max_doi_final": "mean",
        "Landed DOI": "mean"
    }).reset_index()
else:
    summary_data = filtered_data

# Display table
st.write("### Comparison Table")
st.dataframe(summary_data)
