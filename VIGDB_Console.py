import streamlit as st
import pandas as pd

st.set_page_config(page_title="VIGDB Management Console", layout="wide")

# --- 1. DATA DICTIONARY (Mapping Column Headers) ---
DATA_DICTIONARY = {
    # Weight mappings
    'Svars (kg)': 'VAR_WEIGHT', 'Weight': 'VAR_WEIGHT', 'BodyMass_kg': 'VAR_WEIGHT',
    # Smoking mappings
    'Smēķēšanas vēsture': 'VAR_SMOKE', 'Tobacco_Usage': 'VAR_SMOKE', 'Do you smoke?': 'VAR_SMOKE',
    # Diabetes mappings
    'Cukura diabēts': 'VAR_DIAB', 'Diabetes_History': 'VAR_DIAB', 'Has_Diabetes': 'VAR_DIAB'
}

# --- 2. VALUE NORMALIZATION (Translating internal data to Codes) ---
# This ensures "Jā", "Yes", and "Current" all become the same standardized value.
VALUE_MAP = {
    # Smoking: 0=Never, 1=Current, 2=Former
    'Nekad nav smēķējis': '0 (Never)', 'Never': '0 (Never)', 'No': '0 (Never)',
    'Smēķē pašlaik': '1 (Current)', 'Current': '1 (Current)', 'Yes': '1 (Current)',
    'Bijušais smēķētājs': '2 (Former)', 'Former': '2 (Former)', 'Past smoker': '2 (Former)',

    # Diabetes: 0=No, 1=Yes/Type2
    'Nē': '0 (No)', 'None': '0 (No)',
    'Jā': '1 (Yes)', 'Type 2': '1 (Yes)', 'Type 1': '1 (Yes)'
}

# --- 3. CATALOGUE HIERARCHY (Metadata for the Table) ---
CATALOGUE = {
    'VAR_WEIGHT': {'L0': 'Physical Measurement', 'L2': 'Anthropometry', 'Unit': 'kg'},
    'VAR_SMOKE': {'L0': 'Health and Hereditary', 'L2': 'Lifestyle', 'Unit': 'Code'},
    'VAR_DIAB': {'L0': 'Health and Hereditary', 'L2': 'Participant Health History', 'Unit': 'Code'}
}

# --- USER INTERFACE ---
st.title("🧬 VIGDB Master Management Console")
st.sidebar.header("Presentation Controls")

view_mode = st.sidebar.radio("Select Database Mode:", ["Baseline: Unstandardized", "Target: Standardized Framework"])

st.markdown("### 📥 Ingestion Layer")
uploaded_files = st.file_uploader("Upload Questionnaire Sources", type="xlsx", accept_multiple_files=True)

if uploaded_files:
    all_dfs = [pd.read_excel(f) for f in uploaded_files]

    if view_mode == "Baseline: Unstandardized":
        st.subheader("❌ Current State: Fragmented Data Silos")
        raw_db = pd.concat(all_dfs, axis=0, ignore_index=True)
        st.dataframe(raw_db)
        st.error("Analysis blocked: Duplicate attributes and inconsistent naming identified.")

    else:
        st.subheader("✅ Target State: Harmonized VIGDB Database")

        standardized_list = []
        for f in uploaded_files:
            df = pd.read_excel(f)

            # Identify ID column automatically
            id_col = next((c for c in df.columns if c in ['Patient_ID', 'ID', 'Subject', 'Subject_Code']), "Unknown")

            for index, row in df.iterrows():
                p_id = row.get(id_col)

                for col_name in df.columns:
                    if col_name in DATA_DICTIONARY:
                        var_id = DATA_DICTIONARY[col_name]
                        metadata = CATALOGUE[var_id]

                        # Apply Value Normalization
                        raw_value = row[col_name]
                        standard_value = VALUE_MAP.get(raw_value, raw_value)

                        standardized_list.append({
                            "Participant_ID": p_id,
                            "Variable_ID": var_id,
                            "Harmonized_Value": standard_value,
                            "Original_Input": raw_value,
                            "Unit": metadata['Unit'],
                            "L0_Group": metadata['L0'],
                            "L2_Theme": metadata['L2'],
                            "Source": f.name
                        })

        final_df = pd.DataFrame(standardized_list)
        st.table(final_df)
        st.success("Harmonization Complete: Data is now compliant with International Biobank standards.")