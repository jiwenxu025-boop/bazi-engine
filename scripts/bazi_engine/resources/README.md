# 全国出生地离线数据

运行时文件 `cn_divisions.jsonl` 由 AreaCity 的三级行政区划与坐标数据生成，不在排盘过程中调用地图、定位或地理编码服务。

## 来源与版本

- 项目：<https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov>
- 发布版：`2025.251231.260403`
- 发布页：<https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov/releases/tag/2025.251231.260403>
- 许可证：MIT，副本见 `AreaCity-LICENSE.txt`
- 行政区划归档：`ok_data_level3-4.csv.7z`
- 坐标归档：`ok_geo.csv.7z`

归档 SHA256：

```text
0B181B4105C32B2631B1C8C8654859F10684C3748B188EBE08F342291DEC1169  ok_data_level3-4.csv.7z
675C3E9B8DEC6444994D3EF53259A145304F6A957DB8A5E601E55C0B9E61E21A  ok_geo.csv.7z
```

解压后 CSV SHA256：

```text
DD5A1594565B65FA3FEA5CE4B9935E0B28908226949AE44F07EBFD533428E8FF  ok_data_level3.csv
AC2641B1CB137D099779F49B21B965919591AF9D82A29A911F6270530FEF8ED7  ok_geo.csv
```

## 生成口径

- 保留源数据的市级（`deep=1`）与区县级（`deep=2`）真实行政节点。
- 过滤 37 个与父节点同名、同全称的结构补齐节点。
- 使用行政代码作为稳定 ID，并保留简称、全称、行政路径与拼音。
- 源坐标为 GCJ-02，生成器近似逆变换为 WGS84 后保留 6 位小数。
- 当前共 3564 条：市级 392 条、区县级 3172 条；3186 条有坐标，台湾 378 条源数据坐标为 `EMPTY`。
- 缺坐标节点不借用附近地点经度；系统默认回退用户输入时间，也允许用户明确填写手动经度。

## 再生成

在仓库根目录执行：

```powershell
$sourceDir = "C:\path\to\extracted"
python scripts/tools/build_location_registry.py `
  --areas "$sourceDir\ok_data_level3.csv" `
  --geo "$sourceDir\ok_geo.csv" `
  --output scripts/bazi_engine/resources/cn_divisions.jsonl `
  --version 2025.251231.260403
```

生成结果首行包含源 CSV 哈希、记录数、坐标统计和坐标系口径；发布前必须与回归测试一起核对。
