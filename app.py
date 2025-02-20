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
    "Logic A": "LDP85.csv",
    "Logic B": "LDP50.csv",
    "Logic C": "LDP0.csv",
}
# Load and normalize data
common_columns = ["product_id", "product_name", "vendor_id", "primary_vendor_name", "business_tagging", "location_id", "Pareto", "Ship Date","coverage", "New DOI Policy WH"]
logic_columns = [
     'New RL Qty', 'Landed DOI'
]

dfs = []
for key in ["Logic A", "Logic B", "Logic C"]:
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
data = pd.concat(dfs, ignore_index=True).sort_values(by=["product_id", "Logic"], key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3}))
# Convert 'New RL Value' to numeric (remove commas)
data["coverage"] = pd.to_datetime(data["coverage"], errors="coerce").dt.date
#data["New RL Value"] = data["New RL Value"].astype(str).str.replace(",", "", regex=True).astype(float)

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
    data["New RL Qty"] = pd.to_numeric(data["New RL Qty"], errors="coerce").fillna(0).astype(int)
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
        logic_order = {"Logic A": 1, "Logic B": 2, "Logic C": 3}
        selected_data = selected_data.sort_values(by="Logic", key=lambda x: x.map(logic_order))
      
    
            # Debugging: Check the output of aggregation
            #st.write("Aggregated Data Preview:", selected_data)
    
            # Display Table
            #table_columns = ["Logic", "New RL Qty", "coverage", "New DOI Policy WH", "Landed DOI"]
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
    table_columns = ["Logic", "coverage", "New RL Qty", "New DOI Policy WH", "Landed DOI", "Verdict"] #"Landed DOI - JI", 
    original_dtypes = selected_data.dtypes
    
    def highlight_cells(val):
        if val == "Tidak Aman":
            return "background-color: red; color: white;"  # Red background, white text
        return ""
  
    #formatted_df = selected_data.style.applymap(highlight_cells, subset=["Verdict"])
    formatted_df = selected_data[table_columns].sort_values(
        by="Logic", 
        key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3})
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
        selected_data["Landed DOI"] >= selected_data["Jarak Inbound"], "lightgreen", "red"
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
        landed_doi_ji = row["Landed DOI - JI"]
    
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
        fig.add_trace(go.Bar(
            x=[logic_label],
            y=[landed_doi_ji],
            name=f"{logic_label} - Landed DOI - JI",
            marker=dict(color=row["color"], opacity=0.6),  # Lighter color for distinction
            width=bar_width,
            offset=offset,  # Shift left to center
        ))
    for index, row in selected_data.iterrows():
        print(f"Logic: {row['Logic']}, Landed DOI: {row['Landed DOI']}, Landed DOI - JI: {row['Landed DOI - JI']}")

    for index, row in selected_data.iterrows():
        drop_value = round(float(row["Landed DOI"]) - float(row["Landed DOI - JI"]), 2)
        #center_x = [str(logic) for logic in selected_data["Logic"]]  # Use same x values for alignment

        # ✅ Add Drop Line (Scatter, Placed in Center)
        fig.add_trace(go.Scatter(
            x=[row["Logic"], row["Logic"]],
            y=[row["Landed DOI"], row["Landed DOI - JI"]],
            mode="lines",
            line=dict(color="red", width=2, dash="solid"),  # Solid red line
            name=f"Drop {row['Logic']}",
            yaxis="y2",  # ✅ Use secondary y-axis to place it on top
            #text=[f"<span style='background-color:yellow; padding:2px'>{drop_value:.1f}</span>"],  
            #textposition="top center",
            #textfont=dict(color="black"),  # ✅ Black text for visibility
            hoverinfo="skip",
            showlegend = False# ✅ Ensure hover shows exact value
        ))

        fig.add_annotation(
            x=row["Logic"],
            y=row["Landed DOI - JI"] + 0.5,  # ✅ Offset to avoid overlap
            text=f"{round(float(row['Landed DOI']) - float(row['Landed DOI - JI']), 2)}",
            showarrow=False,
            font=dict(color="black", size=12),
            bgcolor="yellow",  # ✅ Background color for better visibility
            borderpad=4, 
        )
       
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
        "Logic Name": ["Logic A", "Logic B", "Logic C"],
        "Logic Details": [
            "LDP LBH 0%",
            "LDP LBH 50%",
            "LDP LBH 85%"
           
        ]
    }
    
    # ✅ Convert to DataFrame & Display Table
    logic_df = pd.DataFrame(logic_details)
    st.dataframe(logic_df, hide_index=True, use_container_width=True)

elif page == "Inbound Quantity Simulation":
    st.title("Inbound Quantities Simulation by Ship Date")
    
    st.markdown(
        """
        <style>
        html,{
            overflow-y: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    data["Ship Date"] = pd.to_datetime(data["Ship Date"], errors="coerce").dt.date
    
    # Sidebar filters
    chart_type = st.sidebar.radio("Select Chart Type", ["Line Chart", "Bar Chart"])
    selected_location = st.sidebar.selectbox("Select Location ID", data["location_id"].dropna().unique())
    selected_business_tag = st.sidebar.multiselect("Select Business Tag", data["business_tagging"].dropna().unique())
    
    # Apply filters but keep all data available
    filtered_data = data.copy()
    if selected_location:
        filtered_data = filtered_data[filtered_data["location_id"] == selected_location]
    if selected_business_tag:
        filtered_data = filtered_data[filtered_data["business_tagging"].isin(selected_business_tag)]
    
    # Display dataset details
    st.write("Filtered Data Sample:", filtered_data.head())
    st.write("Filtered Data Shape:", filtered_data.shape)
    st.write("Total RL Qty Sum Before Processing:", data["New RL Qty"].sum())
    
    # Group data but keep logic selection separate
    inbound_data = data[data["primary_vendor_name"] != "0"].groupby(["Ship Date", "Logic"], as_index=False)["New RL Qty"].sum()
    
    # Logic selection without filtering main data
    filtered_data["Landed DOI"] = pd.to_numeric(filtered_data["Landed DOI"], errors="coerce")
    filtered_data["New RL Qty"] = pd.to_numeric(filtered_data["New RL Qty"], errors="coerce")
    logic_options = filtered_data["Logic"].unique()
    
    selected_logic = st.selectbox("Select Logic", logic_options, key="logic_dropdown")
    
    # Compute values based on selected_logic
    inbound_data_week = filtered_data[filtered_data["Logic"] == selected_logic]["New RL Qty"].sum()
    tidakaman = filtered_data[(filtered_data["Logic"] == selected_logic) & (filtered_data["Landed DOI"] < 5)]["New RL Qty"].count()
    
    st.markdown(f"##### Total RL Qty for **{selected_logic}**: {inbound_data_week} | Total SKU Tidak Aman (Landed DOI < 5): <span style='color:red; font-weight:bold;'>{tidakaman}</span>", unsafe_allow_html=True)
    
    table_tidakaman = ["Logic", "product_id", "product_name", "Pareto", "primary_vendor_name", "New RL Qty", "New DOI Policy WH", "Landed DOI"]
    tidakaman_df = filtered_data[(filtered_data["Landed DOI"] < 5) & (filtered_data["Logic"] == selected_logic)][table_tidakaman]
    tidakaman_df = tidakaman_df.sort_values(by="Logic")
    
    csv = tidakaman_df.to_csv(index=False)
    st.download_button(label="📥 Download SKU Tidak Aman :( ", data=csv, file_name="tidakamanlist.csv", mime="text/csv")
    
    # Plot chart
    if chart_type == "Line Chart":
        fig2 = px.line(inbound_data, x="Ship Date", y="New RL Qty", color="Logic", markers=True)
    else:
        fig2 = px.bar(inbound_data, x="Ship Date", y="New RL Qty", color="Logic", text=inbound_data["New RL Qty"].astype(int).astype(str))
    
    st.plotly_chart(fig2, use_container_width=True)


#elif page == "Inbound Quantity Simulation":

   # st.title("Inbound Quantities Simulation by Ship Date")

    #st.markdown(
        """
     #   <style>
     #   html,{
     #       overflow-y: hidden !important;  /* ✅ Completely disable vertical scrolling */
          
     #   }
    #    </style>
     #   """,
     #   unsafe_allow_html=True
   # )
    
   # data["Ship Date"] = pd.to_datetime(data["Ship Date"], errors="coerce").dt.date
    
   # Sidebar filters for Inbound Quantity Trend
  #  chart_type = st.sidebar.radio("Select Chart Type", ["Line Chart", "Bar Chart"])
    #data['Pareto'] = data['Pareto'].fillna('Blank')
    #pareto_options = [p for p in pareto_order if p in data["Pareto"].unique()]

   # selected_location = st.sidebar.selectbox("Select Location ID", data["location_id"].dropna().unique())
    #selected_pareto = st.sidebar.multiselect("Select Pareto", pareto_options, default=pareto_options)
  #  selected_business_tag = st.sidebar.multiselect("Select Business Tag", data["business_tagging"].dropna().unique())

    

    # Apply filters to data (only for this graph)
  #  filtered_data = data[
  #      (data["location_id"] == selected_location if selected_location else True) &
  #      (data["business_tagging"].isin(selected_business_tag) if selected_business_tag else True)
  #  ]
    #(data["Pareto"].isin(selected_pareto) if selected_pareto else True) &
    
    # ✅ Group by Ship Date and Logic to get total inbound quantity after filtering
 #   st.write("Filtered Data Sample:", filtered_data.head())
 #   st.write("Filtered Data Shape:", filtered_data.shape)
 #   st.write("Total RL Qty Sum Before Processing:", data["New RL Qty"].sum())
 #   inbound_data = (data[data["primary_vendor_name"] != "0"].groupby(["Ship Date", "Logic"], as_index=False)["New RL Qty"].sum())

 #   filtered_data["Landed DOI"] = pd.to_numeric(filtered_data["Landed DOI"], errors="coerce")
 #   filtered_data["New RL Qty"] = pd.to_numeric(filtered_data["New RL Qty"], errors="coerce")
 #   filtered_logic_data = filtered_data[filtered_data["primary_vendor_name"] != "0"]
 #   logic_options = filtered_logic_data["Logic"].unique()

 #   st.markdown(
 #   """
#    <style>
 #   div[data-testid="stSelectbox"] {
 #       width: auto !important;
 #       display: inline-block !important;
 #   }
 #   </style>
 #   """,
 #   unsafe_allow_html=True
 #   )

    # Select Logic first
   # selected_logic = st.selectbox("", logic_options, key="logic_dropdown", label_visibility="collapsed")
    
    # Compute values based on selected_logic
 #   inbound_data_week = filtered_logic_data.loc[filtered_logic_data["Logic"] == selected_logic, "New RL Qty"].sum()
 #   tidakaman = filtered_logic_data.loc[
 #       (filtered_logic_data["Logic"] == selected_logic) & 
 #       (filtered_logic_data["Landed DOI"] < 5), 
 #       "New RL Qty"
 #   ].count()
    
  #  st.markdown(f"##### Total RL Qty for **{selected_logic}**: {inbound_data_week} | Total SKU Tidak Aman (Landed DOI < 5): <span style='color:red; font-weight:bold;'>{tidakaman}</span>", 
   #     unsafe_allow_html=True)


   # table_tidakaman = ["Logic", "product_id","product_name","Pareto", "primary_vendor_name","New RL Qty", "New DOI Policy WH", "Landed DOI"]
    #original_dtypes = selected_data.dtypes
 #   tidakaman_df = filtered_logic_data[(filtered_logic_data["Landed DOI"] < 5) & (filtered_logic_data["Logic"] == selected_logic)][table_tidakaman]
  #  tidakaman_df = tidakaman_df.sort_values(by="Logic", key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3}))

 #   csv = tidakaman_df.to_csv(index=False)

    # Export Button (Without Displaying DataFrame)
 #   st.download_button(
 #       label="📥 Download SKU Tidak Aman :( ",
 #       data=csv,
 #       file_name="tidakamanlist.csv",
 #       mime="text/csv"
#    )

#    st.markdown("---")

    freq_vendors = pd.read_csv("Freq vendors.csv")
    freq_vendors["Inbound Days"] = freq_vendors["Inbound Days"].str.split(", ")
    inbound_data2 = (filtered_data[filtered_data["primary_vendor_name"] != "0"].groupby(["primary_vendor_name", "Logic"], as_index=False).agg(
        **{"Sum RL Qty": ("New RL Qty", "sum"), "First Ship Date": ("Ship Date", "min")}))
    inbound_data2 = inbound_data2[inbound_data2["Logic"] == selected_logic]
    merged_data = inbound_data2.merge(freq_vendors, left_on="primary_vendor_name", right_on="primary_vendor_name", how="right")

    merged_data["RL Qty per Freq"] = merged_data["Sum RL Qty"] / merged_data["Freq"]
    st.write("Inbound Data Sum Before Merge:", inbound_data2["Sum RL Qty"].sum())
    st.write("Inbound Data Sum After Merge:", merged_data["Sum RL Qty"].sum())

    # Select relevant columns
    final_table = merged_data[["primary_vendor_name", "Inbound Days", "Sum RL Qty", "First Ship Date", "RL Qty per Freq"]]
    table_freq = pd.DataFrame(final_table)
    st.dataframe(table_freq)


    # Create a mapping of weekday names to numbers (Monday = 0, ..., Sunday = 6)
    weekday_map = {
        "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6
    }
    
    # Expand rows based on frequency inbound days
    expanded_rows = []

    for _, row in merged_data.iterrows():
        # **Ensure "Inbound Days" is a valid list**
        inbound_days = row["Inbound Days"] if isinstance(row["Inbound Days"], list) else []
    
        if inbound_days:  # Only process vendors with valid inbound days
            first_ship_date = row["First Ship Date"]
    
            if pd.notna(first_ship_date):
                # **Get the week range (Monday-Sunday) for first ship date**
                start_of_week = first_ship_date - pd.Timedelta(days=first_ship_date.weekday())  # Monday of that week
                end_of_week = start_of_week + pd.Timedelta(days=6)  # Sunday of that week
    
                # Get inbound days as a list of weekday numbers
                inbound_weekdays = sorted(
                    [weekday_map[day] for day in inbound_days if day in weekday_map]
                )
    
                if not inbound_weekdays:
                    continue  # Skip vendors with no valid inbound days

                total_qty = row["Sum RL Qty"]
                num_days = len(inbound_weekdays)

                # Distribute RL Qty equally among inbound days
                split_qty = round(total_qty / num_days)
    
                # Start from the first ship date and find valid shipment days
                current_date = first_ship_date
    
                while current_date <= end_of_week:  # **Restrict to same week**
                    if current_date.weekday() in inbound_weekdays:
                        expanded_rows.append([
                            row["primary_vendor_name"], current_date, split_qty
                        ])
                    current_date += pd.Timedelta(days=1)  # Move to the next day

        
    # Convert expanded rows into DataFrame
    processed_data = pd.DataFrame(expanded_rows, columns=["Vendor Name", "Ship Date", "Adjusted RL Qty"])
    st.dataframe(processed_data)

    st.markdown("---")

    # Remove old frequent vendor data from filtered_data
    filtered_data_no_freq = filtered_data[~filtered_data["primary_vendor_name"].isin(freq_vendors["primary_vendor_name"])]
    
    # Append processed_data back into filtered_data to get all vendors
    updated_filtered_data = pd.concat([filtered_data_no_freq, processed_data], ignore_index=True)
    
    # **Step 3: Recalculate Inbound Data with Updated Ship Dates**
    inbound_data = (
        updated_filtered_data[updated_filtered_data["primary_vendor_name"] != "0"]
        .groupby(["Ship Date", "Logic"], as_index=False)["New RL Qty"].sum()
    )

    # ✅ Create the line graph using Plotly Express
    if chart_type == "Line Chart":
        fig2 = px.line(
            inbound_data, 
            x="Ship Date", 
            y="New RL Qty", 
            color="Logic",  # Different colors per logic
            markers=True,  # Enable markers
            color_discrete_sequence=custom_colors,  # ✅ Apply custom colors
            title="<b><span style='font-size:26px; color:#20639B;'>Line Chart</span></b>"
        )
    
       # ✅ Manually add scatter traces for text labels
        
        logic_colors = {trace.name: trace.line.color for trace in fig2.data}
    
        visible_logic = inbound_data["Logic"].unique()
        jitter_map = {logic: (i - len(visible_logic)/2) * 2 for i, logic in enumerate(visible_logic)}
        for logic in visible_logic:
            logic_df = inbound_data[inbound_data["Logic"] == logic]  # Filter data per logic
    
            # 🔹 Determine text position dynamically
            text_positions = []
            prev_value = None
            for value in logic_df["New RL Qty"]:
                if prev_value is None:
                    text_positions.append("top center")  # Default for first point
                elif value > prev_value:
                    text_positions.append("top right")  # Text above for increasing trend
                else:
                    text_positions.append("bottom right")  # Text below for decreasing trend
                prev_value = value
            
            fig2.add_trace(go.Scatter(
                x=logic_df["Ship Date"],
                y=logic_df["New RL Qty"],
                mode="text",  # Only text, no lines or markers
                text=logic_df["New RL Qty"].astype(int).astype(str),  # Convert to text
                textposition=text_positions,  # Position text above markers
                textfont=dict(size=12, color=logic_colors.get(logic, "black"), weight='bold'),
                showlegend=False,  # Hide extra legend entries
                visible=True if logic in visible_logic else "legendonly"
            ))
        
        # ✅ Improve layout
        fig2.update_layout(
            xaxis_title="Ship Date",
            yaxis_title="Total Inbound Quantity",
            xaxis=dict(showgrid=True),
            yaxis=dict(showgrid=True),
            width=1200,  # Increase graph width
            height=500,  # Increase graph height
            autosize=False,
            margin=dict(l=20, r=20, t=50, b=50),
            showlegend=True
        )
    else:  # Bar Chart
        fig2 = px.bar(
            inbound_data, 
            x="Ship Date", 
            y="New RL Qty", 
            color="Logic",  # Different colors per logic
            text=inbound_data["New RL Qty"].astype(int).astype(str),  # 🔥 Auto display text labels inside bars
            color_discrete_sequence=custom_colors,  # ✅ Apply custom colors
            title="<b><span style='font-size:26px; color:#20639B;'>Bar Chart</span></b>"
        
        )
    
        fig2.update_traces(
            textfont=dict(size=12, weight='bold')
        )
    
        # ✅ Improve layout
        fig2.update_layout(
            xaxis_title="Ship Date",
            yaxis_title="Total Inbound Quantity",
            xaxis=dict(showgrid=True),
            yaxis=dict(showgrid=True),
            width=1200,  # Increase graph width
            height=500,  # Increase graph height
            autosize=False,
            margin=dict(l=20, r=20, t=50, b=50),
            showlegend=True
        )
          
        
    # ✅ Display in Streamlit
    #st.write("### Inbound Quantity Trend by Ship Date")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ✅ Add Note Above Table
    st.write("**📝 Note:** All logics assume LDP LBH per 17 Feb 2025 → LDP+LBH are added to SOH, thus SOH might not be entirely accurate 🙂")
    
    # ✅ Define Logic Details Data
    logic_details = {
        "Logic Name": ["Logic A", "Logic B", "Logic C"],
        "Logic Details": [
            "LDP LBH 0%",
            "LDP LBH 50%",
            "LDP LBH 85%"
        ]
    }
    
    # ✅ Convert to DataFrame & Display Table
    logic_df = pd.DataFrame(logic_details)
    st.dataframe(logic_df, hide_index=True, use_container_width=True)

 
