from pathlib import Path
from typing import Dict

import pandas as pd
from housing_data.build_data_utils import (
    NUMERICAL_COLUMNS,
    PUBLIC_DIR,
    add_per_capita_columns,
    write_to_json_directory,
)


def load_crosswalk_df() -> pd.DataFrame:
    # TODO: cache this file to housing-data-data to speed up builds by a few seconds
    crosswalk_df = pd.read_csv(
        "http://data.nber.org/cbsa-csa-fips-county-crosswalk/cbsa2fipsxw.csv"
    )

    # Could also get county name from 'countycountyequivalent' in crosswalk_df... I'm indifferent, just using the
    # one from counties_df for now.
    crosswalk_df = (
        crosswalk_df[["fipsstatecode", "fipscountycode", "csatitle", "cbsatitle"]]
        .rename(
            columns={
                "fipsstatecode": "fips_state",
                "fipscountycode": "fips_county",
                "csatitle": "csa_name",
                "cbsatitle": "cbsa_name",
            }
        )
        .dropna(subset=["cbsa_name"])[
            ["fips_state", "fips_county", "csa_name", "cbsa_name"]
        ]
    )

    return crosswalk_df


def combine_metro_rows(
    df: pd.DataFrame, metro_type: str, crosswalk_df: pd.DataFrame
) -> pd.DataFrame:
    """
    :param metro_type: 'cbsa' or 'csa'
    """
    assert metro_type in ["cbsa", "csa"]

    metro_col = f"{metro_type}_name"

    if metro_type == "cbsa":
        other_metro_col = "csa_name"
    elif metro_type == "csa":
        other_metro_col = "cbsa_name"
    else:
        raise ValueError(f"Unknown metro_type: {metro_type}")

    combined_df = (
        df.drop(columns=[other_metro_col])
        .groupby([metro_col, "year"])
        .agg(**get_aggregate_functions())
        .reset_index()
        .rename(columns={metro_col: "metro_name"})
        .assign(metro_type=metro_type)
    )

    # Only keep a metros in 2021 if all of its counties were observed.
    # Most counties are actually not observed (yet) in 2021, because lots of cities are only surveyed
    # yearly, not monthly.
    num_counties_in_each_metro = (
        crosswalk_df.groupby(metro_col)
        .size()
        .reset_index(name="num_counties")
        .rename(columns={metro_col: "metro_name"})
    )
    combined_df = combined_df.merge(
        num_counties_in_each_metro, on="metro_name", how="left"
    )

    combined_df = combined_df[
        (combined_df["year"] != "2021")
        | (combined_df["num_observed_counties"] == combined_df["num_counties"])
    ]

    combined_df = combined_df.drop(columns=["num_observed_counties", "num_counties"])

    return combined_df


def get_aggregate_functions() -> Dict[str, pd.NamedAgg]:
    aggregate_functions = {
        col: pd.NamedAgg(column=col, aggfunc="sum") for col in NUMERICAL_COLUMNS
    }
    aggregate_functions["county_names"] = pd.NamedAgg(
        column="county_name", aggfunc=lambda counties: counties.tolist()
    )
    aggregate_functions["population"] = pd.NamedAgg(column="population", aggfunc="sum")

    # So that we can check if all the counties in a metro were observed in that year
    aggregate_functions["num_observed_counties"] = pd.NamedAgg(
        column="county_name", aggfunc="count"
    )

    return aggregate_functions


def load_metros(counties_df: pd.DataFrame) -> None:
    counties_df = counties_df.drop(
        columns=[col for col in counties_df.columns if "_per_capita" in col]
    )

    crosswalk_df = load_crosswalk_df()

    merged_df = crosswalk_df.merge(
        counties_df, on=["fips_state", "fips_county"], how="left"
    ).drop(
        columns=[
            "fips_state",
            "fips_county",
            "region_code",
            "division_code",
            "survey_date",
        ]
    )

    cbsas_df = combine_metro_rows(merged_df, "cbsa", crosswalk_df)
    csas_df = combine_metro_rows(merged_df, "csa", crosswalk_df)

    metros_df = pd.concat([cbsas_df, csas_df])

    add_per_capita_columns(metros_df)

    metros_df["path"] = metros_df["metro_name"].str.replace("/", "-")
    metros_df["name"] = metros_df["metro_name"]

    metros_df.to_parquet(PUBLIC_DIR / "metros_annual.parquet")

    (
        metros_df[["metro_name", "metro_type", "path", "county_names"]]
        .drop_duplicates(subset=["metro_name", "metro_type", "path"])
        .sort_values("metro_name")
        .to_json(PUBLIC_DIR / "metros_list.json", orient="records")
    )

    write_to_json_directory(
        metros_df.drop(columns=["county_names"]),
        Path(PUBLIC_DIR, "metros_data"),
        ["path"],
    )
