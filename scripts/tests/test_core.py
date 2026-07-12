"""八字排盘引擎核心测试"""
import sys

sys.path.insert(0, '.')

from bazi_engine.day_pillar_db import lookup_day_pillar, verify_known_cases
from bazi_engine.enums import Shishen, Tiangan, Wuxing
from bazi_engine.nayin_chain import find_all_nayin_relations
from bazi_engine.ten_gods import get_ten_god, wuxing_ke, wuxing_relation, wuxing_sheng


class TestWuxing:
    """五行生克测试"""

    def test_wuxing_sheng(self):
        assert wuxing_sheng(Wuxing.木) == Wuxing.火
        assert wuxing_sheng(Wuxing.火) == Wuxing.土
        assert wuxing_sheng(Wuxing.土) == Wuxing.金

    def test_wuxing_ke(self):
        assert wuxing_ke(Wuxing.木) == Wuxing.土
        assert wuxing_ke(Wuxing.金) == Wuxing.木

    def test_wuxing_relation(self):
        assert wuxing_relation(Wuxing.木, Wuxing.火) == "生"
        assert wuxing_relation(Wuxing.火, Wuxing.木) == "被生"
        assert wuxing_relation(Wuxing.金, Wuxing.木) == "克"
        assert wuxing_relation(Wuxing.木, Wuxing.金) == "被克"
        assert wuxing_relation(Wuxing.木, Wuxing.木) == "比和"


class TestDayPillar:
    """日柱计算测试"""

    def test_known_cases(self):
        assert verify_known_cases(), "已知案例验证失败"

    def test_lookup(self):
        stem, branch = lookup_day_pillar(2007, 8, 26)
        assert stem == "壬" and branch == "辰", f"2007-08-26 should be 壬辰, got {stem}{branch}"


class TestNayinChain:
    """纳音生克链测试"""

    def test_sheng_chain(self):
        rels = find_all_nayin_relations("海中金", "泉中水", "松柏木", "霹雳火")
        chains = [r.relation_type for r in rels]
        assert "顺生链" in chains, "金->水->木->火 should be 顺生链"

    def test_sheng_relation(self):
        rels = find_all_nayin_relations("海中金", "炉中火", "大林木", "路旁土")
        types = [r.relation_type for r in rels]
        assert "他柱克年纳音" in types, "火克金"
        assert "年纳音克他柱" in types, "金克木"


class GetTenGod:
    """十神计算测试"""

    def test_tong_bi(self):
        s = get_ten_god(Tiangan.甲, Tiangan.甲)
        assert s == Shishen.比肩

    def test_sheng_xie(self):
        s = get_ten_god(Tiangan.甲, Tiangan.丙)  # 甲木生丙火, 甲阳丙阳 = 食神
        assert s == Shishen.食神

    def test_ke_wo(self):
        s = get_ten_god(Tiangan.甲, Tiangan.庚)  # 庚金克甲木, 甲阳庚阳 = 偏官
        assert s == Shishen.偏官
