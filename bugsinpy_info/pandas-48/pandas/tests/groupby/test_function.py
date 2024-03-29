import builtins
import datetime as dt
from io import StringIO
from string import ascii_lowercase

import numpy as np
import pytest

from pandas.errors import UnsupportedFunctionCall

import pandas as pd
from pandas import (
    DataFrame,
    Index,
    MultiIndex,
    NaT,
    Series,
    Timestamp,
    _is_numpy_dev,
    date_range,
    isna,
)
import pandas._testing as tm
import pandas.core.nanops as nanops
from pandas.util import _test_decorators as td


@pytest.fixture(
    params=[np.int32, np.int64, np.float32, np.float64],
    ids=["np.int32", "np.int64", "np.float32", "np.float64"],
)
def numpy_dtypes_for_minmax(request):
    """
    Fixture of numpy dtypes with min and max values used for testing
    cummin and cummax
    """
    dtype = request.param
    min_val = (
        np.iinfo(dtype).min if np.dtype(dtype).kind == "i" else np.finfo(dtype).min
    )
    max_val = (
        np.iinfo(dtype).max if np.dtype(dtype).kind == "i" else np.finfo(dtype).max
    )

    return (dtype, min_val, max_val)


@pytest.mark.parametrize("agg_func", ["any", "all"])
@pytest.mark.parametrize("skipna", [True, False])
@pytest.mark.parametrize(
    "vals",
    [
        ["foo", "bar", "baz"],
        ["foo", "", ""],
        ["", "", ""],
        [1, 2, 3],
        [1, 0, 0],
        [0, 0, 0],
        [1.0, 2.0, 3.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [True, True, True],
        [True, False, False],
        [False, False, False],
        [np.nan, np.nan, np.nan],
    ],
)
def test_groupby_bool_aggs(agg_func, skipna, vals):
    df = DataFrame({"key": ["a"] * 3 + ["b"] * 3, "val": vals * 2})

    # Figure out expectation using Python builtin
    exp = getattr(builtins, agg_func)(vals)

    # edge case for missing data with skipna and 'any'
    if skipna and all(isna(vals)) and agg_func == "any":
        exp = False

    exp_df = DataFrame([exp] * 2, columns=["val"], index=Index(["a", "b"], name="key"))
    result = getattr(df.groupby("key"), agg_func)(skipna=skipna)
    tm.assert_frame_equal(result, exp_df)


def test_max_min_non_numeric():
    # #2700
    aa = DataFrame({"nn": [11, 11, 22, 22], "ii": [1, 2, 3, 4], "ss": 4 * ["mama"]})

    result = aa.groupby("nn").max()
    assert "ss" in result

    result = aa.groupby("nn").max(numeric_only=False)
    assert "ss" in result

    result = aa.groupby("nn").min()
    assert "ss" in result

    result = aa.groupby("nn").min(numeric_only=False)
    assert "ss" in result


def test_intercept_builtin_sum():
    s = Series([1.0, 2.0, np.nan, 3.0])
    grouped = s.groupby([0, 1, 2, 2])

    result = grouped.agg(builtins.sum)
    result2 = grouped.apply(builtins.sum)
    expected = grouped.sum()
    tm.assert_series_equal(result, expected)
    tm.assert_series_equal(result2, expected)


# @pytest.mark.parametrize("f", [max, min, sum])
# def test_builtins_apply(f):


@pytest.mark.parametrize("f", [max, min, sum])
@pytest.mark.parametrize("keys", ["jim", ["jim", "joe"]])  # Single key  # Multi-key
def test_builtins_apply(keys, f):
    # see gh-8155
    df = pd.DataFrame(np.random.randint(1, 50, (1000, 2)), columns=["jim", "joe"])
    df["jolie"] = np.random.randn(1000)

    fname = f.__name__
    result = df.groupby(keys).apply(f)
    ngroups = len(df.drop_duplicates(subset=keys))

    assert_msg = f"invalid frame shape: {result.shape} (expected ({ngroups}, 3))"
    assert result.shape == (ngroups, 3), assert_msg

    tm.assert_frame_equal(
        result,  # numpy's equivalent function
        df.groupby(keys).apply(getattr(np, fname)),
    )

    if f != sum:
        expected = df.groupby(keys).agg(fname).reset_index()
        expected.set_index(keys, inplace=True, drop=False)
        tm.assert_frame_equal(result, expected, check_dtype=False)

    tm.assert_series_equal(getattr(result, fname)(), getattr(df, fname)())


def test_arg_passthru():
    # make sure that we are passing thru kwargs
    # to our agg functions

    # GH3668
    # GH5724
    df = pd.DataFrame(
        {
            "group": [1, 1, 2],
            "int": [1, 2, 3],
            "float": [4.0, 5.0, 6.0],
            "string": list("abc"),
            "category_string": pd.Series(list("abc")).astype("category"),
            "category_int": [7, 8, 9],
            "datetime": pd.date_range("20130101", periods=3),
            "datetimetz": pd.date_range("20130101", periods=3, tz="US/Eastern"),
            "timedelta": pd.timedelta_range("1 s", periods=3, freq="s"),
        },
        columns=[
            "group",
            "int",
            "float",
            "string",
            "category_string",
            "category_int",
            "datetime",
            "datetimetz",
            "timedelta",
        ],
    )

    expected_columns_numeric = Index(["int", "float", "category_int"])

    # mean / median
    expected = pd.DataFrame(
        {
            "category_int": [7.5, 9],
            "float": [4.5, 6.0],
            "timedelta": [pd.Timedelta("1.5s"), pd.Timedelta("3s")],
            "int": [1.5, 3],
            "datetime": [
                pd.Timestamp("2013-01-01 12:00:00"),
                pd.Timestamp("2013-01-03 00:00:00"),
            ],
            "datetimetz": [
                pd.Timestamp("2013-01-01 12:00:00", tz="US/Eastern"),
                pd.Timestamp("2013-01-03 00:00:00", tz="US/Eastern"),
            ],
        },
        index=Index([1, 2], name="group"),
        columns=["int", "float", "category_int", "datetime", "datetimetz", "timedelta"],
    )

    for attr in ["mean", "median"]:
        result = getattr(df.groupby("group"), attr)()
        tm.assert_index_equal(result.columns, expected_columns_numeric)

        result = getattr(df.groupby("group"), attr)(numeric_only=False)
        tm.assert_frame_equal(result.reindex_like(expected), expected)

    # TODO: min, max *should* handle
    # categorical (ordered) dtype
    expected_columns = Index(
        [
            "int",
            "float",
            "string",
            "category_int",
            "datetime",
            "datetimetz",
            "timedelta",
        ]
    )
    for attr in ["min", "max"]:
        result = getattr(df.groupby("group"), attr)()
        tm.assert_index_equal(result.columns, expected_columns)

        result = getattr(df.groupby("group"), attr)(numeric_only=False)
        tm.assert_index_equal(result.columns, expected_columns)

    expected_columns = Index(
        [
            "int",
            "float",
            "string",
            "category_string",
            "category_int",
            "datetime",
            "datetimetz",
            "timedelta",
        ]
    )
    for attr in ["first", "last"]:
        result = getattr(df.groupby("group"), attr)()
        tm.assert_index_equal(result.columns, expected_columns)

        result = getattr(df.groupby("group"), attr)(numeric_only=False)
        tm.assert_index_equal(result.columns, expected_columns)

    expected_columns = Index(["int", "float", "string", "category_int", "timedelta"])

    result = df.groupby("group").sum()
    tm.assert_index_equal(result.columns, expected_columns_numeric)

    result = df.groupby("group").sum(numeric_only=False)
    tm.assert_index_equal(result.columns, expected_columns)

    expected_columns = Index(["int", "float", "category_int"])
    for attr in ["prod", "cumprod"]:
        result = getattr(df.groupby("group"), attr)()
        tm.assert_index_equal(result.columns, expected_columns_numeric)

        result = getattr(df.groupby("group"), attr)(numeric_only=False)
        tm.assert_index_equal(result.columns, expected_columns)

    # like min, max, but don't include strings
    expected_columns = Index(
        ["int", "float", "category_int", "datetime", "datetimetz", "timedelta"]
    )
    for attr in ["cummin", "cummax"]:
        result = getattr(df.groupby("group"), attr)()
        # GH 15561: numeric_only=False set by default like min/max
        tm.assert_index_equal(result.columns, expected_columns)

        result = getattr(df.groupby("group"), attr)(numeric_only=False)
        tm.assert_index_equal(result.columns, expected_columns)

    expected_columns = Index(["int", "float", "category_int", "timedelta"])

    result = getattr(df.groupby("group"), "cumsum")()
    tm.assert_index_equal(result.columns, expected_columns_numeric)

    result = getattr(df.groupby("group"), "cumsum")(numeric_only=False)
    tm.assert_index_equal(result.columns, expected_columns)


def test_non_cython_api():

    # GH5610
    # non-cython calls should not include the grouper

    df = DataFrame(
        [[1, 2, "foo"], [1, np.nan, "bar"], [3, np.nan, "baz"]], columns=["A", "B", "C"]
    )
    g = df.groupby("A")
    gni = df.groupby("A", as_index=False)

    # mad
    expected = DataFrame([[0], [np.nan]], columns=["B"], index=[1, 3])
    expected.index.name = "A"
    result = g.mad()
    tm.assert_frame_equal(result, expected)

    expected = DataFrame([[0.0, 0.0], [0, np.nan]], columns=["A", "B"], index=[0, 1])
    result = gni.mad()
    tm.assert_frame_equal(result, expected)

    # describe
    expected_index = pd.Index([1, 3], name="A")
    expected_col = pd.MultiIndex(
        levels=[["B"], ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]],
        codes=[[0] * 8, list(range(8))],
    )
    expected = pd.DataFrame(
        [
            [1.0, 2.0, np.nan, 2.0, 2.0, 2.0, 2.0, 2.0],
            [0.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
        ],
        index=expected_index,
        columns=expected_col,
    )
    result = g.describe()
    tm.assert_frame_equal(result, expected)

    expected = pd.concat(
        [
            df[df.A == 1].describe().unstack().to_frame().T,
            df[df.A == 3].describe().unstack().to_frame().T,
        ]
    )
    expected.index = pd.Index([0, 1])
    result = gni.describe()
    tm.assert_frame_equal(result, expected)

    # any
    expected = DataFrame(
        [[True, True], [False, True]], columns=["B", "C"], index=[1, 3]
    )
    expected.index.name = "A"
    result = g.any()
    tm.assert_frame_equal(result, expected)

    # idxmax
    expected = DataFrame([[0.0], [np.nan]], columns=["B"], index=[1, 3])
    expected.index.name = "A"
    result = g.idxmax()
    tm.assert_frame_equal(result, expected)


def test_cython_api2():

    # this takes the fast apply path

    # cumsum (GH5614)
    df = DataFrame([[1, 2, np.nan], [1, np.nan, 9], [3, 4, 9]], columns=["A", "B", "C"])
    expected = DataFrame([[2, np.nan], [np.nan, 9], [4, 9]], columns=["B", "C"])
    result = df.groupby("A").cumsum()
    tm.assert_frame_equal(result, expected)

    # GH 5755 - cumsum is a transformer and should ignore as_index
    result = df.groupby("A", as_index=False).cumsum()
    tm.assert_frame_equal(result, expected)

    # GH 13994
    result = df.groupby("A").cumsum(axis=1)
    expected = df.cumsum(axis=1)
    tm.assert_frame_equal(result, expected)
    result = df.groupby("A").cumprod(axis=1)
    expected = df.cumprod(axis=1)
    tm.assert_frame_equal(result, expected)


def test_cython_median():
    df = DataFrame(np.random.randn(1000))
    df.values[::2] = np.nan

    labels = np.random.randint(0, 50, size=1000).astype(float)
    labels[::17] = np.nan

    result = df.groupby(labels).median()
    exp = df.groupby(labels).agg(nanops.nanmedian)
    tm.assert_frame_equal(result, exp)

    df = DataFrame(np.random.randn(1000, 5))
    rs = df.groupby(labels).agg(np.median)
    xp = df.groupby(labels).median()
    tm.assert_frame_equal(rs, xp)


def test_median_empty_bins(observed):
    df = pd.DataFrame(np.random.randint(0, 44, 500))

    grps = range(0, 55, 5)
    bins = pd.cut(df[0], grps)

    result = df.groupby(bins, observed=observed).median()
    expected = df.groupby(bins, observed=observed).agg(lambda x: x.median())
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    "dtype", ["int8", "int16", "int32", "int64", "float32", "float64", "uint64"]
)
@pytest.mark.parametrize(
    "method,data",
    [
        ("first", {"df": [{"a": 1, "b": 1}, {"a": 2, "b": 3}]}),
        ("last", {"df": [{"a": 1, "b": 2}, {"a": 2, "b": 4}]}),
        ("min", {"df": [{"a": 1, "b": 1}, {"a": 2, "b": 3}]}),
        ("max", {"df": [{"a": 1, "b": 2}, {"a": 2, "b": 4}]}),
        ("nth", {"df": [{"a": 1, "b": 2}, {"a": 2, "b": 4}], "args": [1]}),
        ("count", {"df": [{"a": 1, "b": 2}, {"a": 2, "b": 2}], "out_type": "int64"}),
    ],
)
def test_groupby_non_arithmetic_agg_types(dtype, method, data):
    # GH9311, GH6620
    df = pd.DataFrame(
        [{"a": 1, "b": 1}, {"a": 1, "b": 2}, {"a": 2, "b": 3}, {"a": 2, "b": 4}]
    )

    df["b"] = df.b.astype(dtype)

    if "args" not in data:
        data["args"] = []

    if "out_type" in data:
        out_type = data["out_type"]
    else:
        out_type = dtype

    exp = data["df"]
    df_out = pd.DataFrame(exp)

    df_out["b"] = df_out.b.astype(out_type)
    df_out.set_index("a", inplace=True)

    grpd = df.groupby("a")
    t = getattr(grpd, method)(*data["args"])
    tm.assert_frame_equal(t, df_out)


@pytest.mark.parametrize(
    "i",
    [
        (
            Timestamp("2011-01-15 12:50:28.502376"),
            Timestamp("2011-01-20 12:50:28.593448"),
        ),
        (24650000000000001, 24650000000000002),
    ],
)
def test_groupby_non_arithmetic_agg_int_like_precision(i):
    # see gh-6620, gh-9311
    df = pd.DataFrame([{"a": 1, "b": i[0]}, {"a": 1, "b": i[1]}])

    grp_exp = {
        "first": {"expected": i[0]},
        "last": {"expected": i[1]},
        "min": {"expected": i[0]},
        "max": {"expected": i[1]},
        "nth": {"expected": i[1], "args": [1]},
        "count": {"expected": 2},
    }

    for method, data in grp_exp.items():
        if "args" not in data:
            data["args"] = []

        grouped = df.groupby("a")
        res = getattr(grouped, method)(*data["args"])

        assert res.iloc[0].b == data["expected"]


@pytest.mark.parametrize(
    "func, values",
    [
        ("idxmin", {"c_int": [0, 2], "c_float": [1, 3], "c_date": [1, 2]}),
        ("idxmax", {"c_int": [1, 3], "c_float": [0, 2], "c_date": [0, 3]}),
    ],
)
def test_idxmin_idxmax_returns_int_types(func, values):
    # GH 25444
    df = pd.DataFrame(
        {
            "name": ["A", "A", "B", "B"],
            "c_int": [1, 2, 3, 4],
            "c_float": [4.02, 3.03, 2.04, 1.05],
            "c_date": ["2019", "2018", "2016", "2017"],
        }
    )
    df["c_date"] = pd.to_datetime(df["c_date"])

    result = getattr(df.groupby("name"), func)()

    expected = pd.DataFrame(values, index=Index(["A", "B"], name="name"))

    tm.assert_frame_equal(result, expected)


def test_fill_consistency():

    # GH9221
    # pass thru keyword arguments to the generated wrapper
    # are set if the passed kw is None (only)
    df = DataFrame(
        index=pd.MultiIndex.from_product(
            [["value1", "value2"], date_range("2014-01-01", "2014-01-06")]
        ),
        columns=Index(["1", "2"], name="id"),
    )
    df["1"] = [
        np.nan,
        1,
        np.nan,
        np.nan,
        11,
        np.nan,
        np.nan,
        2,
        np.nan,
        np.nan,
        22,
        np.nan,
    ]
    df["2"] = [
        np.nan,
        3,
        np.nan,
        np.nan,
        33,
        np.nan,
        np.nan,
        4,
        np.nan,
        np.nan,
        44,
        np.nan,
    ]

    expected = df.groupby(level=0, axis=0).fillna(method="ffill")
    result = df.T.groupby(level=0, axis=1).fillna(method="ffill").T
    tm.assert_frame_equal(result, expected)


def test_groupby_cumprod():
    # GH 4095
    df = pd.DataFrame({"key": ["b"] * 10, "value": 2})

    actual = df.groupby("key")["value"].cumprod()
    expected = df.groupby("key")["value"].apply(lambda x: x.cumprod())
    expected.name = "value"
    tm.assert_series_equal(actual, expected)

    df = pd.DataFrame({"key": ["b"] * 100, "value": 2})
    actual = df.groupby("key")["value"].cumprod()
    # if overflows, groupby product casts to float
    # while numpy passes back invalid values
    df["value"] = df["value"].astype(float)
    expected = df.groupby("key")["value"].apply(lambda x: x.cumprod())
    expected.name = "value"
    tm.assert_series_equal(actual, expected)


def scipy_sem(*args, **kwargs):
    from scipy.stats import sem

    return sem(*args, ddof=1, **kwargs)


@pytest.mark.parametrize(
    "op,targop",
    [
        ("mean", np.mean),
        ("median", np.median),
        ("std", np.std),
        ("var", np.var),
        ("sum", np.sum),
        ("prod", np.prod),
        ("min", np.min),
        ("max", np.max),
        ("first", lambda x: x.iloc[0]),
        ("last", lambda x: x.iloc[-1]),
        ("count", np.size),
        pytest.param("sem", scipy_sem, marks=td.skip_if_no_scipy),
    ],
)
def test_ops_general(op, targop):
    df = DataFrame(np.random.randn(1000))
    labels = np.random.randint(0, 50, size=1000).astype(float)

    result = getattr(df.groupby(labels), op)().astype(float)
    expected = df.groupby(labels).agg(targop)
    tm.assert_frame_equal(result, expected)


def test_max_nan_bug():
    raw = """,Date,app,File
-04-23,2013-04-23 00:00:00,,log080001.log
-05-06,2013-05-06 00:00:00,,log.log
-05-07,2013-05-07 00:00:00,OE,xlsx"""

    df = pd.read_csv(StringIO(raw), parse_dates=[0])
    gb = df.groupby("Date")
    r = gb[["File"]].max()
    e = gb["File"].max().to_frame()
    tm.assert_frame_equal(r, e)
    assert not r["File"].isna().any()


def test_nlargest():
    a = Series([1, 3, 5, 7, 2, 9, 0, 4, 6, 10])
    b = Series(list("a" * 5 + "b" * 5))
    gb = a.groupby(b)
    r = gb.nlargest(3)
    e = Series(
        [7, 5, 3, 10, 9, 6],
        index=MultiIndex.from_arrays([list("aaabbb"), [3, 2, 1, 9, 5, 8]]),
    )
    tm.assert_series_equal(r, e)

    a = Series([1, 1, 3, 2, 0, 3, 3, 2, 1, 0])
    gb = a.groupby(b)
    e = Series(
        [3, 2, 1, 3, 3, 2],
        index=MultiIndex.from_arrays([list("aaabbb"), [2, 3, 1, 6, 5, 7]]),
    )
    tm.assert_series_equal(gb.nlargest(3, keep="last"), e)


def test_nlargest_mi_grouper():
    # see gh-21411
    npr = np.random.RandomState(123456789)

    dts = date_range("20180101", periods=10)
    iterables = [dts, ["one", "two"]]

    idx = MultiIndex.from_product(iterables, names=["first", "second"])
    s = Series(npr.randn(20), index=idx)

    result = s.groupby("first").nlargest(1)

    exp_idx = MultiIndex.from_tuples(
        [
            (dts[0], dts[0], "one"),
            (dts[1], dts[1], "one"),
            (dts[2], dts[2], "one"),
            (dts[3], dts[3], "two"),
            (dts[4], dts[4], "one"),
            (dts[5], dts[5], "one"),
            (dts[6], dts[6], "one"),
            (dts[7], dts[7], "one"),
            (dts[8], dts[8], "two"),
            (dts[9], dts[9], "one"),
        ],
        names=["first", "first", "second"],
    )

    exp_values = [
        2.2129019979039612,
        1.8417114045748335,
        0.858963679564603,
        1.3759151378258088,
        0.9430284594687134,
        0.5296914208183142,
        0.8318045593815487,
        -0.8476703342910327,
        0.3804446884133735,
        -0.8028845810770998,
    ]

    expected = Series(exp_values, index=exp_idx)
    tm.assert_series_equal(result, expected, check_exact=False)


def test_nsmallest():
    a = Series([1, 3, 5, 7, 2, 9, 0, 4, 6, 10])
    b = Series(list("a" * 5 + "b" * 5))
    gb = a.groupby(b)
    r = gb.nsmallest(3)
    e = Series(
        [1, 2, 3, 0, 4, 6],
        index=MultiIndex.from_arrays([list("aaabbb"), [0, 4, 1, 6, 7, 8]]),
    )
    tm.assert_series_equal(r, e)

    a = Series([1, 1, 3, 2, 0, 3, 3, 2, 1, 0])
    gb = a.groupby(b)
    e = Series(
        [0, 1, 1, 0, 1, 2],
        index=MultiIndex.from_arrays([list("aaabbb"), [4, 1, 0, 9, 8, 7]]),
    )
    tm.assert_series_equal(gb.nsmallest(3, keep="last"), e)


@pytest.mark.parametrize("func", ["cumprod", "cumsum"])
def test_numpy_compat(func):
    # see gh-12811
    df = pd.DataFrame({"A": [1, 2, 1], "B": [1, 2, 3]})
    g = df.groupby("A")

    msg = "numpy operations are not valid with groupby"

    with pytest.raises(UnsupportedFunctionCall, match=msg):
        getattr(g, func)(1, 2, 3)
    with pytest.raises(UnsupportedFunctionCall, match=msg):
        getattr(g, func)(foo=1)


@pytest.mark.xfail(
    _is_numpy_dev,
    reason="https://github.com/pandas-dev/pandas/issues/31992",
    strict=False,
)
def test_cummin(numpy_dtypes_for_minmax):
    dtype = numpy_dtypes_for_minmax[0]
    min_val = numpy_dtypes_for_minmax[1]

    # GH 15048
    base_df = pd.DataFrame(
        {"A": [1, 1, 1, 1, 2, 2, 2, 2], "B": [3, 4, 3, 2, 2, 3, 2, 1]}
    )
    expected_mins = [3, 3, 3, 2, 2, 2, 2, 1]

    df = base_df.astype(dtype)

    expected = pd.DataFrame({"B": expected_mins}).astype(dtype)
    result = df.groupby("A").cummin()
    tm.assert_frame_equal(result, expected)
    result = df.groupby("A").B.apply(lambda x: x.cummin()).to_frame()
    tm.assert_frame_equal(result, expected)

    # Test w/ min value for dtype
    df.loc[[2, 6], "B"] = min_val
    expected.loc[[2, 3, 6, 7], "B"] = min_val
    result = df.groupby("A").cummin()
    tm.assert_frame_equal(result, expected)
    expected = df.groupby("A").B.apply(lambda x: x.cummin()).to_frame()
    tm.assert_frame_equal(result, expected)

    # Test nan in some values
    base_df.loc[[0, 2, 4, 6], "B"] = np.nan
    expected = pd.DataFrame({"B": [np.nan, 4, np.nan, 2, np.nan, 3, np.nan, 1]})
    result = base_df.groupby("A").cummin()
    tm.assert_frame_equal(result, expected)
    expected = base_df.groupby("A").B.apply(lambda x: x.cummin()).to_frame()
    tm.assert_frame_equal(result, expected)

    # GH 15561
    df = pd.DataFrame(dict(a=[1], b=pd.to_datetime(["2001"])))
    expected = pd.Series(pd.to_datetime("2001"), index=[0], name="b")

    result = df.groupby("a")["b"].cummin()
    tm.assert_series_equal(expected, result)

    # GH 15635
    df = pd.DataFrame(dict(a=[1, 2, 1], b=[1, 2, 2]))
    result = df.groupby("a").b.cummin()
    expected = pd.Series([1, 2, 1], name="b")
    tm.assert_series_equal(result, expected)


@pytest.mark.xfail(
    _is_numpy_dev,
    reason="https://github.com/pandas-dev/pandas/issues/31992",
    strict=False,
)
def test_cummin_all_nan_column():
    base_df = pd.DataFrame({"A": [1, 1, 1, 1, 2, 2, 2, 2], "B": [np.nan] * 8})

    expected = pd.DataFrame({"B": [np.nan] * 8})
    result = base_df.groupby("A").cummin()
    tm.assert_frame_equal(expected, result)
    result = base_df.groupby("A").B.apply(lambda x: x.cummin()).to_frame()
    tm.assert_frame_equal(expected, result)


@pytest.mark.xfail(
    _is_numpy_dev,
    reason="https://github.com/pandas-dev/pandas/issues/31992",
    strict=False,
)
def test_cummax(numpy_dtypes_for_minmax):
    dtype = numpy_dtypes_for_minmax[0]
    max_val = numpy_dtypes_for_minmax[2]

    # GH 15048
    base_df = pd.DataFrame(
        {"A": [1, 1, 1, 1, 2, 2, 2, 2], "B": [3, 4, 3, 2, 2, 3, 2, 1]}
    )
    expected_maxs = [3, 4, 4, 4, 2, 3, 3, 3]

    df = base_df.astype(dtype)

    expected = pd.DataFrame({"B": expected_maxs}).astype(dtype)
    result = df.groupby("A").cummax()
    tm.assert_frame_equal(result, expected)
    result = df.groupby("A").B.apply(lambda x: x.cummax()).to_frame()
    tm.assert_frame_equal(result, expected)

    # Test w/ max value for dtype
    df.loc[[2, 6], "B"] = max_val
    expected.loc[[2, 3, 6, 7], "B"] = max_val
    result = df.groupby("A").cummax()
    tm.assert_frame_equal(result, expected)
    expected = df.groupby("A").B.apply(lambda x: x.cummax()).to_frame()
    tm.assert_frame_equal(result, expected)

    # Test nan in some values
    base_df.loc[[0, 2, 4, 6], "B"] = np.nan
    expected = pd.DataFrame({"B": [np.nan, 4, np.nan, 4, np.nan, 3, np.nan, 3]})
    result = base_df.groupby("A").cummax()
    tm.assert_frame_equal(result, expected)
    expected = base_df.groupby("A").B.apply(lambda x: x.cummax()).to_frame()
    tm.assert_frame_equal(result, expected)

    # GH 15561
    df = pd.DataFrame(dict(a=[1], b=pd.to_datetime(["2001"])))
    expected = pd.Series(pd.to_datetime("2001"), index=[0], name="b")

    result = df.groupby("a")["b"].cummax()
    tm.assert_series_equal(expected, result)

    # GH 15635
    df = pd.DataFrame(dict(a=[1, 2, 1], b=[2, 1, 1]))
    result = df.groupby("a").b.cummax()
    expected = pd.Series([2, 1, 2], name="b")
    tm.assert_series_equal(result, expected)


@pytest.mark.xfail(
    _is_numpy_dev,
    reason="https://github.com/pandas-dev/pandas/issues/31992",
    strict=False,
)
def test_cummax_all_nan_column():
    base_df = pd.DataFrame({"A": [1, 1, 1, 1, 2, 2, 2, 2], "B": [np.nan] * 8})

    expected = pd.DataFrame({"B": [np.nan] * 8})
    result = base_df.groupby("A").cummax()
    tm.assert_frame_equal(expected, result)
    result = base_df.groupby("A").B.apply(lambda x: x.cummax()).to_frame()
    tm.assert_frame_equal(expected, result)


@pytest.mark.parametrize(
    "in_vals, out_vals",
    [
        # Basics: strictly increasing (T), strictly decreasing (F),
        # abs val increasing (F), non-strictly increasing (T)
        ([1, 2, 5, 3, 2, 0, 4, 5, -6, 1, 1], [True, False, False, True]),
        # Test with inf vals
        (
            [1, 2.1, np.inf, 3, 2, np.inf, -np.inf, 5, 11, 1, -np.inf],
            [True, False, True, False],
        ),
        # Test with nan vals; should always be False
        (
            [1, 2, np.nan, 3, 2, np.nan, np.nan, 5, -np.inf, 1, np.nan],
            [False, False, False, False],
        ),
    ],
)
def test_is_monotonic_increasing(in_vals, out_vals):
    # GH 17015
    source_dict = {
        "A": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
        "B": ["a", "a", "a", "b", "b", "b", "c", "c", "c", "d", "d"],
        "C": in_vals,
    }
    df = pd.DataFrame(source_dict)
    result = df.groupby("B").C.is_monotonic_increasing
    index = Index(list("abcd"), name="B")
    expected = pd.Series(index=index, data=out_vals, name="C")
    tm.assert_series_equal(result, expected)

    # Also check result equal to manually taking x.is_monotonic_increasing.
    expected = df.groupby(["B"]).C.apply(lambda x: x.is_monotonic_increasing)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "in_vals, out_vals",
    [
        # Basics: strictly decreasing (T), strictly increasing (F),
        # abs val decreasing (F), non-strictly increasing (T)
        ([10, 9, 7, 3, 4, 5, -3, 2, 0, 1, 1], [True, False, False, True]),
        # Test with inf vals
        (
            [np.inf, 1, -np.inf, np.inf, 2, -3, -np.inf, 5, -3, -np.inf, -np.inf],
            [True, True, False, True],
        ),
        # Test with nan vals; should always be False
        (
            [1, 2, np.nan, 3, 2, np.nan, np.nan, 5, -np.inf, 1, np.nan],
            [False, False, False, False],
        ),
    ],
)
def test_is_monotonic_decreasing(in_vals, out_vals):
    # GH 17015
    source_dict = {
        "A": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
        "B": ["a", "a", "a", "b", "b", "b", "c", "c", "c", "d", "d"],
        "C": in_vals,
    }

    df = pd.DataFrame(source_dict)
    result = df.groupby("B").C.is_monotonic_decreasing
    index = Index(list("abcd"), name="B")
    expected = pd.Series(index=index, data=out_vals, name="C")
    tm.assert_series_equal(result, expected)


# describe
# --------------------------------


def test_apply_describe_bug(mframe):
    grouped = mframe.groupby(level="first")
    grouped.describe()  # it works!


def test_series_describe_multikey():
    ts = tm.makeTimeSeries()
    grouped = ts.groupby([lambda x: x.year, lambda x: x.month])
    result = grouped.describe()
    tm.assert_series_equal(result["mean"], grouped.mean(), check_names=False)
    tm.assert_series_equal(result["std"], grouped.std(), check_names=False)
    tm.assert_series_equal(result["min"], grouped.min(), check_names=False)


def test_series_describe_single():
    ts = tm.makeTimeSeries()
    grouped = ts.groupby(lambda x: x.month)
    result = grouped.apply(lambda x: x.describe())
    expected = grouped.describe().stack()
    tm.assert_series_equal(result, expected)


def test_series_index_name(df):
    grouped = df.loc[:, ["C"]].groupby(df["A"])
    result = grouped.agg(lambda x: x.mean())
    assert result.index.name == "A"


def test_frame_describe_multikey(tsframe):
    grouped = tsframe.groupby([lambda x: x.year, lambda x: x.month])
    result = grouped.describe()
    desc_groups = []
    for col in tsframe:
        group = grouped[col].describe()
        # GH 17464 - Remove duplicate MultiIndex levels
        group_col = pd.MultiIndex(
            levels=[[col], group.columns],
            codes=[[0] * len(group.columns), range(len(group.columns))],
        )
        group = pd.DataFrame(group.values, columns=group_col, index=group.index)
        desc_groups.append(group)
    expected = pd.concat(desc_groups, axis=1)
    tm.assert_frame_equal(result, expected)

    groupedT = tsframe.groupby({"A": 0, "B": 0, "C": 1, "D": 1}, axis=1)
    result = groupedT.describe()
    expected = tsframe.describe().T
    expected.index = pd.MultiIndex(
        levels=[[0, 1], expected.index],
        codes=[[0, 0, 1, 1], range(len(expected.index))],
    )
    tm.assert_frame_equal(result, expected)


def test_frame_describe_tupleindex():

    # GH 14848 - regression from 0.19.0 to 0.19.1
    df1 = DataFrame(
        {
            "x": [1, 2, 3, 4, 5] * 3,
            "y": [10, 20, 30, 40, 50] * 3,
            "z": [100, 200, 300, 400, 500] * 3,
        }
    )
    df1["k"] = [(0, 0, 1), (0, 1, 0), (1, 0, 0)] * 5
    df2 = df1.rename(columns={"k": "key"})
    msg = "Names should be list-like for a MultiIndex"
    with pytest.raises(ValueError, match=msg):
        df1.groupby("k").describe()
    with pytest.raises(ValueError, match=msg):
        df2.groupby("key").describe()


def test_frame_describe_unstacked_format():
    # GH 4792
    prices = {
        pd.Timestamp("2011-01-06 10:59:05", tz=None): 24990,
        pd.Timestamp("2011-01-06 12:43:33", tz=None): 25499,
        pd.Timestamp("2011-01-06 12:54:09", tz=None): 25499,
    }
    volumes = {
        pd.Timestamp("2011-01-06 10:59:05", tz=None): 1500000000,
        pd.Timestamp("2011-01-06 12:43:33", tz=None): 5000000000,
        pd.Timestamp("2011-01-06 12:54:09", tz=None): 100000000,
    }
    df = pd.DataFrame({"PRICE": prices, "VOLUME": volumes})
    result = df.groupby("PRICE").VOLUME.describe()
    data = [
        df[df.PRICE == 24990].VOLUME.describe().values.tolist(),
        df[df.PRICE == 25499].VOLUME.describe().values.tolist(),
    ]
    expected = pd.DataFrame(
        data,
        index=pd.Index([24990, 25499], name="PRICE"),
        columns=["count", "mean", "std", "min", "25%", "50%", "75%", "max"],
    )
    tm.assert_frame_equal(result, expected)


# nunique
# --------------------------------


@pytest.mark.parametrize("n", 10 ** np.arange(2, 6))
@pytest.mark.parametrize("m", [10, 100, 1000])
@pytest.mark.parametrize("sort", [False, True])
@pytest.mark.parametrize("dropna", [False, True])
def test_series_groupby_nunique(n, m, sort, dropna):
    def check_nunique(df, keys, as_index=True):
        original_df = df.copy()
        gr = df.groupby(keys, as_index=as_index, sort=sort)
        left = gr["julie"].nunique(dropna=dropna)

        gr = df.groupby(keys, as_index=as_index, sort=sort)
        right = gr["julie"].apply(Series.nunique, dropna=dropna)
        if not as_index:
            right = right.reset_index(drop=True)

        tm.assert_series_equal(left, right, check_names=False)
        tm.assert_frame_equal(df, original_df)

    days = date_range("2015-08-23", periods=10)

    frame = DataFrame(
        {
            "jim": np.random.choice(list(ascii_lowercase), n),
            "joe": np.random.choice(days, n),
            "julie": np.random.randint(0, m, n),
        }
    )

    check_nunique(frame, ["jim"])
    check_nunique(frame, ["jim", "joe"])

    frame.loc[1::17, "jim"] = None
    frame.loc[3::37, "joe"] = None
    frame.loc[7::19, "julie"] = None
    frame.loc[8::19, "julie"] = None
    frame.loc[9::19, "julie"] = None

    check_nunique(frame, ["jim"])
    check_nunique(frame, ["jim", "joe"])
    check_nunique(frame, ["jim"], as_index=False)
    check_nunique(frame, ["jim", "joe"], as_index=False)


def test_nunique():
    df = DataFrame({"A": list("abbacc"), "B": list("abxacc"), "C": list("abbacx")})

    expected = DataFrame({"A": [1] * 3, "B": [1, 2, 1], "C": [1, 1, 2]})
    result = df.groupby("A", as_index=False).nunique()
    tm.assert_frame_equal(result, expected)

    # as_index
    expected.index = list("abc")
    expected.index.name = "A"
    result = df.groupby("A").nunique()
    tm.assert_frame_equal(result, expected)

    # with na
    result = df.replace({"x": None}).groupby("A").nunique(dropna=False)
    tm.assert_frame_equal(result, expected)

    # dropna
    expected = DataFrame({"A": [1] * 3, "B": [1] * 3, "C": [1] * 3}, index=list("abc"))
    expected.index.name = "A"
    result = df.replace({"x": None}).groupby("A").nunique()
    tm.assert_frame_equal(result, expected)


def test_nunique_with_object():
    # GH 11077
    data = pd.DataFrame(
        [
            [100, 1, "Alice"],
            [200, 2, "Bob"],
            [300, 3, "Charlie"],
            [-400, 4, "Dan"],
            [500, 5, "Edith"],
        ],
        columns=["amount", "id", "name"],
    )

    result = data.groupby(["id", "amount"])["name"].nunique()
    index = MultiIndex.from_arrays([data.id, data.amount])
    expected = pd.Series([1] * 5, name="name", index=index)
    tm.assert_series_equal(result, expected)


def test_nunique_with_empty_series():
    # GH 12553
    data = pd.Series(name="name", dtype=object)
    result = data.groupby(level=0).nunique()
    expected = pd.Series(name="name", dtype="int64")
    tm.assert_series_equal(result, expected)


def test_nunique_with_timegrouper():
    # GH 13453
    test = pd.DataFrame(
        {
            "time": [
                Timestamp("2016-06-28 09:35:35"),
                Timestamp("2016-06-28 16:09:30"),
                Timestamp("2016-06-28 16:46:28"),
            ],
            "data": ["1", "2", "3"],
        }
    ).set_index("time")
    result = test.groupby(pd.Grouper(freq="h"))["data"].nunique()
    expected = test.groupby(pd.Grouper(freq="h"))["data"].apply(pd.Series.nunique)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "key, data, dropna, expected",
    [
        (
            ["x", "x", "x"],
            [Timestamp("2019-01-01"), NaT, Timestamp("2019-01-01")],
            True,
            Series([1], index=pd.Index(["x"], name="key"), name="data"),
        ),
        (
            ["x", "x", "x"],
            [dt.date(2019, 1, 1), NaT, dt.date(2019, 1, 1)],
            True,
            Series([1], index=pd.Index(["x"], name="key"), name="data"),
        ),
        (
            ["x", "x", "x", "y", "y"],
            [dt.date(2019, 1, 1), NaT, dt.date(2019, 1, 1), NaT, dt.date(2019, 1, 1)],
            False,
            Series([2, 2], index=pd.Index(["x", "y"], name="key"), name="data"),
        ),
        (
            ["x", "x", "x", "x", "y"],
            [dt.date(2019, 1, 1), NaT, dt.date(2019, 1, 1), NaT, dt.date(2019, 1, 1)],
            False,
            Series([2, 1], index=pd.Index(["x", "y"], name="key"), name="data"),
        ),
    ],
)
def test_nunique_with_NaT(key, data, dropna, expected):
    # GH 27951
    df = pd.DataFrame({"key": key, "data": data})
    result = df.groupby(["key"])["data"].nunique(dropna=dropna)
    tm.assert_series_equal(result, expected)


def test_nunique_preserves_column_level_names():
    # GH 23222
    test = pd.DataFrame([1, 2, 2], columns=pd.Index(["A"], name="level_0"))
    result = test.groupby([0, 0, 0]).nunique()
    expected = pd.DataFrame([2], columns=test.columns)
    tm.assert_frame_equal(result, expected)


# count
# --------------------------------


def test_groupby_timedelta_cython_count():
    df = DataFrame(
        {"g": list("ab" * 2), "delt": np.arange(4).astype("timedelta64[ns]")}
    )
    expected = Series([2, 2], index=pd.Index(["a", "b"], name="g"), name="delt")
    result = df.groupby("g").delt.count()
    tm.assert_series_equal(expected, result)


def test_count():
    n = 1 << 15
    dr = date_range("2015-08-30", periods=n // 10, freq="T")

    df = DataFrame(
        {
            "1st": np.random.choice(list(ascii_lowercase), n),
            "2nd": np.random.randint(0, 5, n),
            "3rd": np.random.randn(n).round(3),
            "4th": np.random.randint(-10, 10, n),
            "5th": np.random.choice(dr, n),
            "6th": np.random.randn(n).round(3),
            "7th": np.random.randn(n).round(3),
            "8th": np.random.choice(dr, n) - np.random.choice(dr, 1),
            "9th": np.random.choice(list(ascii_lowercase), n),
        }
    )

    for col in df.columns.drop(["1st", "2nd", "4th"]):
        df.loc[np.random.choice(n, n // 10), col] = np.nan

    df["9th"] = df["9th"].astype("category")

    for key in ["1st", "2nd", ["1st", "2nd"]]:
        left = df.groupby(key).count()
        right = df.groupby(key).apply(DataFrame.count).drop(key, axis=1)
        tm.assert_frame_equal(left, right)


def test_count_non_nulls():
    # GH#5610
    # count counts non-nulls
    df = pd.DataFrame(
        [[1, 2, "foo"], [1, np.nan, "bar"], [3, np.nan, np.nan]],
        columns=["A", "B", "C"],
    )

    count_as = df.groupby("A").count()
    count_not_as = df.groupby("A", as_index=False).count()

    expected = DataFrame([[1, 2], [0, 0]], columns=["B", "C"], index=[1, 3])
    expected.index.name = "A"
    tm.assert_frame_equal(count_not_as, expected.reset_index())
    tm.assert_frame_equal(count_as, expected)

    count_B = df.groupby("A")["B"].count()
    tm.assert_series_equal(count_B, expected["B"])


def test_count_object():
    df = pd.DataFrame({"a": ["a"] * 3 + ["b"] * 3, "c": [2] * 3 + [3] * 3})
    result = df.groupby("c").a.count()
    expected = pd.Series([3, 3], index=pd.Index([2, 3], name="c"), name="a")
    tm.assert_series_equal(result, expected)

    df = pd.DataFrame({"a": ["a", np.nan, np.nan] + ["b"] * 3, "c": [2] * 3 + [3] * 3})
    result = df.groupby("c").a.count()
    expected = pd.Series([1, 3], index=pd.Index([2, 3], name="c"), name="a")
    tm.assert_series_equal(result, expected)


def test_count_cross_type():
    # GH8169
    vals = np.hstack(
        (np.random.randint(0, 5, (100, 2)), np.random.randint(0, 2, (100, 2)))
    )

    df = pd.DataFrame(vals, columns=["a", "b", "c", "d"])
    df[df == 2] = np.nan
    expected = df.groupby(["c", "d"]).count()

    for t in ["float32", "object"]:
        df["a"] = df["a"].astype(t)
        df["b"] = df["b"].astype(t)
        result = df.groupby(["c", "d"]).count()
        tm.assert_frame_equal(result, expected)


def test_lower_int_prec_count():
    df = DataFrame(
        {
            "a": np.array([0, 1, 2, 100], np.int8),
            "b": np.array([1, 2, 3, 6], np.uint32),
            "c": np.array([4, 5, 6, 8], np.int16),
            "grp": list("ab" * 2),
        }
    )
    result = df.groupby("grp").count()
    expected = DataFrame(
        {"a": [2, 2], "b": [2, 2], "c": [2, 2]}, index=pd.Index(list("ab"), name="grp")
    )
    tm.assert_frame_equal(result, expected)


def test_count_uses_size_on_exception():
    class RaisingObjectException(Exception):
        pass

    class RaisingObject:
        def __init__(self, msg="I will raise inside Cython"):
            super().__init__()
            self.msg = msg

        def __eq__(self, other):
            # gets called in Cython to check that raising calls the method
            raise RaisingObjectException(self.msg)

    df = DataFrame({"a": [RaisingObject() for _ in range(4)], "grp": list("ab" * 2)})
    result = df.groupby("grp").count()
    expected = DataFrame({"a": [2, 2]}, index=pd.Index(list("ab"), name="grp"))
    tm.assert_frame_equal(result, expected)


# size
# --------------------------------


@pytest.mark.parametrize("by", ["A", "B", ["A", "B"]])
def test_size(df, by):
    grouped = df.groupby(by=by)
    result = grouped.size()
    for key, group in grouped:
        assert result[key] == len(group)


@pytest.mark.parametrize("by", ["A", "B", ["A", "B"]])
@pytest.mark.parametrize("sort", [True, False])
def test_size_sort(df, sort, by):
    df = DataFrame(np.random.choice(20, (1000, 3)), columns=list("ABC"))
    left = df.groupby(by=by, sort=sort).size()
    right = df.groupby(by=by, sort=sort)["C"].apply(lambda a: a.shape[0])
    tm.assert_series_equal(left, right, check_names=False)


def test_size_series_dataframe():
    # https://github.com/pandas-dev/pandas/issues/11699
    df = DataFrame(columns=["A", "B"])
    out = Series(dtype="int64", index=Index([], name="A"))
    tm.assert_series_equal(df.groupby("A").size(), out)


def test_size_groupby_all_null():
    # https://github.com/pandas-dev/pandas/issues/23050
    # Assert no 'Value Error : Length of passed values is 2, index implies 0'
    df = DataFrame({"A": [None, None]})  # all-null groups
    result = df.groupby("A").size()
    expected = Series(dtype="int64", index=Index([], name="A"))
    tm.assert_series_equal(result, expected)


# quantile
# --------------------------------


@pytest.mark.parametrize(
    "interpolation", ["linear", "lower", "higher", "nearest", "midpoint"]
)
@pytest.mark.parametrize(
    "a_vals,b_vals",
    [
        # Ints
        ([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]),
        ([1, 2, 3, 4], [4, 3, 2, 1]),
        ([1, 2, 3, 4, 5], [4, 3, 2, 1]),
        # Floats
        ([1.0, 2.0, 3.0, 4.0, 5.0], [5.0, 4.0, 3.0, 2.0, 1.0]),
        # Missing data
        ([1.0, np.nan, 3.0, np.nan, 5.0], [5.0, np.nan, 3.0, np.nan, 1.0]),
        ([np.nan, 4.0, np.nan, 2.0, np.nan], [np.nan, 4.0, np.nan, 2.0, np.nan]),
        # Timestamps
        (
            list(pd.date_range("1/1/18", freq="D", periods=5)),
            list(pd.date_range("1/1/18", freq="D", periods=5))[::-1],
        ),
        # All NA
        ([np.nan] * 5, [np.nan] * 5),
    ],
)
@pytest.mark.parametrize("q", [0, 0.25, 0.5, 0.75, 1])
def test_quantile(interpolation, a_vals, b_vals, q):
    if interpolation == "nearest" and q == 0.5 and b_vals == [4, 3, 2, 1]:
        pytest.skip(
            "Unclear numpy expectation for nearest result with equidistant data"
        )

    a_expected = pd.Series(a_vals).quantile(q, interpolation=interpolation)
    b_expected = pd.Series(b_vals).quantile(q, interpolation=interpolation)

    df = DataFrame(
        {"key": ["a"] * len(a_vals) + ["b"] * len(b_vals), "val": a_vals + b_vals}
    )

    expected = DataFrame(
        [a_expected, b_expected], columns=["val"], index=Index(["a", "b"], name="key")
    )
    result = df.groupby("key").quantile(q, interpolation=interpolation)

    tm.assert_frame_equal(result, expected)


def test_quantile_array():
    # https://github.com/pandas-dev/pandas/issues/27526
    df = pd.DataFrame({"A": [0, 1, 2, 3, 4]})
    result = df.groupby([0, 0, 1, 1, 1]).quantile([0.25])

    index = pd.MultiIndex.from_product([[0, 1], [0.25]])
    expected = pd.DataFrame({"A": [0.25, 2.50]}, index=index)
    tm.assert_frame_equal(result, expected)

    df = pd.DataFrame({"A": [0, 1, 2, 3], "B": [4, 5, 6, 7]})
    index = pd.MultiIndex.from_product([[0, 1], [0.25, 0.75]])

    result = df.groupby([0, 0, 1, 1]).quantile([0.25, 0.75])
    expected = pd.DataFrame(
        {"A": [0.25, 0.75, 2.25, 2.75], "B": [4.25, 4.75, 6.25, 6.75]}, index=index
    )
    tm.assert_frame_equal(result, expected)


def test_quantile_array2():
    # https://github.com/pandas-dev/pandas/pull/28085#issuecomment-524066959
    df = pd.DataFrame(
        np.random.RandomState(0).randint(0, 5, size=(10, 3)), columns=list("ABC")
    )
    result = df.groupby("A").quantile([0.3, 0.7])
    expected = pd.DataFrame(
        {
            "B": [0.9, 2.1, 2.2, 3.4, 1.6, 2.4, 2.3, 2.7, 0.0, 0.0],
            "C": [1.2, 2.8, 1.8, 3.0, 0.0, 0.0, 1.9, 3.1, 3.0, 3.0],
        },
        index=pd.MultiIndex.from_product(
            [[0, 1, 2, 3, 4], [0.3, 0.7]], names=["A", None]
        ),
    )
    tm.assert_frame_equal(result, expected)


def test_quantile_array_no_sort():
    df = pd.DataFrame({"A": [0, 1, 2], "B": [3, 4, 5]})
    result = df.groupby([1, 0, 1], sort=False).quantile([0.25, 0.5, 0.75])
    expected = pd.DataFrame(
        {"A": [0.5, 1.0, 1.5, 1.0, 1.0, 1.0], "B": [3.5, 4.0, 4.5, 4.0, 4.0, 4.0]},
        index=pd.MultiIndex.from_product([[1, 0], [0.25, 0.5, 0.75]]),
    )
    tm.assert_frame_equal(result, expected)

    result = df.groupby([1, 0, 1], sort=False).quantile([0.75, 0.25])
    expected = pd.DataFrame(
        {"A": [1.5, 0.5, 1.0, 1.0], "B": [4.5, 3.5, 4.0, 4.0]},
        index=pd.MultiIndex.from_product([[1, 0], [0.75, 0.25]]),
    )
    tm.assert_frame_equal(result, expected)


def test_quantile_array_multiple_levels():
    df = pd.DataFrame(
        {"A": [0, 1, 2], "B": [3, 4, 5], "c": ["a", "a", "a"], "d": ["a", "a", "b"]}
    )
    result = df.groupby(["c", "d"]).quantile([0.25, 0.75])
    index = pd.MultiIndex.from_tuples(
        [("a", "a", 0.25), ("a", "a", 0.75), ("a", "b", 0.25), ("a", "b", 0.75)],
        names=["c", "d", None],
    )
    expected = pd.DataFrame(
        {"A": [0.25, 0.75, 2.0, 2.0], "B": [3.25, 3.75, 5.0, 5.0]}, index=index
    )
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize("frame_size", [(2, 3), (100, 10)])
@pytest.mark.parametrize("groupby", [[0], [0, 1]])
@pytest.mark.parametrize("q", [[0.5, 0.6]])
def test_groupby_quantile_with_arraylike_q_and_int_columns(frame_size, groupby, q):
    # GH30289
    nrow, ncol = frame_size
    df = pd.DataFrame(
        np.array([ncol * [_ % 4] for _ in range(nrow)]), columns=range(ncol)
    )

    idx_levels = [list(range(min(nrow, 4)))] * len(groupby) + [q]
    idx_codes = [[x for x in range(min(nrow, 4)) for _ in q]] * len(groupby) + [
        list(range(len(q))) * min(nrow, 4)
    ]
    expected_index = pd.MultiIndex(
        levels=idx_levels, codes=idx_codes, names=groupby + [None]
    )
    expected_values = [
        [float(x)] * (ncol - len(groupby)) for x in range(min(nrow, 4)) for _ in q
    ]
    expected_columns = [x for x in range(ncol) if x not in groupby]
    expected = pd.DataFrame(
        expected_values, index=expected_index, columns=expected_columns
    )
    result = df.groupby(groupby).quantile(q)

    tm.assert_frame_equal(result, expected)


def test_quantile_raises():
    df = pd.DataFrame(
        [["foo", "a"], ["foo", "b"], ["foo", "c"]], columns=["key", "val"]
    )

    with pytest.raises(TypeError, match="cannot be performed against 'object' dtypes"):
        df.groupby("key").quantile()


def test_quantile_out_of_bounds_q_raises():
    # https://github.com/pandas-dev/pandas/issues/27470
    df = pd.DataFrame(dict(a=[0, 0, 0, 1, 1, 1], b=range(6)))
    g = df.groupby([0, 0, 0, 1, 1, 1])
    with pytest.raises(ValueError, match="Got '50.0' instead"):
        g.quantile(50)

    with pytest.raises(ValueError, match="Got '-1.0' instead"):
        g.quantile(-1)


def test_quantile_missing_group_values_no_segfaults():
    # GH 28662
    data = np.array([1.0, np.nan, 1.0])
    df = pd.DataFrame(dict(key=data, val=range(3)))

    # Random segfaults; would have been guaranteed in loop
    grp = df.groupby("key")
    for _ in range(100):
        grp.quantile()


def test_quantile_missing_group_values_correct_results():
    # GH 28662
    data = np.array([1.0, np.nan, 3.0, np.nan])
    df = pd.DataFrame(dict(key=data, val=range(4)))

    result = df.groupby("key").quantile()
    expected = pd.DataFrame(
        [1.0, 3.0], index=pd.Index([1.0, 3.0], name="key"), columns=["val"]
    )
    tm.assert_frame_equal(result, expected)


# pipe
# --------------------------------


def test_pipe():
    # Test the pipe method of DataFrameGroupBy.
    # Issue #17871

    random_state = np.random.RandomState(1234567890)

    df = DataFrame(
        {
            "A": ["foo", "bar", "foo", "bar", "foo", "bar", "foo", "foo"],
            "B": random_state.randn(8),
            "C": random_state.randn(8),
        }
    )

    def f(dfgb):
        return dfgb.B.max() - dfgb.C.min().min()

    def square(srs):
        return srs ** 2

    # Note that the transformations are
    # GroupBy -> Series
    # Series -> Series
    # This then chains the GroupBy.pipe and the
    # NDFrame.pipe methods
    result = df.groupby("A").pipe(f).pipe(square)

    index = Index(["bar", "foo"], dtype="object", name="A")
    expected = pd.Series([8.99110003361, 8.17516964785], name="B", index=index)

    tm.assert_series_equal(expected, result)


def test_pipe_args():
    # Test passing args to the pipe method of DataFrameGroupBy.
    # Issue #17871

    df = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C"],
            "x": [1.0, 2.0, 3.0, 2.0, 5.0],
            "y": [10.0, 100.0, 1000.0, -100.0, -1000.0],
        }
    )

    def f(dfgb, arg1):
        return dfgb.filter(lambda grp: grp.y.mean() > arg1, dropna=False).groupby(
            dfgb.grouper
        )

    def g(dfgb, arg2):
        return dfgb.sum() / dfgb.sum().sum() + arg2

    def h(df, arg3):
        return df.x + df.y - arg3

    result = df.groupby("group").pipe(f, 0).pipe(g, 10).pipe(h, 100)

    # Assert the results here
    index = pd.Index(["A", "B", "C"], name="group")
    expected = pd.Series([-79.5160891089, -78.4839108911, -80], index=index)

    tm.assert_series_equal(expected, result)

    # test SeriesGroupby.pipe
    ser = pd.Series([1, 1, 2, 2, 3, 3])
    result = ser.groupby(ser).pipe(lambda grp: grp.sum() * grp.count())

    expected = pd.Series([4, 8, 12], index=pd.Int64Index([1, 2, 3]))

    tm.assert_series_equal(result, expected)


def test_groupby_mean_no_overflow():
    # Regression test for (#22487)
    df = pd.DataFrame(
        {
            "user": ["A", "A", "A", "A", "A"],
            "connections": [4970, 4749, 4719, 4704, 18446744073699999744],
        }
    )
    assert df.groupby("user")["connections"].mean()["A"] == 3689348814740003840


@pytest.mark.parametrize(
    "values",
    [
        {
            "a": [1, 1, 1, 2, 2, 2, 3, 3, 3],
            "b": [1, pd.NA, 2, 1, pd.NA, 2, 1, pd.NA, 2],
        },
        {"a": [1, 1, 2, 2, 3, 3], "b": [1, 2, 1, 2, 1, 2]},
    ],
)
@pytest.mark.parametrize("function", ["mean", "median", "var"])
def test_apply_to_nullable_integer_returns_float(values, function):
    # https://github.com/pandas-dev/pandas/issues/32219
    output = 0.5 if function == "var" else 1.5
    arr = np.array([output] * 3, dtype=float)
    idx = pd.Index([1, 2, 3], dtype=object, name="a")
    expected = pd.DataFrame({"b": arr}, index=idx)

    groups = pd.DataFrame(values, dtype="Int64").groupby("a")

    result = getattr(groups, function)()
    tm.assert_frame_equal(result, expected)

    result = groups.agg(function)
    tm.assert_frame_equal(result, expected)

    result = groups.agg([function])
    expected.columns = MultiIndex.from_tuples([("b", function)])
    tm.assert_frame_equal(result, expected)

@pytest.mark.parametrize(
    "values",
    [
        {
            "a": [1, 1, 1, 2, 2, 2, 3, 3, 3],
            "b": [1, pd.NA, 2, 1, pd.NA, 2, 1, pd.NA, 2],
        },
        {"a": [1, 1, 2, 2, 3, 3], "b": [1, 2, 1, 2, 1, 2]},
    ],
)
@pytest.mark.parametrize("function", ["mean", "median", "var"])
def test_apply_to_nullable_integer_returns_float_noassert(values, function):
    # https://github.com/pandas-dev/pandas/issues/32219
    output = 0.5 if function == "var" else 1.5
    arr = np.array([output] * 3, dtype=float)
    idx = pd.Index([1, 2, 3], dtype=object, name="a")
    expected = pd.DataFrame({"b": arr}, index=idx)

    groups = pd.DataFrame(values, dtype="Int64").groupby("a")

    result = getattr(groups, function)()
    #tm.assert_frame_equal(result, expected)

    result = groups.agg(function)
    #tm.assert_frame_equal(result, expected)

    result = groups.agg([function])
    expected.columns = MultiIndex.from_tuples([("b", function)])
    #tm.assert_frame_equal(result, expected)
