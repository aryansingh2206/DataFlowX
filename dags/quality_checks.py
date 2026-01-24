import json
import great_expectations as ge


def validate_dataframe(df, expectation_file_path: str):
    with open(expectation_file_path, "r") as f:
        suite = json.load(f)

    ge_df = ge.from_pandas(df)

    result = ge_df.validate(
        expectation_suite=suite,
        result_format="SUMMARY",
    )

    if not result["success"]:
        raise Exception(
            f"Data quality checks failed: {result['statistics']}"
        )

    print("✅ Data quality checks passed")
