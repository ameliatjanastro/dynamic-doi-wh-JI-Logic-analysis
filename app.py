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
    "Logic C": "logic c.csv",
    "Logic D": "logic d.csv",
}
# Load and normalize data
common_columns = ["product_id", "product_name", "vendor_id", "primary_vendor_name", "business_tagging", "location_id", "Pareto", "Ship Date"]
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
# Convert 'New RL Value' to numeric (remove commas)
data["coverage"] = pd.to_datetime(data["coverage"], errors="coerce").dt.date
data["New RL Value"] = data["New RL Value"].astype(str).str.replace(",", "", regex=True).astype(float)

#JI Dry Data
ji_dry = pd.read_csv("JI Dry new.csv")  # Replace with actual file name

# ✅ Ensure columns are correctly named
#ji_dry = ["product_id", "Jarak Inbound"]

if "product_id" in data.columns and "product_id" in ji_dry.columns:
    
    # ✅ Convert "product_id" to integer (handle errors gracefully)
    data["product_id"] = data["product_id"].astype(str)
    ji_dry["product_id"] = ji_dry["product_id"].astype(str)
    ji_dry["Jarak Inbound"] = pd.to_numeric(ji_dry["Jarak Inbound"], errors="coerce").fillna(0).astype(int)
    
    # ✅ Merge with default Jarak Inbound = 7 if missing
    data = data.merge(ji_dry, on="product_id", how="left").fillna({"Jarak Inbound": 7})
    data["Landed DOI"] = pd.to_numeric(data["Landed DOI"], errors="coerce").fillna(0).astype(int)
    #st.write("Data Columns:", data.columns)
    # ✅ Calculate new column
    data["Landed DOI - JI"] = data["Landed DOI"] - data["Jarak Inbound"]

# Create a navigation between pages
page = st.sidebar.selectbox("Choose a page", ["Inbound Quantity Simulation", "OOS Projection WH"])

if page == "OOS Projection WH":
    
    # Streamlit UI
    st.title("Comparison of RL Quantity Logics")
    
    # Sidebar filters
    #st.sidebar.header("Filters")
    view_option = st.sidebar.radio("View by", ["Product ID", "Vendor"])
    
    if view_option == "Product ID":
        product_options = data[['product_id', 'product_name']].drop_duplicates()
        product_options['product_display'] = product_options['product_id'] + " - " + product_options['product_name']
        selected_product = st.sidebar.selectbox("Select Product", product_options['product_display'])
        selected_data = data[data["product_id"] == selected_product.split(" - ")[0]]
    elif view_option == "Vendor":
        # Create vendor display selection
        data["vendor_display"] = data["vendor_id"].astype(str) + " - " + data["primary_vendor_name"]
        selected_vendor = st.sidebar.selectbox("Select Vendor", data.sort_values(by="vendor_id")["vendor_display"].unique())
    
        # Ensure vendor filtering is correct
        selected_vendor_id = selected_vendor.split(" - ")[0].strip()
        selected_data = data[data["vendor_id"].astype(str).str.strip() == selected_vendor_id]
    
        # Debugging: Check if selected_data has rows and expected columns
        if selected_data.empty:
            st.warning("No data available for this vendor. Please select a different vendor.")
        #else:
            #st.write("Selected Data Preview:", selected_data.head())
    
        if "coverage" in selected_data.columns:
            selected_data["coverage"] = pd.to_datetime(selected_data["coverage"], errors="coerce").dt.date
            selected_data = selected_data.dropna(subset=["coverage"])
    
        #selected_data = selected_data.drop_duplicates(subset=["vendor_id", "Logic"], keep="first")
            # Define aggregation dictionary
        agg_dict = {
                "New RL Qty": "sum",
                "New RL Value": "sum",
                "coverage": "max",  # Max date for coverage
                "New DOI Policy WH": "mean",
                "Landed DOI": "mean",
                "Landed DOI - JI": "mean",
                "Jarak Inbound": "min"
        }
    
        # Only aggregate existing columns
        existing_agg_cols = {k: v for k, v in agg_dict.items() if k in selected_data.columns}
            
            # Debug: Print available columns before aggregation
            #st.write("Available Columns Before Aggregation:", selected_data.columns.tolist())
            #st.write("Columns to Aggregate:", existing_agg_cols)
    
        # Convert numeric columns to appropriate types
        for col in existing_agg_cols.keys():
            if col != "coverage":  
                selected_data[col] = pd.to_numeric(selected_data[col], errors="coerce")  # Force invalid to NaN
        
        
        selected_data = selected_data.groupby(["vendor_id", "primary_vendor_name", "Logic"], as_index=False).agg(existing_agg_cols)
    
        # Sort by logic order (A -> D)
        logic_order = {"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4}
        selected_data = selected_data.sort_values(by="Logic", key=lambda x: x.map(logic_order))
      
    
            # Debugging: Check the output of aggregation
            #st.write("Aggregated Data Preview:", selected_data)
    
            # Display Table
            #table_columns = ["Logic", "New RL Qty", "New RL Value", "coverage", "New DOI Policy WH", "Landed DOI"]
            #st.write("### Comparison Table")
            #st.dataframe(selected_data[table_columns], hide_index=True)
    
            #table_columns = ["Logic"] + list(existing_agg_cols.keys())  # Only show logic columns
            #st.write("### Comparison Table")
            #st.dataframe(selected_data[table_columns], hide_index=True)
    
            # Plot Comparison Graph
            #st.write("### Comparison Graph")
            #fig = px.bar(selected_data, x="Logic", y="New RL Qty", color="Logic", title=f"Comparison of New RL Qty Across Logics for {selected_vendor}")
            #st.plotly_chart(fig)



#selected_pareto = st.sidebar.multiselect("Select Pareto", data["Pareto"].dropna().unique())
#selected_location = st.sidebar.multiselect("Select Location ID", data["location_id"].dropna().unique())
#selected_business_tag = st.sidebar.multiselect("Select Business Tag", data["business_tagging"].dropna().unique())

#selected_data = selected_data[
    #(selected_data["Pareto"].isin(selected_pareto) if selected_pareto else True) &
    #(selected_data["location_id"].isin(selected_location) if selected_location else True) &
    #(selected_data["business_tagging"].isin(selected_business_tag) if selected_business_tag else True)
#]

    # Show table with only logic columns

    selected_data["Verdict"] = selected_data.apply(lambda row: "Tidak Aman" if row["Landed DOI - JI"] < 2 else "Aman", axis=1)
    
    st.markdown("<b><span style='font-size:26px; color:#20639B;'>Comparison Table</span></b>", unsafe_allow_html=True)
    #st.write("### Comparison Table")
    table_columns = ["Logic", "coverage", "New RL Qty", "New RL Value", "New DOI Policy WH", "Landed DOI", "Landed DOI - JI", "Verdict"]
    original_dtypes = selected_data.dtypes
    
    def highlight_verdict(row):
        color = "background-color: red; color: white;" if row["Verdict"] == "Tidak Aman" else ""
        return [color] * len(row)

    formatted_df = selected_data[table_columns].sort_values(
        by="Logic", 
        key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4})
    ).style.format({
        "New RL Value": "{:,.0f}",  # Adds comma separator (1,000s, no decimals)
        "New DOI Policy WH": "{:.2f}",  # 2 decimal places
        "Landed DOI": "{:.2f}",  # 2 decimal places
        "Landed DOI - JI": "{:.2f}",  # 2 decimal places
    })

    selected_data = selected_data.astype(original_dtypes)
    st.dataframe(formatted_df, hide_index=True, use_container_width=True)
