import datetime as dt

import ishikawa as k
import pytest


def test_parse_date_forms():
    assert k.parse_date("R4.3.3") == dt.date(2022, 3, 3)
    assert k.parse_date("R1.5.1") == dt.date(2019, 5, 1)
    assert k.parse_date("2019/1/8") == dt.date(2019, 1, 8)
    assert k.parse_date("2025.1.9") == dt.date(2025, 1, 9)
    assert k.parse_date("43575") == dt.date(2019, 4, 20)  # Excel serial day number
    assert k.parse_date("") is None
    with pytest.raises(ValueError):
        k.parse_date("令和4年3月3日")
    with pytest.raises(ValueError):
        k.parse_date("12345")  # not a plausible serial


def csv_of(rows, header):
    return ("﻿" + ",".join(header) + "\n" + "\n".join(rows) + "\n").encode()


H = ["WKT", "緯度", "経度", "出没日", "時間", "市町名", "場所", "備考", "頭数", "月", "番号"]
ROW = "POINT (136.3651 36.2919),36.2919,136.3651,2025.1.9,10時30分頃,加賀市,山代,備考,1頭,1月,"


def test_parse_csv_ok_and_refusals():
    assert len(k.parse_csv(csv_of([ROW], H), H)) == 1
    for bad in (
        ROW.replace("36.2919,136.3651,2025", "36.3,136.3651,2025"),  # WKT and latitude differ
        ROW.replace("136.3651 36.2919", "36.2919 136.3651").replace(
            "36.2919,136.3651,2025", "136.3651,36.2919,2025"
        ),
        ROW.replace("2025.1.9", "9 Jan"),
        "POINT 1 2,36.2919,136.3651,2025.1.9,x,y,z,w,1頭,1月,",
    ):
        with pytest.raises(ValueError):
            k.parse_csv(csv_of([bad], H), H)
    with pytest.raises(ValueError):
        k.parse_csv(csv_of([ROW], H), H[:-1])


def test_point_of():
    assert k.point_of("POINT (136.5 36.25)") == (136.5, 36.25)


def test_tables_have_the_common_columns_first():
    assert len(k.TABLES) == 5 and k.COMMON[0] == "WKT"
