import pytest
from xvideos_dl.xvideos_dl import (
    download,
    get_video_full_name,
    get_video_url,
    parse_cookies,
    parse_video_id,
    parse_video_name,
    read_cookie,
    save_cookie,
)

COOKIE = (
    "html5_pref=%7B%22SQ%22%3Afalse%2C%22MUTE%22%3Afalse%2C%22VOLUME%22%3A1%2C%22FORCENOPICTURE%22%3Afalse%2C%22FORCEN"
    "OAUTOBUFFER%22%3Afalse%2C%22FORCENATIVEHLS%22%3Afalse%2C%22PLAUTOPLAY%22%3Atrue%2C%22CHROMECAST%22%3Afalse%2C%22E"
    "XPANDED%22%3Afalse%2C%22FORCENOLOOP%22%3Afalse%7D; wpn_ad_cookie=394cc002eee8b93bfa12907baa16c0ad; session_ath=li"
    "ght; zone-cap-3959997=1; last_views=%5B%2237177493-1615713518%22%5D; chat_data_c=%7B%22ct%22%3A%229v%5C%2FmGUDeJs"
    "zV5WHZjgvrogMKoIYVrD27y2uRKrHVzKetjaIqq9TGQzf5KI8D9Zl%2BWqCE4cRh7ByiFgmk84IR3tBd7egoowqyCBVqNt6Fg4Yl6EDRHLgj4FtPq"
    "XvzXHN9925UGs%2B3eQIxua093%2BfsKYI1ntzVBN2yGY%2BczxEw4V9DdtL5JtoZDdIpvsEqBI4QA5f2zW47UVR%5C%2Fh5UE85DR9ichsnTZSeZ"
    "Nr4%5C%2FxwTnrHHS%2BYrqtf%5C%2Fvr%5C%2FS0g1XaYfV7mxwskpvKo6l%2BbcV6zOP1s2eO5QXxczqA5RSW8BdDLcAWcng4h3IFAGhTyteq1O"
    "6elT1NthZqGWW5tXdKx%2BCtqrtF7qwZgUHR7776QwCSv2ShXpANQn8xzQ7APZKhvFByiZPA1dKtfzREjIXp6btiFM2Ql5eHhohocnUxp9PoAJL9b"
    "FVULKgWeKs1RZZIPcwDk6VBKUlYm%5C%2FY4OwVmzh2jL6eaSo6TxHKd6cT%5C%2Fjx%2BV7GBUw%5C%2F%5C%2Frrgl3bW1XnyNKFMPGiHcqrbmm"
    "6yugXnLQHZCs0X4DRbcuX5w07pByfPpf9F2uRk7h4mtESNuX%5C%2FMJDKtP63gEYdcaeDqMZqk94HiYxQUYBwpwdzYU6LOKVbE08%5C%2FrHroT7"
    "A26YQb3a5N33zEhbEFJbNjcp8Qnat9TaW%2BiVSTKlzycSMOaC5A81eN%5C%2F6x4%2B5Q9S%5C%2FO%5C%2FrP9LfsLIdMW647XOLR2ff8svfbHp"
    "Fjthy7SY3oUus9jLAGA50XQVHOc64KYdpdIyjs5LHr%5C%2FOvab7hew4kGBhWyHjNqNUIACA9%2BGHyg4MRM8zFMlgUrWJYT0ku%5C%2FgvPvISM"
    "iamZqtpQQeO9LLDYLxYcYtjgIV0NSfGKJL7vFN9ryZWosMsVgogwoWc7ruHyp9H6F6snvj6d8XGsTKLJKWhR49lyQTPJzwI3F90sLcTYLoW7UJf1V"
    "PYr%5C%2FaaQmltvTgU0Xsy6zNPA00ZLWQuZSahcg66%5C%2FJkhPRR904wmZgsdDlI0mLAWEHZMlmYHiSupkqczu%5C%2F%5C%2FSUlOGYo590gd"
    "0MIYvH1P0vQEWz6b4jn91WvhWsSilCwA2mulTk4qLI0z7jqYVf7p1WuppfKjHC%2BgXocWxToiFRQsL1FHLm2a01Sj01zAL0gqruvyzgGC3FkmF79"
    "6efdSpI17VtxYpeqyL0RTQEDhYpLLXdzIiKCZogqgbPeCkecIOh6Xd6KnsLtjShJ86MZPVTC%2BxIQWVMzsp%2BHkrf6bA7vFz%5C%2FH6UA5lk2a"
    "Ij96Yi3cDG6JaajevCJwoQA9foa4II2ubWqBDcPOaS%22%2C%22iv%22%3A%22046e4418e6818046d792644a4b8b52ee%22%2C%22s%22%3A%22"
    "8eae24883cdd399e%22%7D; session_token=4bc901d5777eaa32aTEY0rppU0xlJ_NVMq4aT35i0IBO9fc6Ifz1wVBTaZqhGVEgrFhM_cM2Z_C"
    "YzJziOkUCVRQTRejOf2rQ_PK6UbO2US3Wn-Y5zWgc2QwG0TEvTvG_sPUwbooGa7rkuGYYyC3rpPzyY9levAN4Pyuu60TGBpR0fqCV20lJstCDyOeJ"
    "bCu7tMKwexyznMsapYOQjO9BuJaPxEZant-c2W0eqc-VMD2rtDG9rWB0zxK9YXKYxWcyw0SGDQVadhJqZyhQZyxFl8-75T_3vriTuCs-Urdq8sWZz"
    "MuahaWCoLFeYCjuZRytO8D2Yy-LFWTmFKkBsdJsSrnnJgwpoDr3jfNXee3kU1AjKPweHHvjg10dG8ZGAbyUrkn0Ukq6BA4ON7i-fSliEGaq2Zb4-B"
    "1Rcg0qU9NAy_hsFp56IzlkHOgxK4L4zZ-TuAA7YVJYYGKXCKtkmD3rOi9WKqG3eabn8sEyCA%3D%3D; X-Backend=11|YE3XA|YE3W+; hexavid"
    "_lastsubscheck=1"
)
COOKIES = [
    ("", {}),
    ("foo=bar", {"foo": "bar"}),
    ("foo=bar; hello=world", {"foo": "bar", "hello": "world"}),
    ("foo=bar;hello=world", {"foo": "bar;hello"}),
    (
        COOKIE,
        {
            "html5_pref": "%7B%22SQ%22%3Afalse%2C%22MUTE%22%3Afalse%2C%22VOLUME%22%3A1%2C%22FORCENOPICTURE%22%3Afalse%"
            "2C%22FORCENOAUTOBUFFER%22%3Afalse%2C%22FORCENATIVEHLS%22%3Afalse%2C%22PLAUTOPLAY%22%3Atrue%"
            "2C%22CHROMECAST%22%3Afalse%2C%22EXPANDED%22%3Afalse%2C%22FORCENOLOOP%22%3Afalse%7D",
            "wpn_ad_cookie": "394cc002eee8b93bfa12907baa16c0ad",
            "session_ath": "light",
            "zone-cap-3959997": "1",
            "last_views": "%5B%2237177493-1615713518%22%5D",
            "chat_data_c": "%7B%22ct%22%3A%229v%5C%2FmGUDeJszV5WHZjgvrogMKoIYVrD27y2uRKrHVzKetjaIqq9TGQzf5KI8D9Zl%2BWq"
            "CE4cRh7ByiFgmk84IR3tBd7egoowqyCBVqNt6Fg4Yl6EDRHLgj4FtPqXvzXHN9925UGs%2B3eQIxua093%2BfsKYI1"
            "ntzVBN2yGY%2BczxEw4V9DdtL5JtoZDdIpvsEqBI4QA5f2zW47UVR%5C%2Fh5UE85DR9ichsnTZSeZNr4%5C%2FxwT"
            "nrHHS%2BYrqtf%5C%2Fvr%5C%2FS0g1XaYfV7mxwskpvKo6l%2BbcV6zOP1s2eO5QXxczqA5RSW8BdDLcAWcng4h3I"
            "FAGhTyteq1O6elT1NthZqGWW5tXdKx%2BCtqrtF7qwZgUHR7776QwCSv2ShXpANQn8xzQ7APZKhvFByiZPA1dKtfzR"
            "EjIXp6btiFM2Ql5eHhohocnUxp9PoAJL9bFVULKgWeKs1RZZIPcwDk6VBKUlYm%5C%2FY4OwVmzh2jL6eaSo6TxHKd"
            "6cT%5C%2Fjx%2BV7GBUw%5C%2F%5C%2Frrgl3bW1XnyNKFMPGiHcqrbmm6yugXnLQHZCs0X4DRbcuX5w07pByfPpf9"
            "F2uRk7h4mtESNuX%5C%2FMJDKtP63gEYdcaeDqMZqk94HiYxQUYBwpwdzYU6LOKVbE08%5C%2FrHroT7A26YQb3a5N"
            "33zEhbEFJbNjcp8Qnat9TaW%2BiVSTKlzycSMOaC5A81eN%5C%2F6x4%2B5Q9S%5C%2FO%5C%2FrP9LfsLIdMW647X"
            "OLR2ff8svfbHpFjthy7SY3oUus9jLAGA50XQVHOc64KYdpdIyjs5LHr%5C%2FOvab7hew4kGBhWyHjNqNUIACA9%2B"
            "GHyg4MRM8zFMlgUrWJYT0ku%5C%2FgvPvISMiamZqtpQQeO9LLDYLxYcYtjgIV0NSfGKJL7vFN9ryZWosMsVgogwoW"
            "c7ruHyp9H6F6snvj6d8XGsTKLJKWhR49lyQTPJzwI3F90sLcTYLoW7UJf1VPYr%5C%2FaaQmltvTgU0Xsy6zNPA00Z"
            "LWQuZSahcg66%5C%2FJkhPRR904wmZgsdDlI0mLAWEHZMlmYHiSupkqczu%5C%2F%5C%2FSUlOGYo590gd0MIYvH1P"
            "0vQEWz6b4jn91WvhWsSilCwA2mulTk4qLI0z7jqYVf7p1WuppfKjHC%2BgXocWxToiFRQsL1FHLm2a01Sj01zAL0gq"
            "ruvyzgGC3FkmF796efdSpI17VtxYpeqyL0RTQEDhYpLLXdzIiKCZogqgbPeCkecIOh6Xd6KnsLtjShJ86MZPVTC%2B"
            "xIQWVMzsp%2BHkrf6bA7vFz%5C%2FH6UA5lk2aIj96Yi3cDG6JaajevCJwoQA9foa4II2ubWqBDcPOaS%22%2C%22i"
            "v%22%3A%22046e4418e6818046d792644a4b8b52ee%22%2C%22s%22%3A%228eae24883cdd399e%22%7D",
            "session_token": "4bc901d5777eaa32aTEY0rppU0xlJ_NVMq4aT35i0IBO9fc6Ifz1wVBTaZqhGVEgrFhM_cM2Z_CYzJziOkUCVRQT"
            "RejOf2rQ_PK6UbO2US3Wn-Y5zWgc2QwG0TEvTvG_sPUwbooGa7rkuGYYyC3rpPzyY9levAN4Pyuu60TGBpR0fqCV"
            "20lJstCDyOeJbCu7tMKwexyznMsapYOQjO9BuJaPxEZant-c2W0eqc-VMD2rtDG9rWB0zxK9YXKYxWcyw0SGDQVa"
            "dhJqZyhQZyxFl8-75T_3vriTuCs-Urdq8sWZzMuahaWCoLFeYCjuZRytO8D2Yy-LFWTmFKkBsdJsSrnnJgwpoDr3"
            "jfNXee3kU1AjKPweHHvjg10dG8ZGAbyUrkn0Ukq6BA4ON7i-fSliEGaq2Zb4-B1Rcg0qU9NAy_hsFp56IzlkHOgx"
            "K4L4zZ-TuAA7YVJYYGKXCKtkmD3rOi9WKqG3eabn8sEyCA%3D%3D",
            "X-Backend": "11|YE3XA|YE3W+",
            "hexavid_lastsubscheck": "1",
        },
    ),
]


@pytest.mark.parametrize(("cookie", "expected"), COOKIES)
def test_parse_cookies(cookie, expected):
    assert parse_cookies(cookie) == expected


@pytest.mark.parametrize(
    ("cookie", "expected"),
    [(cookie_pair[0], cookie_pair[0]) for cookie_pair in COOKIES],
)
def test_cookie_save_and_read(cookie, expected):
    save_cookie(cookie)
    assert read_cookie() == cookie


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (
            "https://www.xvideos.com/video37177493/asian_webcam_2_camsex4u.life",
            "37177493",
        ),
        ("https://www.xvideos.com/profiles/mypornstation", None),
    ],
)
def test_parse_video_id(index, expected):
    assert parse_video_id(index) == expected


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (
            "https://www.xvideos.com/video37177493/asian_webcam_2_camsex4u.life",
            "asian_webcam_2_camsex4u.life",
        ),
        ("https://www.xvideos.com/profiles/mypornstation", None),
    ],
)
def test_parse_video_name(index, expected):
    assert parse_video_name(index) == expected


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (
            "https://www.xvideos.com/video37177493/asian_webcam_2_camsex4u.life",
            "Asian Webcam #2 camsex4u.life",
        ),
        ("https://www.xvideos.com/profiles/mypornstation", None),
    ],
)
def test_get_video_full_name(index, expected):
    assert get_video_full_name(index) == expected


@pytest.mark.parametrize(
    ("vid", "expected"),
    [
        (
            "37177493",
            "https://video-hw.xvideos-cdn.com/videos/mp4/3/c/3/xvideos.com_3c3bde289827a1e121613e06e401602d.mp4?e=1615"
            "725210&h=270d5104980859c94ba386295c8c39ae&download=1",
        ),
    ],
)
def test_get_video_url(vid, expected):
    assert get_video_url(vid, False, False).split("?")[0] == expected.split("?")[0]
