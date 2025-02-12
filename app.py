import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

pareto_order = ["X", "A", "B", "C", "D", "New SKU A", "New SKU B", "New SKU C", "New SKU D", "No Sales L3M"]
custom_colors = ["#20639B", "#3CAEA3", "#F6D55C", "#ED553B"]  # Light Blue & Gray Tones
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
    st.sidebar.header("Filters")
    view_option = st.sidebar.radio("View by", ["Product ID", "Vendor"])
    
    if view_option == "Product ID":
        product_options = data[['product_id', 'product_name']].drop_duplicates()
        product_options['product_display'] = product_options['product_id'] + " - " + product_options['product_name']
        selected_product = st.sidebar.selectbox("Select Product", product_options['product_display'])
        selected_data = data[data["product_id"] == selected_product.split(" - ")[0]]
    elif view_option == "Vendor":
        # Create vendor display selection
        data["vendor_display"] = data["vendor_id"].astype(str) + " - " + data["primary_vendor_name"]
        selected_vendor = st.sidebar.selectbox("Select Vendor", data["vendor_display"].unique())
    
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
    st.write("### Comparison Table")
    table_columns = ["Logic", "coverage", "New RL Qty", "New RL Value", "New DOI Policy WH", "Landed DOI", "Landed DOI - JI"]
    st.dataframe(selected_data[table_columns].sort_values(by="Logic", key=lambda x: x.map({"Logic A": 1, "Logic B": 2, "Logic C": 3, "Logic D": 4})), hide_index=True, use_container_width=True)

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
    
    for index, row in selected_data.iterrows():
        # ✅ First Bar: Landed DOI
        fig.add_trace(go.Bar(
            x=[row["Logic"]],
            y=[row["Landed DOI"]],
            name=f"{row['Logic']} - Landed DOI",
            marker=dict(color=row["color"]),
        ))
    
        # ✅ Second Bar: Landed DOI - JI
        fig.add_trace(go.Bar(
            x=[row["Logic"]],
            y=[row["Landed DOI - JI"]],
            name=f"{row['Logic']} - Landed DOI - JI",
            marker=dict(color=row["color"], opacity=0.6),  # Lighter color for distinction
        ))

        drop_value = round(row["Landed DOI"] - row["Landed DOI - JI"], 1)  # 1 decimal place
        # ✅ Add a diagonal line between the two bars
        fig.add_trace(go.Scatter(
            x=[row["Logic"], row["Logic"]],  # Same x-axis position
            y=[row["Landed DOI"], row["Landed DOI - JI"]],  # Connect the bars
            mode="lines+text",
            line=dict(color="red", width=1, dash="solid"),  # Dashed black line
            name=f"Drop {row['Logic']}",
            text=[None, f"{drop_value}"],  # Show drop value
            textposition="middle right",
        ))
    
    # ✅ Add horizontal line at 2 (Safe threshold)
    fig.add_hline(y=2, line_dash="dash", line_color="red", annotation_text="Minimum Safe Level (2)", annotation_position="top right")
    
    # ✅ Graph layout settings
    fig.update_layout(
        xaxis_title="Logic",
        yaxis_title="Days",
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True),
        width=700,  # ✅ Adjust width (half page size)
        height=500,  # ✅ Adjust height
        showlegend=False
    )
    
    # ✅ Display graph in Streamlit
    st.write("### DOI Movement Comparison Graph")
    st.plotly_chart(fig, use_container_width=False)

elif page == "Inbound Quantity Simulation":

    st.title("Inbound Quantity Trend by Ship Date")

    st.markdown(
        """
        <style>
        html,{
            overflow-y: hidden !important;  /* ✅ Completely disable vertical scrolling */
          
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    data["Ship Date"] = pd.to_datetime(data["Ship Date"], errors="coerce")
    
   # Sidebar filters for Inbound Quantity Trend
    pareto_options = [p for p in pareto_order if p in data["Pareto"].dropna().unique()]

    selected_location = st.sidebar.selectbox("Select Location ID", data["location_id"].dropna().unique())
    selected_pareto = st.sidebar.multiselect("Select Pareto", pareto_options, default=[])
    selected_business_tag = st.sidebar.multiselect("Select Business Tag", data["business_tagging"].dropna().unique())

    chart_type = st.sidebar.radio("Select Chart Type", ["Line Chart", "Bar Chart"])

    # Apply filters to data (only for this graph)
    filtered_data = data[
        (data["Pareto"].isin(selected_pareto) if selected_pareto else True) &
        (data["location_id"] == selected_location if selected_location else True) &
        (data["business_tagging"].isin(selected_business_tag) if selected_business_tag else True)
    ]
    
    # ✅ Group by Ship Date and Logic to get total inbound quantity after filtering
    inbound_data = filtered_data.groupby(["Ship Date", "Logic"], as_index=False)["New RL Qty"].sum()
    
    # ✅ Create the line graph using Plotly Express
    if chart_type == "Line Chart":
        fig2 = px.line(
            inbound_data, 
            x="Ship Date", 
            y="New RL Qty", 
            color="Logic",  # Different colors per logic
            markers=True,  # Enable markers
            color_discrete_sequence=custom_colors,  # ✅ Apply custom colors
            title="Line Chart"
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
                text=logic_df["New RL Qty"].astype(str),  # Convert to text
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
            width=800,  # Increase graph width
            height=600,  # Increase graph height
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
            text=inbound_data["New RL Qty"].astype(str),  # 🔥 Auto display text labels inside bars
            color_discrete_sequence=custom_colors,  # ✅ Apply custom colors
            title="Bar Chart"
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
            width=800,  # Increase graph width
            height=600,  # Increase graph height
            autosize=False,
            margin=dict(l=20, r=20, t=50, b=50),
            showlegend=True
        )
          
        
    # ✅ Display in Streamlit
    #st.write("### Inbound Quantity Trend by Ship Date")
    st.plotly_chart(fig2, use_container_width=True)
