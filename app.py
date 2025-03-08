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
        data = data[data["vendor_id"] != 0]
        data["vendor_display"] = np.where(data["primary_vendor_name"] == "0", data["vendor_id"].astype(str), data["vendor_id"].astype(str) + " - " + data["primary_vendor_name"])
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

        selected_data["Verdict"] = selected_data.apply(lambda row: "Tidak Aman" if row["Landed DOI"] < 5 else "Aman", axis=1)
        
        st.markdown("<b><span style='font-size:26px; color:#20639B;'>Comparison Table</span></b>", unsafe_allow_html=True)
        #st.write("### Comparison Table")
        table_columns = ["Logic", "coverage", "New RL Qty", "New RL Value", "New DOI Policy WH", "Landed DOI", "Verdict"] #"Landed DOI - JI", 
        original_dtypes = selected_data.dtypes
    
        def highlight_cells(val):
            if val == "Tidak Aman":
                return "background-color: #FF6961; color: white;"  # Red background, white text
            return ""
      
        #formatted_df = selected_data.style.applymap(highlight_cells, subset=["Verdict"])
        formatted_df = selected_data[table_columns].sort_values(
            by="Logic", 
            key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4})
        ).style.applymap(highlight_cells, subset=["Verdict"]).format({
            "New RL Value": "{:,.0f}",  # Adds comma separator (1,000s, no decimals)
            "New DOI Policy WH": "{:.2f}",  # 2 decimal places
            "Landed DOI": "{:.2f}",  # 2 decimal places
            #"Landed DOI - JI": "{:.2f}",  # 2 decimal places
        })
    
        #selected_data = selected_data.astype(original_dtypes)
    
        st.dataframe(formatted_df, hide_index=True, use_container_width=True)
    
    st.markdown(
    """
    <style>
    div[data-testid="stTable"] table {
        table-layout: fixed !important;  /* ✅ Fix column width */
        width: 100% !important;  /* ✅ Ensure full width */
    }
    </style>
    """,
    unsafe_allow_html=True
    )
    
    # Comparison Graph
    #st.write("### Comparison Graph")
    #fig = px.bar(selected_data, x="Logic", y="Landed DOI", color="Logic", title="Comparison of New RL Qty Across Logics")
    #st.plotly_chart(fig)
    
    import plotly.graph_objects as go
    
    # ✅ Define color based on "Landed DOI" threshold
    selected_data["Landed DOI"] = pd.to_numeric(selected_data["Landed DOI"], errors="coerce")
    
    # ✅ Fill NaN values with 0 (or another safe default)
    selected_data["Landed DOI"].fillna(0, inplace=True)
    selected_data["color"] = np.where(
        selected_data["Landed DOI"] >= 7, "lightgreen", "#FF6961"
    )
    
    # ✅ Create bar chart
    fig = go.Figure()
    
    bar_width = 0.3  # Adjust as needed
    offset = bar_width / 2  # Offset bars slightly

    # ✅ Convert Logic column to categorical type for correct alignment
    logic_labels = selected_data["Logic"].tolist()

    for index, row in selected_data.iterrows():
        logic_label = row["Logic"]  # Keep the label for x-axis
        landed_doi = row["Landed DOI"]
        #landed_doi_ji = row["Landed DOI - JI"]
    
        # ✅ First Bar: Landed DOI
        fig.add_trace(go.Bar(
            x=[logic_label],
            y=[landed_doi],
            name=f"{logic_label} - Landed DOI",
            marker=dict(color=row["color"]),
            width=bar_width,
            offset=-offset,  # Shift left to center
        ))
    
        # ✅ Second Bar: Landed DOI - JI
        #fig.add_trace(go.Bar(
         #   x=[logic_label],
         #   y=[landed_doi_ji],
          #  name=f"{logic_label} - Landed DOI - JI",
         #   marker=dict(color=row["color"], opacity=0.6),  # Lighter color for distinction
         #   width=bar_width,
         #   offset=offset,  # Shift left to center
  #    #  ))
   # for index, row in selected_data.iterrows():
       # print(f"Logic: {row['Logic']}, Landed DOI: {row['Landed DOI']}, Landed DOI - JI: {row['Landed DOI - JI']}")

    #for index, row in selected_data.iterrows():
    #    drop_value = round(float(row["Landed DOI"]) - float(row["Landed DOI - JI"]), 2)
    #    #center_x = [str(logic) for logic in selected_data["Logic"]]  # Use same x values for alignment

        # ✅ Add Drop Line (Scatter, Placed in Center)
   #    fig.add_trace(go.Scatter(
   #        x=[row["Logic"], row["Logic"]],
   #        y=[row["Landed DOI"],
      #     mode="lines",
      #     line=dict(color="red", width=2, dash="solid"),  # Solid red line
       #   name=f"Drop {row['Logic']}",
       #   yaxis="y2",  # ✅ Use secondary y-axis to place it on top
       #     #text=[f"<span style='background-color:yellow; padding:2px'>{drop_value:.1f}</span>"],  
       #     #textposition="top center",
        #    #textfont=dict(color="black"),  # ✅ Black text for visibility
        #    hoverinfo="skip",
       #     showlegend = False# ✅ Ensure hover shows exact value
      #  ))

     #   fig.add_annotation(
      #      x=row["Logic"],
      #      y=row["Landed DOI - JI"] + 0.5,  # ✅ Offset to avoid overlap
      #      text=f"{round(float(row['Landed DOI']) - float(row['Landed DOI - JI']), 2)}",
       #     showarrow=False,
       #     font=dict(color="black", size=12),
      #      bgcolor="yellow",  # ✅ Background color for better visibility
      #      borderpad=4, 
      #  )
       
    # ✅ Improve layout
    fig.update_layout(
        xaxis_title="Logic",
        yaxis_title="Days",
        xaxis=dict(
            type="category",  # ✅ Ensure correct categorical alignment
            showgrid=True,
        ),
        yaxis=dict(showgrid=True),
        width=1000,  # ✅ Adjust width (half page)
        height=500,
        bargap=0.1, 
        showlegend=False
    )

    # ✅ Update layout for scatter line (Secondary Y-Axis)
    fig.update_layout(
        yaxis2=dict(  # ✅ Create secondary y-axis for drop line
            overlaying="y",  # ✅ Places drop line on top
            showgrid=False,  # ✅ Prevents double grid lines
            zeroline=False,  
            visible=False  # ✅ Hide extra axis
        ),
        width=1000,  # ✅ Adjust width (half page)
        height=500,
        showlegend=False
    )
    
    # ✅ Display graph in Streamlit
    #st.write("### DOI Movement Comparison Graph")
    st.markdown("<b><span style='font-size:26px; color:#20639B;'>DOI Movement Comparison Graph</span></b>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=False)

    # ✅ Add Note Above Table
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

elif page == "Inbound Quantity Simulation":
    pareto_options = data["Pareto"].dropna().unique().tolist()
    
    selected_location = st.sidebar.selectbox("Select Location ID", data["location_id"].dropna().unique())
    selected_pareto = st.sidebar.multiselect("Select Pareto", pareto_options, default=[])
    selected_business_tag = st.sidebar.multiselect("Select Business Tag", data["business_tagging"].dropna().unique())
    
    # Apply filters
    filtered_data = data.copy()
    if selected_pareto:
        filtered_data = filtered_data[filtered_data["Pareto"].isin(selected_pareto)]
    if selected_location:
        filtered_data = filtered_data[filtered_data["location_id"] == selected_location]
    if selected_business_tag:
        filtered_data = filtered_data[filtered_data["business_tagging"].isin(selected_business_tag)]
    
    # Ensure numeric conversion
    filtered_data["Landed DOI"] = pd.to_numeric(filtered_data["Landed DOI"], errors="coerce")
    
    # Select Logic dropdown
    logic_options = filtered_data["Logic"].dropna().unique()
    selected_logic = st.selectbox("Select Logic", logic_options, key="logic_dropdown")
    
    # Compute total RL Quantity
    inbound_data_week = filtered_data.loc[filtered_data["Logic"] == selected_logic, "New RL Qty"].sum()
    
    tidakaman = filtered_data.loc[
        (filtered_data["Logic"] == selected_logic) & (filtered_data["Landed DOI"] < 5),
        "New RL Qty"
    ].count()
    
    st.markdown(f"##### Total RL Qty for **{selected_logic}**: {inbound_data_week} | Total SKU Tidak Aman (Landed DOI < 5): <span style='color:red; font-weight:bold;'>{tidakaman}</span>", 
        unsafe_allow_html=True)
    
    # Create table for "Tidak Aman" SKUs
    tidakaman_df = filtered_data[(filtered_data["Landed DOI"] < 5) & (filtered_data["Logic"] == selected_logic)][
        ["Logic", "product_id", "product_name", "Pareto", "primary_vendor_name", "New RL Qty", "New RL Value", "New DOI Policy WH", "Landed DOI"]
    ]
    
    # Sorting with custom order
    tidakaman_df["Logic"] = pd.Categorical(tidakaman_df["Logic"], ["Logic A", "Logic B", "Logic C", "Logic D"], ordered=True)
    tidakaman_df = tidakaman_df.sort_values(by="Logic")
    
    # Download button
    st.download_button(
        label="📥 Download SKU Tidak Aman",
        data=tidakaman_df.to_csv(index=False),
        file_name="tidakamanlist.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    
    # Read frequency vendor data
    # Read frequency vendor data
    freq_vendors = pd.read_csv("Freq vendors.csv")
    freq_vendors["Inbound Days"] = freq_vendors["Inbound Days"].str.split(", ")
    
    # Merge vendor frequency data
    inbound_data2 = filtered_data.groupby(["primary_vendor_name", "Logic"], as_index=False).agg(
        **{"Sum RL Qty": ("New RL Qty", "sum"), "First Ship Date": ("Ship Date", "min")}
    )
    inbound_data2 = inbound_data2[inbound_data2["Logic"] == selected_logic]
    
    # Merge with frequency vendors
    merged_data = inbound_data2.merge(freq_vendors, on="primary_vendor_name", how="right")
    merged_data["Freq"] = merged_data["Freq"].fillna(1)  # Set default frequency to 1
    merged_data["RL Qty per Freq"] = (merged_data["Sum RL Qty"] / merged_data["Freq"]).fillna(0)
    
    # Ensure no NaN and cast to int
    merged_data["RL Qty per Freq"] = merged_data["RL Qty per Freq"].astype(int)
    
    # Display DataFrame after dropping NaN values
    st.dataframe(merged_data[["primary_vendor_name", "Inbound Days", "Sum RL Qty", "First Ship Date", "RL Qty per Freq"]].dropna())
    
    st.markdown("---")
    
    # **Step 1: Identify frequent vendors**
    freq_vendor_names = set(freq_vendors["primary_vendor_name"].unique())
    
    # **Step 2: Replace "New RL Qty" with "RL Qty per Freq" for frequent vendors**
    filtered_data["Adjusted RL Qty"] = filtered_data.apply(
        lambda row: merged_data.loc[merged_data["primary_vendor_name"] == row["primary_vendor_name"], "RL Qty per Freq"].values[0]
        if row["primary_vendor_name"] in freq_vendor_names else row["New RL Qty"],
        axis=1
    )
    st.write(filtered_data["Adjusted RL Qty"].head())
    # **Step 3: Aggregate inbound quantity correctly**
    inbound_data = filtered_data.groupby(["Ship Date", "Logic"], as_index=False)["Adjusted RL Qty"].sum()
    
    # **Step 4: Plot the corrected data**
    fig = px.bar(inbound_data, x="Ship Date", y="Adjusted RL Qty", color="Logic", text_auto=True)
    
    st.plotly_chart(fig, use_container_width=True)
    
    fig.update_layout(
        xaxis_title="Ship Date",
        yaxis_title="Total Inbound Quantity",
        width=1200,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # **Logic Details Table**
    logic_details = pd.DataFrame({
        "Logic Name": ["Logic A", "Logic B", "Logic C", "Logic D"],
        "Logic Details": [
            "cov sesuai RL everyday, dynamic DOI 50% * JI",
            "cov sesuai RL everyday, dynamic DOI JI",
            "cov sesuai RL everyday, dynamic DOI JI*FR Performance weight",
            "cov 14 Days, DOI Policy 5"
        ]
    })
    st.dataframe(logic_details, hide_index=True, use_container_width=True)

