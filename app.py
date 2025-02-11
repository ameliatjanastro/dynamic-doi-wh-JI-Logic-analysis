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
logic_columns = [
    'coverage', 'New DOI Policy WH', 'New RL Qty', 'New RL Value', 'Landed DOI'
]

dfs = []
for key, path in file_paths.items():
    try:
        df = pd.read_csv(path, dtype={"product_id": str})
        logic_cols = [col for col in df.columns if any(lc in col for lc in logic_columns)]
        df = df[['product_id', 'product_name', 'vendor_id', 'primary_vendor_name'] + logic_cols]
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
product_search = st.sidebar.text_input("Search Product ID or Name")
selected_product = st.sidebar.selectbox("Select Product ID", data["product_id"].unique())

# Filter data by selected product
filtered_data = data[data["product_id"] == selected_product]

# Display table
st.write("### Comparison Table")
st.dataframe(filtered_data[logic_columns + ["Logic"]])

# Plot comparison graph
st.write("### Comparison Graph")
fig, ax = plt.subplots(figsize=(8, 5))
for logic in filtered_data["Logic"].unique():
    subset = filtered_data[filtered_data["Logic"] == logic]
    ax.bar(logic, subset["New RL Qty"].values[0], label=logic)
ax.set_ylabel("New RL Qty")
ax.set_title("Comparison of New RL Qty Across Logics")
plt.xticks(rotation=45)
st.pyplot(fig)
