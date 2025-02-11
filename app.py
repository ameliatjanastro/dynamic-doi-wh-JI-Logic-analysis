import pandas as pd
import streamlit as st
import plotly.express as px

# Define file paths
file_paths = {
    "Logic A": "logic a.csv",
    "Logic B": "logic b.csv",
    "Logic C": "logic c.csv",
    "Logic D": "logic d.csv",
}
# Load and normalize data
common_columns = ["product_id", "product_name", "vendor_id", "primary_vendor_name", "business_tagging", "location_id", "Pareto"]
logic_columns = [
    'coverage', 'New DOI Policy WH', 'New RL Qty', 'New RL Value', 'Landed DOI'
]

dfs = []
for key in ["Logic A", "Logic B", "Logic C", "Logic D"]:
    path = file_paths[key]
    try:
        df = pd.read_csv(path, dtype={"product_id": str})
        logic_cols = [col for col in df.columns if any(lc in col for lc in logic_columns)]
        df = df[common_columns + logic_cols]
        df = df.rename(columns={col: col.split(') ')[-1] for col in df.columns})
        df["Logic"] = key
        dfs.append(df)
    except Exception as e:
        st.error(f"Error reading {key}: {e}")

# Merge data
data = pd.concat(dfs, ignore_index=True).sort_values(by=["product_id", "Logic"], key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4}))

# Streamlit UI
st.title("Comparison of RL Quantity Logics")

# Sidebar filters
st.sidebar.header("Filters")
product_options = data[['product_id', 'product_name']].drop_duplicates()
product_options['product_display'] = product_options['product_id'] + " - " + product_options['product_name']
selected_product = st.sidebar.selectbox("Select Product", product_options['product_display'])
#selected_pareto = st.sidebar.multiselect("Select Pareto", data["Pareto"].dropna().unique())
#selected_location = st.sidebar.multiselect("Select Location ID", data["location_id"].dropna().unique())
#selected_business_tag = st.sidebar.multiselect("Select Business Tag", data["business_tagging"].dropna().unique())

filtered_data = data[
    (data["product_id"] == selected_product.split(" - ")[0]) #&
    #(data["Pareto"].isin(selected_pareto) if selected_pareto else True) &
    #(data["location_id"].isin(selected_location) if selected_location else True) &
    #(data["business_tagging"].isin(selected_business_tag) if selected_business_tag else True)
]

view_option = st.sidebar.radio("View by", ["Product ID", "Vendor"])

if view_option == "Vendor":
    grouped_data = filtered_data.groupby(["vendor_id", "primary_vendor_name", "Logic"], as_index=False).agg({
        "New RL Qty": "sum",
        "New RL Value": "sum",
        "coverage": "max",
        "New DOI Policy WH": "mean",
        "Landed DOI": "mean"
    })
else:
    grouped_data = filtered_data

# Display table
st.write("### Comparison Table")
st.dataframe(grouped_data.sort_values(by=["Logic"], key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4})), hide_index=True)

# Plot comparison graph
st.write("### Comparison Graph")
fig = px.bar(grouped_data, x="Logic", y="New RL Qty", color="Logic", title="Comparison of New RL Qty Across Logics")
st.plotly_chart(fig)

