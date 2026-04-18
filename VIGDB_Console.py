import json
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# LOAD JSON FILES
# ---------------------------------------------------------
@st.cache_data
def load_dictionary(path: str = "dictionary.json") -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)

@st.cache_data
def load_bmc_categories(path: str = "bmc_categories.json") -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)

@st.cache_data
def load_ukb_mapping(path: str = "ukb_mapping.json") -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)


# ---------------------------------------------------------
# PARSE QUESTIONNAIRE JSON
# ---------------------------------------------------------
def flatten_questionnaire(file_bytes: bytes, filename: str) -> pd.DataFrame:
    obj = json.loads(file_bytes.decode("utf-8"))
    questions = obj.get("questions", [])

    rows = []
    for q in questions:
        rows.append({
            "filename": filename,
            "form_id": obj.get("form_id"),
            "form_machine_id": obj.get("form_machine_id"),
            "language": obj.get("language"),
            "question_number": q.get("question_number"),
            "question_id_human": q.get("question_id_human"),
            "question_id_machine": q.get("question_id_machine"),
            "section": q.get("section"),
            "subsection": q.get("subsection"),
            "question_text": q.get("text"),
            "answer_raw": q.get("answer_raw")
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------
# MERGE PIPELINE
# ---------------------------------------------------------
def build_merged_tables(q_df, dict_df, bmc_df, ukb_df):
    # questionnaire → dictionary
    merged = q_df.merge(
        dict_df,
        on="question_id_machine",
        how="left",
        validate="m:1"
    )

    # dictionary → BMC
    merged = merged.merge(
        bmc_df,
        on="harmonized_variable",
        how="left",
        validate="m:1"
    )

    # dictionary → UKB
    merged = merged.merge(
        ukb_df,
        on="harmonized_variable",
        how="left",
        suffixes=("", "_ukb"),
        validate="m:1"
    )

    # ⭐ FIX: create improved classification path
    merged["improved_classification_path"] = (
        merged["level_0"].fillna("") + " > " +
        merged["level_1"].fillna("")
    )

    return merged



# ---------------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------------
def main():
    st.set_page_config(page_title="VIGDB Harmonization Console", layout="wide")

    st.title("VIGDB Harmonization Console")
    st.caption("BMC Latvia • UK Biobank • Improved BMC")

    uploaded_files = st.sidebar.file_uploader(
        "Upload questionnaire JSON files",
        type=["json"],
        accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("Upload one or more questionnaire JSON files to begin.")
        return

    # Parse all uploaded questionnaires
    q_frames = []
    for f in uploaded_files:
        try:
            df = flatten_questionnaire(f.read(), f.name)
            q_frames.append(df)
        except Exception as e:
            st.error(f"Could not parse {f.name}: {e}")

    if not q_frames:
        st.error("No valid questionnaire files found.")
        return

    q_df = pd.concat(q_frames, ignore_index=True)

    # Load reference tables
    dict_df = load_dictionary()
    bmc_df = load_bmc_categories()
    ukb_df = load_ukb_mapping()

    merged = build_merged_tables(q_df, dict_df, bmc_df, ukb_df)

    # Sidebar file selector
    file_choice = st.sidebar.selectbox(
        "Select a file to view",
        options=["All files"] + sorted(merged["filename"].unique())
    )

    if file_choice != "All files":
        view_df = merged[merged["filename"] == file_choice].copy()
    else:
        view_df = merged.copy()

    # ---------------------------------------------------------
    # TABS
    # ---------------------------------------------------------
    tab_bmc, tab_ukb, tab_improved = st.tabs([
        "BMC Classification",
        "UK Biobank Classification",
        "Improved BMC Classification"
    ])

    # ---------------------------------------------------------
    # BMC TAB
    # ---------------------------------------------------------
    with tab_bmc:
        st.subheader("BMC Classification")

        cols = [
            "filename",
            "question_text",
            "question_id_human",
            "question_id_machine",
            "harmonized_variable",
            "label_lv",
            "label_en",
            "level_0_id",
            "level_0",
            "level_1_id",
            "level_1",
            "level_2_id",
            "level_2",
            "level_isleaf_id",
            "level_isleaf"
        ]

        # Sort ONLY by filename (safe for all forms)
        bmc_view = view_df[cols].sort_values(
            ["filename"],
            na_position="last"
        )

        st.dataframe(bmc_view, use_container_width=True)

        st.download_button(
            "Download BMC CSV",
            bmc_view.to_csv(index=False).encode("utf-8"),
            file_name="bmc_classification.csv"
        )

    # ---------------------------------------------------------
    # UKB TAB
    # ---------------------------------------------------------
    with tab_ukb:
        st.subheader("UK Biobank Classification")

        cols = [
            "filename",
            "question_text",
            "question_id_machine",
            "harmonized_variable",
            "label_lv",
            "label_en",
            "ukb_category_id",
            "ukb_category_name",
            "ukb_subcategory",
            "ukb_field_group",
            "ukb_field_id",
            "ukb_field_name",
            "ukb_field_description",
            "ukb_field_url"
        ]

        ukb_view = view_df[cols].sort_values(
            ["filename"],
            na_position="last"
        )

        st.dataframe(ukb_view, use_container_width=True)

        st.download_button(
            "Download UKB CSV",
            ukb_view.to_csv(index=False).encode("utf-8"),
            file_name="ukb_mapping.csv"
        )

    # ---------------------------------------------------------
    # IMPROVED BMC TAB
    # ---------------------------------------------------------
    with tab_improved:
        st.subheader("Improved BMC Classification")

        cols = [
            "harmonized_variable",
            "label_lv",
            "label_en",
            "level_0",
            "level_1",
            "level_2",
            "level_isleaf",
            "improved_classification_path"
        ]

        improved_view = (
            view_df[cols]
            .drop_duplicates(subset=["harmonized_variable"])
            .sort_values("harmonized_variable")
        )

        st.dataframe(improved_view, use_container_width=True)

        st.download_button(
            "Download Improved BMC CSV",
            improved_view.to_csv(index=False).encode("utf-8"),
            file_name="improved_bmc_classification.csv"
        )


if __name__ == "__main__":
    main()
