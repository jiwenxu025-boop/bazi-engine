"""Versioned, offline birth-place registry used by the time resolver.

The registry deliberately contains only locations whose coordinates are bundled
with the engine.  A place that is not listed must remain ``unknown`` instead of
silently borrowing a nearby city's longitude.
"""

from dataclasses import dataclass

REGISTRY_VERSION = "cn-major-cities-v1"


@dataclass(frozen=True)
class CityRecord:
    id: str
    name: str
    province: str
    longitude: float
    aliases: tuple[str, ...] = ()
    timezone_offset_minutes: int = 480

    @property
    def label(self) -> str:
        return f"{self.province} {self.name}" if self.province else self.name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "province": self.province,
            "label": self.label,
            "longitude": self.longitude,
            "timezone_offset_minutes": self.timezone_offset_minutes,
        }


def _city(
    city_id: str,
    name: str,
    province: str,
    longitude: float,
    *aliases: str,
) -> CityRecord:
    return CityRecord(city_id, name, province, longitude, aliases)


# City-centre longitudes are intentionally a compact, explicit product
# registry.  They are not district-level coordinates and are not used as a
# fallback for an unlisted birthplace.
CITY_REGISTRY: tuple[CityRecord, ...] = (
    _city("beijing", "北京", "北京市", 116.4074, "beijing"),
    _city("tianjin", "天津", "天津市", 117.2009, "tianjin"),
    _city("shijiazhuang", "石家庄", "河北", 114.5149, "shijiazhuang"),
    _city("tangshan", "唐山", "河北", 118.1802, "tangshan"),
    _city("baoding", "保定", "河北", 115.4648, "baoding"),
    _city("taiyuan", "太原", "山西", 112.5492, "taiyuan"),
    _city("hohhot", "呼和浩特", "内蒙古", 111.7492, "huhehaote", "hohhot"),
    _city("shenyang", "沈阳", "辽宁", 123.4315, "shenyang"),
    _city("dalian", "大连", "辽宁", 121.6147, "dalian"),
    _city("changchun", "长春", "吉林", 125.3235, "changchun"),
    _city("haerbin", "哈尔滨", "黑龙江", 126.6424, "harbin", "haerbin"),
    _city("shanghai", "上海", "上海市", 121.4737, "shanghai"),
    _city("nanjing", "南京", "江苏", 118.7969, "nanjing"),
    _city("suzhou", "苏州", "江苏", 120.5853, "suzhou"),
    _city("wuxi", "无锡", "江苏", 120.3119, "wuxi"),
    _city("changzhou", "常州", "江苏", 119.9741, "changzhou"),
    _city("nantong", "南通", "江苏", 120.8943, "nantong"),
    _city("xuzhou", "徐州", "江苏", 117.1848, "xuzhou"),
    _city("hangzhou", "杭州", "浙江", 120.1551, "hangzhou"),
    _city("ningbo", "宁波", "浙江", 121.5503, "ningbo"),
    _city("wenzhou", "温州", "浙江", 120.6994, "wenzhou"),
    _city("jiaxing", "嘉兴", "浙江", 120.7555, "jiaxing"),
    _city("shaoxing", "绍兴", "浙江", 120.5821, "shaoxing"),
    _city("jinhua", "金华", "浙江", 119.6474, "jinhua"),
    _city("taizhou-zj", "台州", "浙江", 121.4208, "taizhou"),
    _city("hefei", "合肥", "安徽", 117.2272, "hefei"),
    _city("wuhu", "芜湖", "安徽", 118.4331, "wuhu"),
    _city("fuzhou", "福州", "福建", 119.2965, "fuzhou"),
    _city("xiamen", "厦门", "福建", 118.0894, "xiamen"),
    _city("quanzhou", "泉州", "福建", 118.6757, "quanzhou"),
    _city("nanchang", "南昌", "江西", 115.8582, "nanchang"),
    _city("ganzhou", "赣州", "江西", 114.9359, "ganzhou"),
    _city("jinan", "济南", "山东", 117.1201, "jinan"),
    _city("qingdao", "青岛", "山东", 120.3826, "qingdao"),
    _city("yantai", "烟台", "山东", 121.4479, "yantai"),
    _city("weifang", "潍坊", "山东", 119.1618, "weifang"),
    _city("linyi", "临沂", "山东", 118.3564, "linyi"),
    _city("zhengzhou", "郑州", "河南", 113.6254, "zhengzhou"),
    _city("luoyang", "洛阳", "河南", 112.4540, "luoyang"),
    _city("kaifeng", "开封", "河南", 114.3076, "kaifeng"),
    _city("xinxiang", "新乡", "河南", 113.8839, "xinxiang"),
    _city("wuhan", "武汉", "湖北", 114.3054, "wuhan"),
    _city("yichang", "宜昌", "湖北", 111.2865, "yichang"),
    _city("xiangyang", "襄阳", "湖北", 112.1441, "xiangyang"),
    _city("jingzhou", "荆州", "湖北", 112.2397, "jingzhou"),
    _city("changsha", "长沙", "湖南", 112.9388, "changsha"),
    _city("zhuzhou", "株洲", "湖南", 113.1340, "zhuzhou"),
    _city("hengyang", "衡阳", "湖南", 112.5719, "hengyang"),
    _city("yueyang", "岳阳", "湖南", 113.1329, "yueyang"),
    _city("guangzhou", "广州", "广东", 113.2644, "guangzhou"),
    _city("shenzhen", "深圳", "广东", 114.0579, "shenzhen"),
    _city("foshan", "佛山", "广东", 113.1227, "foshan"),
    _city("dongguan", "东莞", "广东", 113.7518, "dongguan"),
    _city("zhongshan", "中山", "广东", 113.3824, "zhongshan"),
    _city("zhuhai", "珠海", "广东", 113.5767, "zhuhai"),
    _city("shantou", "汕头", "广东", 116.6819, "shantou"),
    _city("zhanjiang", "湛江", "广东", 110.3594, "zhanjiang"),
    _city("nanning", "南宁", "广西", 108.3665, "nanning"),
    _city("guilin", "桂林", "广西", 110.2900, "guilin"),
    _city("beihai", "北海", "广西", 109.1193, "beihai"),
    _city("haikou", "海口", "海南", 110.1999, "haikou"),
    _city("sanya", "三亚", "海南", 109.5121, "sanya"),
    _city("chongqing", "重庆", "重庆市", 106.5516, "chongqing"),
    _city("chengdu", "成都", "四川", 104.0665, "chengdu"),
    _city("mianyang", "绵阳", "四川", 104.6791, "mianyang"),
    _city("deyang", "德阳", "四川", 104.3979, "deyang"),
    _city("leshan", "乐山", "四川", 103.7654, "leshan"),
    _city("nanchong", "南充", "四川", 106.1107, "nanchong"),
    _city("guiyang", "贵阳", "贵州", 106.6302, "guiyang"),
    _city("kunming", "昆明", "云南", 102.8329, "kunming"),
    _city("dali", "大理", "云南", 100.2676, "dali"),
    _city("lasa", "拉萨", "西藏", 91.1322, "lasa", "lhasa"),
    _city("xian", "西安", "陕西", 108.9398, "xian"),
    _city("xianyang", "咸阳", "陕西", 108.7089, "xianyang"),
    _city("lanzhou", "兰州", "甘肃", 103.8343, "lanzhou"),
    _city("jiayuguan", "嘉峪关", "甘肃", 98.2892, "jiayuguan"),
    _city("xining", "西宁", "青海", 101.7782, "xining"),
    _city("yinchuan", "银川", "宁夏", 106.2309, "yinchuan"),
    _city("urumqi", "乌鲁木齐", "新疆", 87.6168, "wulumuqi", "urumqi"),
    _city("kashgar", "喀什", "新疆", 75.9898, "kashi", "kashgar"),
    _city("hong-kong", "香港", "香港", 114.1694, "hongkong", "hong-kong"),
    _city("macau", "澳门", "澳门", 113.5439, "aomen", "macau"),
    _city("taipei", "台北", "台湾", 121.5654, "taipei"),
    _city("kaohsiung", "高雄", "台湾", 120.3014, "kaohsiung"),
)

_CITY_BY_ID = {city.id: city for city in CITY_REGISTRY}


def get_city(city_id: str | None) -> CityRecord | None:
    return _CITY_BY_ID.get((city_id or "").strip())


def search_cities(query: str, *, limit: int = 12) -> list[CityRecord]:
    normalized = (query or "").strip().casefold()
    if not normalized:
        return list(CITY_REGISTRY[:limit])

    matches = []
    for city in CITY_REGISTRY:
        fields = (city.name, city.province, city.id, *city.aliases)
        if any(normalized in field.casefold() for field in fields):
            matches.append(city)
    return matches[:limit]
