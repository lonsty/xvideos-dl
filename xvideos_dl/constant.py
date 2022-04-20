APP_NAME = "xvideos-dl"
HOST = "https://www.xvideos.com"
VIDEO_PAGE = HOST + "/video{vid}/_"
FAVORITE_API = HOST + "/api/playlists/alpha"
USER_UPLOAD_API = HOST + "/profiles/{u}/activity/{aid}"
PLAYLIST_API = HOST + "/api/playlists/list/{pid}"
CHANNEL_API = HOST + "/channels/{u}/activity/straight/{aid}"
AMATEUR_CHANNEL_API = HOST + "/amateur-channels/{u}/activity/straight/{aid}"
PORNSTAR_CHANNEL_API = HOST + "/pornstar-channels/{u}/activity/straight/{aid}"
MODELS_API = HOST + "/models/{u}/videos/best/{p}"
VIDEO_API = HOST + "/video-download/{vid}/"
HAS_MP4_RESOUCE = ["360p", "250p"]
TIMEOUT = 15  # seconds
FRAGMENT_SIZE = 1024 ** 2 * 16  # 16MB
CHUNK_SIZE = 1024 * 4  # 4KB

SMILE_EMOJIS = [
    "😁",
    "😀",
    "😂",
    "🤣",
    "😃",
    "😄",
    "😅",
    "😆",
    "😉",
    "😊",
    "😋",
    "😎",
    "😍",
    "😘",
    "😗",
    "😙",
    "😚",
    "🙂",
    "🤗",
    "🤔",
    "😐",
    "😑",
    "😏",
    "😛",
    "😜",
    "😝",
    "🤤",
    # "☯",
]
