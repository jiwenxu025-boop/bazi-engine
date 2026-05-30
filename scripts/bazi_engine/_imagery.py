"""干支体象查表 — 《渊海子平》十干体象 + 十二支咏 + 《格物至言》六十甲子逐日取象

验证来源: WebSearch 2026-05-26
- 十干体象: 《渊海子平·十干体象》全篇
- 十二支咏: 《渊海子平·地支十二咏》
- 六十甲子取象: 《格物至言》(又名《日元确论》)
"""

from .enums import Dizhi, Tiangan

# ═══════════════════════════════════════════════════════════════
# 十干体象
# 来源: 《渊海子平·十干体象》+《滴天髓》天干论
# 验证: WebSearch 2026-05-26
# ═══════════════════════════════════════════════════════════════

STEM_IMAGERY: dict[str, dict] = {
    "甲": {
        "core_image": "参天大树、栋梁之材",
        "poem": "甲木天干作首排，原无枝叶与根荄。欲存天地千年久，直向沙泥万丈埋。断就栋梁金得用，化成灰炭火为灾。蠢然块物无机事，一任春秋自往来。",
        "drip": "甲木参天，脱胎要火。春不容金，秋不容土。火炽乘龙，水宕骑虎。地润天和，植立千古。",
        "likes": "土为根基，金为雕琢（庚金七杀为斧斤）",
        "dislikes": "火多木焚（健康问题），水多木漂",
        "personality": "正直、向上、坚韧、有原则。性直无机心，如大树般可依靠。",
        "five_virtues": "木主仁（阳木），仁德宽厚有担当",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "乙": {
        "core_image": "花草藤蔓、稻黍稷麦",
        "poem": "乙木根荄种得深，只宜阳地不宜阴。漂浮最怕多逢水，刻断何当苦用金。南去火炎灾不浅，西行土重祸犹侵。栋梁不是连根木，辨别工夫好用心。",
        "drip": "乙木虽柔，刲羊解牛。怀丁抱丙，跨凤乘猴。虚湿之地，骑马亦忧。藤萝系甲，可春可秋。",
        "likes": "阳地（喜阳光丙火），甲木为靠（藤萝系甲）",
        "dislikes": "水多漂荡，金多戕害，火炎土重",
        "personality": "柔韧、灵活、善变通、适应力强。如藤蔓般善攀附借力。",
        "five_virtues": "木主仁（阴木），柔仁善适应",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "丙": {
        "core_image": "太阳之光、洪炉烈火",
        "poem": "丙火明明一太阳，原从正大立纲常。洪光不独窥千里，巨焰犹能遍八荒。出世肯为浮木子，传生不作湿泥娘。江湖死水安能克，惟怕成林木作殃。",
        "drip": "丙火猛烈，欺霜侮雪。能煅庚金，逢辛反怯。土众成慈，水猖显节。虎马犬乡，甲来焚灭。",
        "likes": "壬水映照（日照江湖），甲木为燃料",
        "dislikes": "木多火塞（甲木偏印多反无生机），癸水云雾遮蔽",
        "personality": "光明正大、热情奔放、重面子好礼仪。如太阳般照耀他人。",
        "five_virtues": "火主礼（阳火），光明磊落重礼仪",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "丁": {
        "core_image": "烛灯、星火、炉中火",
        "poem": "丁火其形一烛灯，太阳相见夺光明。得时能化千斤铁，失令难熔一寸金。虽少干柴尤可引，纵多湿木不能生。其间衰旺当分晓，旺比一炉衰一檠。",
        "drip": "丁火柔中，内性昭融。抱乙而孝，合壬而忠。旺而不烈，衰而不穷。如有嫡母，可秋可冬。",
        "likes": "甲木为燃料（嫡母），乙木为干柴。夜生最佳。",
        "dislikes": "丙火（太阳）同现夺光，湿木（水多木湿）不能生火",
        "personality": "敏锐细腻、外柔内刚、忠诚持久。灯烛之光绵延不绝，持久力强。",
        "five_virtues": "火主礼（阴火），文明之象，内心有锋芒",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "戊": {
        "core_image": "城墙、堤岸、高山冈陵",
        "poem": "戊土城墙堤岸同，振江河海要根重。柱中带合形还壮，日下乘虚势必崩。力薄不胜金漏泄，功成安用木疏通。平生最爱东南健，身旺东南健失中。",
        "drip": "戊土固重，既中且正。静翕动辟，万物司命。水润物生，火燥物病。若在艮坤，怕冲宜静。",
        "likes": "甲木疏土（功成用木疏通），戊癸合火，水润",
        "dislikes": "金多泄土（力薄不胜金漏泄），火燥",
        "personality": "敦厚诚实、稳重可靠、信誉第一。如城墙般坚固可靠。",
        "five_virtues": "土主信（阳土），诚信稳重有担当",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "己": {
        "core_image": "田园沃土、坤德载物",
        "poem": "己土田园属四维，坤深能为万物基。水金旺处身还弱，火土功成局最奇。失令岂能埋剑戟，得时方可用磁基。漫夸印旺兼多合，不遇刑冲总不宜。",
        "drip": "己土卑湿，中正蓄藏。不愁木盛，不畏水狂。火少火晦，金多金光。若要物旺，宜助宜帮。",
        "likes": "丙火（不离丙火），刑冲（不遇刑冲总不宜——需要冲开），湿土（丑辰）",
        "dislikes": "甲乙官杀混杂，燥土（戊戌未）",
        "personality": "温厚包容、细腻周到、如大地般承载养育。",
        "five_virtues": "土主信（阴土），温厚诚信善包容",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "庚": {
        "core_image": "钢铁、剑戟、顽金矿石",
        "poem": "庚金顽钝性偏刚，火制功成怕火乡。夏产东南过锻炼，秋生西北亦光芒。水深反见他相克，木旺能令我自伤。戊己干支重遇土，不逢冲破即埋藏。",
        "drip": "庚金带煞，刚健为最。得水而清，得火而锐。土润则生，土干则脆。能赢甲兄，输于乙妹。",
        "likes": "丁火锻炼，丙火熔铸，水淬（金水相涵）",
        "dislikes": "土厚埋金（戊己重遇土，不逢冲破即埋藏），木旺耗金",
        "personality": "刚健果断、带煞气、不怒自威。如刀剑般锐利干脆。",
        "five_virtues": "金主义（阳金），刚义果断有魄力",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "辛": {
        "core_image": "珠玉、金银首饰、珍宝",
        "poem": "辛金珠玉性虚灵，最爱阳和沙水清。成就不劳炎火煅，资扶偏爱湿泥生。木多火旺宜西北，水冷金寒要丙丁。坐禄通根身旺地，何愁厚土没其形。",
        "drip": "辛金软弱，温润而清。畏土之叠，乐水之盈。能扶社稷，能救生灵。热则喜母，寒则喜丁。",
        "likes": "水洗（金水相涵，伤官格最佳），湿土（己丑辰），丙丁暖金",
        "dislikes": "厚土掩埋（戊戌未燥土印格无用），火多克金",
        "personality": "灵秀细腻、追求完美、如珠玉般温润而有光泽。",
        "five_virtues": "金主义（阴金），秀义细腻有品味",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "壬": {
        "core_image": "江河湖海、百川汇聚",
        "poem": "壬水汪洋并百川，漫流天下总无边。干支多聚成漂荡，火土重逢涸本源。养性结胎须未午，长生归禄属坤乾。身强原自无财禄，西北行程厄少年。",
        "drip": "壬水通河，能泄金气。刚中之德，周流不滞。通根透癸，冲天奔地。化则有情，从则相济。",
        "likes": "戊土堤防，丙火日照（日照江湖），寅木纳水",
        "dislikes": "身强无制则泛滥，水多漂荡，土重涸源",
        "personality": "智慧豁达、胸怀宽广、流动性强。如江河般奔流不息。",
        "five_virtues": "水主智（阳水），豁达智慧有胸襟",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
    "癸": {
        "core_image": "雨露甘霖、涧泽细水",
        "poem": "癸水应非雨露麽，根通亥子即江河。柱无坤坎身还弱，局有财官不尚多。申子辰全成上格，午寅戌备要中和。假饶火土生深夏，西北行程岂太过。",
        "drip": "癸水至弱，达于天津。得龙而运，功化斯神。不愁火土，不论庚辛。合戊见火，化象斯真。",
        "likes": "乙卯（草叶露珠之象），庚辛发源。申子辰润下格。",
        "dislikes": "戊癸合不化恐利令智昏，火土过燥涸水",
        "personality": "细腻内敛、聪慧含蓄、润物无声。如春雨般滋养万物。",
        "five_virtues": "水主智（阴水），细腻智慧善渗透",
        "source": "《渊海子平》十干体象 +《滴天髓》天干论"
    },
}

# ═══════════════════════════════════════════════════════════════
# 十二支体象（《渊海子平·地支十二咏》选要）
# 来源: 《渊海子平》+ 搜索验证 2026-05-26
# ═══════════════════════════════════════════════════════════════

BRANCH_IMAGERY: dict[str, dict] = {
    "子": {
        "core_image": "溪涧汪洋、水之魁首",
        "likes": "申辰合局即成江海",
        "dislikes": "午破无定，卯刑有暗伤",
        "notes": "子为水之正位，阳水之源。逢申辰三合水局，格局放大。",
        "source": "《渊海子平》地支十二咏"
    },
    "丑": {
        "core_image": "隆冬冰土、寒金之库",
        "likes": "须火温暖方能生万物，刑冲戌未开库",
        "dislikes": "无火则冰土寒金不能发用",
        "notes": "丑为金库，藏己辛癸。刑冲开库方显其能。",
        "source": "《渊海子平》地支十二咏"
    },
    "寅": {
        "core_image": "初春嫩木、火之长生地",
        "likes": "午戌合火局超凡入圣",
        "dislikes": "申金冲克",
        "notes": "寅为甲木禄地、丙火长生、戊土长生。木火土同宫之奇。",
        "source": "《渊海子平》地支十二咏"
    },
    "卯": {
        "core_image": "繁华灌木、仲春之木",
        "likes": "亥未三合成林",
        "dislikes": "庚辛申酉克伐",
        "notes": "卯为乙木禄地，最怕金克。月为桃花之乡。",
        "source": "《渊海子平》地支十二咏"
    },
    "辰": {
        "core_image": "温润水泥、水库",
        "likes": "戌冲开库为吉",
        "dislikes": "三戌冲破为凶，水木过重",
        "notes": "辰为水库，又为戊土本气。冲开则水库可纳水、土库可生金。",
        "source": "《渊海子平》地支十二咏"
    },
    "巳": {
        "core_image": "初夏增光、六阳之极",
        "likes": "寅申三刑无害",
        "dislikes": "亥冲有伤",
        "notes": "巳为丙火禄地、庚金长生。巳亥冲最烈，因火水直接对冲。",
        "source": "《渊海子平》地支十二咏"
    },
    "午": {
        "core_image": "炎炎烈火、一阴始生",
        "likes": "戌寅合局光明",
        "dislikes": "申子冲克不利",
        "notes": "午为丁火禄地、己土禄地。阳极阴生之地。",
        "source": "《渊海子平》地支十二咏"
    },
    "未": {
        "core_image": "阴深火衰、木库",
        "likes": "丙丁暖之方可发用",
        "dislikes": "无火怕行金水运",
        "notes": "未为木库，藏官藏印不藏财。木火相生为佳。",
        "source": "《渊海子平》地支十二咏"
    },
    "申": {
        "core_image": "刚健之金、水土长生",
        "likes": "巳午锻炼成器，子辰合局生辉",
        "dislikes": "土重埋金",
        "notes": "申为庚金禄地、壬水长生。金水相生，忌土重。",
        "source": "《渊海子平》地支十二咏"
    },
    "酉": {
        "core_image": "从魁珠玉、金白水清",
        "likes": "水洗金清，巳丑合金局",
        "dislikes": "火多忌行木火运",
        "notes": "酉为辛金禄地，纯金之位。金水相涵最美。",
        "source": "《渊海子平》地支十二咏"
    },
    "戌": {
        "core_image": "河魁刚土、火库",
        "likes": "能成就顽金钝铁，辰冲生雨露，寅午合文章",
        "dislikes": "无冲则火库郁闭",
        "notes": "戌为火库，又为戊土本气。辰戌冲开则水火既济。",
        "source": "《渊海子平》地支十二咏"
    },
    "亥": {
        "core_image": "登明深水、六阴之寒",
        "likes": "须火方能用土，亥卯未合木有成",
        "dislikes": "巳冲、水多无制",
        "notes": "亥为壬水禄地、甲木长生。水木清华，但水寒须火暖。",
        "source": "《渊海子平》地支十二咏"
    },
}

# ═══════════════════════════════════════════════════════════════
# 六十甲子逐日取象（《格物至言》又名《日元确论》）
# 来源: 《格物至言》六十干支取象
# 验证: WebSearch 2026-05-26
# 注: 仅完成已有参考数据的干支，其余留待后续填充
# ═══════════════════════════════════════════════════════════════

# 完整60甲子取象 — WebSearch验证 2026-05-27
JIAZI_DAILY_IMAGERY: dict[str, dict] = {
    # ── 完整60甲子逐日取象（《格物至言》）──
    # 来源: WebSearch 2026-05-27 验证
    # 甲木
    "甲子": {"object_image": "空心衰败之木", "characteristics": "甲坐子水正印，水冷木寒，需火暖局方能发荣。忌金水漂荡。", "source": "《格物至言》"},
    "甲寅": {"object_image": "硕果品汇之木", "characteristics": "甲坐寅禄地，根深叶茂。喜庚辛修剪看守，忌无官杀复行比劫。", "source": "《格物至言》"},
    "甲辰": {"object_image": "郁湿水松之木", "characteristics": "水边松树，韧性有余干燥不足。喜火土培根，忌水多烂根。", "source": "《格物至言》"},
    "甲午": {"object_image": "工师运斤之木", "characteristics": "甲坐午火伤官，木火通明。喜庚金雕琢，辛次之。", "source": "《格物至言》"},
    "甲申": {"object_image": "斫断入水之木", "characteristics": "甲坐申金七杀绝地，枯木偏宜活水长濡。喜金水湿泥，忌火土枯燥。", "source": "《格物至言》"},
    "甲戌": {"object_image": "窖土松杉之木", "characteristics": "甲坐戌火库，木根入火土。宜因时五行葆合，忌违时冲克。", "source": "《格物至言》"},
    # 乙木
    "乙丑": {"object_image": "沾土初芽之木", "characteristics": "乙坐丑湿土，初春嫩芽。喜丙火暖之、微云细雨养之，忌甲庚冲克。", "source": "《格物至言》"},
    "乙卯": {"object_image": "秀实禄品之木", "characteristics": "乙坐卯禄地，繁华灌木。喜辛金修剪、水火土护，忌庚甲伤害。", "source": "《格物至言》"},
    "乙巳": {"object_image": "倒插花卉之木", "characteristics": "乙坐巳火伤官，倒插之花。喜庚壬金水湿泥相凑，忌木火燥土。", "source": "《格物至言》"},
    "乙未": {"object_image": "藤萝施架之木", "characteristics": "乙坐未木库，藤萝需架。喜甲乙寅亥火土旺气，忌庚辛申酉墓库。", "source": "《格物至言》"},
    "乙酉": {"object_image": "盆花奇馥之木", "characteristics": "乙坐酉金七杀，盆中花木。喜酉时护酉之五行，忌午亥破劫。", "source": "《格物至言》"},
    "乙亥": {"object_image": "水上寄生之木", "characteristics": "乙坐亥水正印，水上浮萍。喜生扶及甲乙卯未寅亥相合，忌申酉巳亥冲。", "source": "《格物至言》"},
    # 丙火
    "丙子": {"object_image": "日入咸池之火", "characteristics": "丙坐子水正官，太阳入水。昼生喜木火土，夜生喜金水。", "source": "《格物至言》"},
    "丙寅": {"object_image": "日升旸谷之火", "characteristics": "丙坐寅木长生，旭日东升。昼喜会刃舒配，夜忌申马冲驰。", "source": "《格物至言》"},
    "丙辰": {"object_image": "日经天罗之火", "characteristics": "丙坐辰水库，日照龙宫。昼喜发强刚毅，夜喜静息宁谧。", "source": "《格物至言》"},
    "丙午": {"object_image": "日丽中天之火", "characteristics": "丙坐午火羊刃，烈日当空。昼喜金水调剂，夜忌木火土重逢。", "source": "《格物至言》"},
    "丙申": {"object_image": "日落西山之火", "characteristics": "丙坐申金病地，红霞晚照。喜木火土运，忌金水阴曀。", "source": "《格物至言》"},
    "丙戌": {"object_image": "日入地网之火", "characteristics": "丙坐戌火库，火归库中。昼喜木火寅午戌，夜喜金水亥子丑。", "source": "《格物至言》"},
    # 丁火
    "丁丑": {"object_image": "钻激之火", "characteristics": "丁坐丑金库，火钻金石。喜庚甲木火土燥运，忌辛水阴湿。", "source": "《格物至言》"},
    "丁卯": {"object_image": "木屑香烟之火", "characteristics": "丁坐卯木偏印，香烟袅袅。喜金水潮湿运，忌木火土干燥。", "source": "《格物至言》"},
    "丁巳": {"object_image": "燧珠之火", "characteristics": "丁坐巳火帝旺，燧火明珠。喜东南木火土开霁，忌西北金水库墓。", "source": "《格物至言》"},
    "丁未": {"object_image": "炉余之炭", "characteristics": "丁坐未木库，炭火余温。喜金水木运续燃，忌火土并冲（怕丑冲）。", "source": "《格物至言》"},
    "丁酉": {"object_image": "琉璃灯光", "characteristics": "丁坐酉金偏财，灯映琉璃。喜乙壬火土金，忌癸甲丙午卯冲破。", "source": "《格物至言》"},
    "丁亥": {"object_image": "风前蜡烛", "characteristics": "丁坐亥水正官绝地，风中残烛。喜壬庚火土运护卫，忌甲癸刑冲。", "source": "《格物至言》"},
    # 戊土
    "戊子": {"object_image": "蒙泉润土", "characteristics": "戊坐子水正财，山下有水。喜火土寅午戌生扶，忌官杀卯申子辰克泄。", "source": "《格物至言》"},
    "戊寅": {"object_image": "艮山静土", "characteristics": "戊坐寅木七杀，静而不动。喜财官印食伤舒配得宜，忌刑冲破耗。", "source": "《格物至言》"},
    "戊辰": {"object_image": "蟹象吐颖之山", "characteristics": "戊坐辰水库，山临水畔。喜金水木申子辰运，忌火土寅午戌（怕戌填辰）。", "source": "《格物至言》"},
    "戊午": {"object_image": "炎炎火山", "characteristics": "戊坐午火正印，火炎土燥。喜五行调剂中和，忌偏畸过甚。", "source": "《格物至言》"},
    "戊申": {"object_image": "石山滞土", "characteristics": "戊坐申金食神，山石崔巍。喜金水木点缀明秀，忌火土燥烈。", "source": "《格物至言》"},
    "戊戌": {"object_image": "魁罡演武山", "characteristics": "戊坐戌土魁罡，重土叠嶂。喜五行舒配得宜，忌卯酉与申子辰运。", "source": "《格物至言》"},
    # 己土
    "己丑": {"object_image": "水腴润田", "characteristics": "己坐丑金库湿土，沃腴之田。喜火土乙运培植，忌金水甲运。", "source": "《格物至言》"},
    "己卯": {"object_image": "休囚失气之土", "characteristics": "己坐卯木七杀，土被木克。喜火土甲木丑戌帮身，忌金水乙木申子卯酉（行卯必危）。", "source": "《格物至言》"},
    "己巳": {"object_image": "岭头稼穑", "characteristics": "己坐巳火正印，岭头之田。喜金水木运滋润，忌火土合燥。", "source": "《格物至言》"},
    "己未": {"object_image": "入土稼穑", "characteristics": "己坐未土比肩，沃土深藏。喜会合化土培植，忌剥削冲克。", "source": "《格物至言》"},
    "己酉": {"object_image": "筑地稼穑", "characteristics": "己坐酉金食神，筑地之田。喜甲木火土培植（最喜丙寅），忌乙木金水。", "source": "《格物至言》"},
    "己亥": {"object_image": "注地稼穑", "characteristics": "己坐亥水正财，水洼之田。喜甲木火土干燥运，忌乙木金水库注运。", "source": "《格物至言》"},
    # 庚金
    "庚子": {"object_image": "倒悬钟磬", "characteristics": "庚坐子水伤官，金沉水底。喜金水木火虚灵发挥，忌火土塞实。", "source": "《格物至言》"},
    "庚寅": {"object_image": "斧斤入林之金", "characteristics": "庚坐寅木绝地，金临绝而伐木。喜木火土干燥锻炼，忌金水木潮湿。", "source": "《格物至言》"},
    "庚辰": {"object_image": "水师将军", "characteristics": "庚坐辰土魁罡，金得水库滋养。喜刃劫金水帮扶，忌木火库墓未戌刑冲。", "source": "《格物至言》"},
    "庚午": {"object_image": "出冶炉锤", "characteristics": "庚坐午火正官，金经火炼。喜金水运淬砺，忌木火土运过甚。", "source": "《格物至言》"},
    "庚申": {"object_image": "已成剑戟", "characteristics": "庚坐申金禄地，金锋已成。喜金水运淬砺锋芒，忌木火土运毁折。", "source": "《格物至言》"},
    "庚戌": {"object_image": "陆路将军", "characteristics": "庚坐戌火库魁罡，金得火炼。喜金火土运，忌水库水乡（最忌辰冲）。", "source": "《格物至言》"},
    # 辛金
    "辛丑": {"object_image": "初胎息之金", "characteristics": "辛坐丑金库，初生嫩金。喜金水沙土生扶运，忌木火卯未刑冲。", "source": "《格物至言》"},
    "辛卯": {"object_image": "水晶虚幻之金", "characteristics": "辛坐卯木绝地，脆薄虚金。喜金土子戌生扶，忌水火亥卯克泄。", "source": "《格物至言》"},
    "辛巳": {"object_image": "石中璞玉", "characteristics": "辛坐巳火正官，玉在石中。喜金水运（总要水方能吐气），忌木火土运掩埋。", "source": "《格物至言》"},
    "辛未": {"object_image": "豁土成辛", "characteristics": "辛坐未土偏印，土中出金。喜土金水运培护，忌木妒合并阴库。", "source": "《格物至言》"},
    "辛酉": {"object_image": "珍贵金玉", "characteristics": "辛坐酉金专禄，纯净珠玉。喜金水运淬洗，忌木火土刑冲破损。", "source": "《格物至言》"},
    "辛亥": {"object_image": "水底珠玉", "characteristics": "辛坐亥水伤官，珠沉水底。喜寅午戌火土运（喜寅合），忌申子辰水库运。", "source": "《格物至言》"},
    # 壬水
    "壬子": {"object_image": "波涛之水", "characteristics": "壬坐子水羊刃，汪洋波涛。喜火土成坝运约束，忌金水木冲坝泛滥。", "source": "《格物至言》"},
    "壬寅": {"object_image": "雨落沙堤", "characteristics": "壬坐寅木食神，雨润林木。喜金水木运流通，忌火土午戌运。", "source": "《格物至言》"},
    "壬辰": {"object_image": "龙宫魁罡之水", "characteristics": "壬坐辰水库魁罡，龙潜深渊。喜金水木申子辰亥子丑，忌火土巳午未寅戌。", "source": "《格物至言》"},
    "壬午": {"object_image": "日照江河之水", "characteristics": "壬坐午火正财，水火既济。喜补水或补火匀停即富贵，失衡即贫贱。", "source": "《格物至言》"},
    "壬申": {"object_image": "水满渠成", "characteristics": "壬坐申金偏印长生，水源充沛。喜金水火运流通，忌木土运阻塞。", "source": "《格物至言》"},
    "壬戌": {"object_image": "骤雨易晴之水", "characteristics": "壬坐戌火库，骤雨入燥土。喜金水运补源，忌木火土运干涸。", "source": "《格物至言》"},
    # 癸水
    "癸丑": {"object_image": "秽积丛杂之水", "characteristics": "癸坐丑金库，杂水汇聚。喜金水木（喜乙卯通气疏息），忌火土库运。", "source": "《格物至言》"},
    "癸卯": {"object_image": "林中涧泉", "characteristics": "癸坐卯木食神长生，林间清泉。喜金水木运培源，忌火土运干涸。", "source": "《格物至言》"},
    "癸巳": {"object_image": "冈阜岑珂水", "characteristics": "癸坐巳火正财帝旺，财官双美。喜山林云雨阴曀，忌亥冲堤坏水枯。", "source": "《格物至言》"},
    "癸未": {"object_image": "洲泽湾苗之水", "characteristics": "癸坐未土，水入木库。喜金水木运涵养，忌火土库运淤塞。", "source": "《格物至言》"},
    "癸酉": {"object_image": "石孔流泉之水", "characteristics": "癸坐酉金偏印，石中泉眼。喜金水木（喜木荫庚润），忌火土运堵塞。", "source": "《格物至言》"},
    "癸亥": {"object_image": "水天一色", "characteristics": "癸坐亥水帝旺，还元之水。喜平稳会合运，忌巳亥刑冲作浪。", "source": "《格物至言》"},
}


# ═══════════════════════════════════════════════════════════════
# Getter functions
# ═══════════════════════════════════════════════════════════════

def get_stem_imagery(stem: Tiangan) -> dict:
    """返回天干的干支体象字典。

    Returns:
        dict with keys: core_image, poem, drip, likes, dislikes, personality, five_virtues, source
    Raises:
        KeyError if stem not in STEM_IMAGERY
    """
    key = stem.value
    if key not in STEM_IMAGERY:
        raise KeyError(f"天干体象未找到: {key}")
    return STEM_IMAGERY[key]


def get_branch_imagery(branch: Dizhi) -> dict:
    """返回地支的体象字典。

    Returns:
        dict with keys: core_image, likes, dislikes, notes, source
    Raises:
        KeyError if branch not in BRANCH_IMAGERY
    """
    key = branch.value
    if key not in BRANCH_IMAGERY:
        raise KeyError(f"地支体象未找到: {key}")
    return BRANCH_IMAGERY[key]


def check_stem_root(stem: Tiangan, seated_branch: Dizhi) -> dict:
    """干支虚实——段建业盲派核心规则。

    段建业《盲派高级班面授笔记》: 「虚实不是旺衰，有根有力的叫实，无根虚浮的叫虚。」
    判断标准: 以单柱定虚实——天干在坐支（同一柱的地支）的藏干中是否有根。
    实=有根有力，虚=无根虚浮。

    Returns: {"rooted": bool, "root_branch": "寅", "type": "實"/"虛"}
    """
    from ._constants import DIZHI_CANGGAN
    for hs in DIZHI_CANGGAN.get(seated_branch, []):
        if hs.stem == stem:
            return {"rooted": True, "root_branch": seated_branch.value, "type": "實"}
    return {"rooted": False, "root_branch": seated_branch.value, "type": "虛"}


def check_all_stems_root(pillars_data: list[dict]) -> dict[str, dict]:
    """检查四柱天干各自的虚实状态。

    Args:
        pillars_data: [{stem, branch, pillar_type}, ...]

    Returns:
        {pillar_type: {rooted, root_branch, type}}
    """
    result = {}
    for p in pillars_data:
        stem_str = p.get("stem", "")
        branch_str = p.get("branch", "")
        pillar_type = p.get("pillar_type", "")
        if stem_str and branch_str:
            try:
                stem = Tiangan(stem_str)
                branch = Dizhi(branch_str)
                result[pillar_type] = check_stem_root(stem, branch)
            except (ValueError, KeyError):
                result[pillar_type] = {"rooted": False, "root_branch": branch_str, "type": "虛"}
    return result


def get_daily_imagery(stem: Tiangan, branch: Dizhi) -> dict | None:
    """返回六十甲子逐日取象。

    Args:
        stem: 天干
        branch: 地支

    Returns:
        dict with keys: object_image, characteristics, source
        None if the entry is not yet populated
    """
    key = f"{stem.value}{branch.value}"
    return JIAZI_DAILY_IMAGERY.get(key)
