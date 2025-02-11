import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
#data1 = pd.read_csv('logic a.csv')
#data2 = pd.read_csv('logic b.csv')
#data3 = pd.read_csv('logic c.csv')
#data4 = pd.read_csv('logic d.csv')


#data1 = data1[['product_id','product_name','location_id','business_tagging','product_type_name','vendor_id','primary_vendor_name','Logic A) coverage','Logic A) New DOI Policy WH','max_doi_final','Logic A) New RL Qty','Logic A) New RL Value','Logic A) Order Date','Ship Date','INBOUND TO OOS PROJECTION','Pareto','active_hub','Logic A) Landed DOI']]
#data2 = data2[['product_id','product_name','location_id','business_tagging','product_type_name','vendor_id','primary_vendor_name','Logic B) coverage','Logic B) New DOI Policy WH','max_doi_final','Logic B) New RL Qty','Logic B) New RL Value','Logic B) Order Date','Ship Date','INBOUND TO OOS PROJECTION','Pareto','active_hub','Logic B) Landed DOI']]
#data3 = data3[['product_id','product_name','location_id','business_tagging','product_type_name','vendor_id','primary_vendor_name','Logic C) coverage','Logic C) New DOI Policy WH','max_doi_final','Logic C) New RL Qty','Logic C) New RL Value','Logic C) Order Date','Ship Date','INBOUND TO OOS PROJECTION','Pareto','active_hub','Logic C) Landed DOI']]
#data4 = data4[['product_id','product_name','location_id','business_tagging','product_type_name','vendor_id','primary_vendor_name','Logic D) coverage','Logic D) New DOI Policy WH','max_doi_final','Logic D) New RL Qty','Logic D) New RL Value','Logic D) Order Date','Ship Date','INBOUND TO OOS PROJECTION','Pareto','active_hub','Logic D) Landed DOI']]

# Define file paths
file_paths = {
    "Logic A": "logic a.csv",
    "Logic B": "logic b.csv",
    "Logic C": "logic c.csv",
    "Logic D": "logic d.csv",
}

# Load data one by one and inspect
dfs = []
for key, path in file_paths.items():
    print(f"Reading {key} from {path}")
    try:
        df = pd.read_csv(path, dtype={"product_id": str, "location_id": str, "vendor_id": str})
        df["Logic"] = key  # Add a marker column to indicate logic type
        print(f"{key} loaded successfully with {df.shape[0]} rows and {df.shape[1]} columns")
        dfs.append(df)
    except Exception as e:
        print(f"Error reading {key}: {e}")

# Define common columns and logic-specific columns
common_columns = [
    'product_id', 'product_name', 'location_id', 'business_tagging', 'product_type_name',
    'vendor_id', 'primary_vendor_name', 'max_doi_final', 'Ship Date', 'INBOUND TO OOS PROJECTION',
    'Pareto', 'active_hub'
]

# Standardized logic-specific column names
logic_column_mapping = {
    'coverage': 'coverage',
    'New DOI Policy WH': 'New DOI Policy WH',
    'New RL Qty': 'New RL Qty',
    'New RL Value': 'New RL Value',
    'Order Date': 'Order Date',
    'Landed DOI': 'Landed DOI'
}

# Process each dataframe and normalize column names
normalized_dfs = []
for df in dfs:
    logic = df["Logic"].iloc[0]  # Get logic name
    rename_mapping = {col: logic_column_mapping[col.replace(f"{logic}) ", "")] for col in df.columns if any(col.endswith(suffix) for suffix in logic_column_mapping.keys())}
    df = df.rename(columns=rename_mapping)
    df = df[common_columns + list(logic_column_mapping.values()) + ["Logic"]]
    normalized_dfs.append(df)

# Concatenate all logic data into a single dataframe
merged_df = pd.concat(normalized_dfs, ignore_index=True)

merged_df = merged_df.sort_values(by=['location_id','product_id'])

# Streamlit UI
st.title("Comparison of RL Quantity Logics")

# Sidebar filters
st.sidebar.header("Filters")
view_by = st.sidebar.radio("View By", ["Product ID", "Vendor"])
selected_pareto = st.sidebar.multiselect("Filter by Pareto", merged_df["Pareto"].unique())
selected_location = st.sidebar.multiselect("Filter by Location ID", merged_df["location_id"].unique())
selected_business_tag = st.sidebar.multiselect("Filter by Business Tag", merged_df["business_tagging"].unique())

# Apply filters
filtered_df = merged_df.copy()
if selected_pareto:
    filtered_df = filtered_df[filtered_df["Pareto"].isin(selected_pareto)]
if selected_location:
    filtered_df = filtered_df[filtered_df["location_id"].isin(selected_location)]
if selected_business_tag:
    filtered_df = filtered_df[filtered_df["business_tagging"].isin(selected_business_tag)]

# Aggregation logic
if view_by == "Vendor":
    grouped_df = filtered_df.groupby(["vendor_id", "primary_vendor_name", "Logic"]).agg({
        "New RL Qty": "sum",
        "New RL Value": "sum",
        "New DOI Policy WH": "mean",
        "max_doi_final": "mean",
        "Landed DOI": "mean"
    }).reset_index()
    x_axis = "primary_vendor_name"
else:
    grouped_df = filtered_df
    x_axis = "product_id"

# Ensure numeric columns are properly formatted for plotting
numeric_cols = ["New RL Qty", "coverage", "Landed DOI", "New RL Value", "New DOI Policy WH", "max_doi_final"]
for col in numeric_cols:
    grouped_df[col] = pd.to_numeric(grouped_df[col], errors='coerce')

# Matplotlib plot
st.write("### Comparison of Metrics")
fig, ax = plt.subplots(figsize=(12, 6))
for logic in grouped_df["Logic"].unique():
    logic_df = grouped_df[grouped_df["Logic"] == logic]
    ax.plot(logic_df[x_axis], logic_df["New RL Qty"], marker='o', label=logic)
ax.set_title(f"Comparison of RL Quantity by {view_by}")
ax.set_xlabel(view_by)
ax.set_ylabel("New RL Qty")
ax.legend()
st.pyplot(fig)

# Display merged data
st.write("### Merged Data Preview")
st.dataframe(filtered_df)
